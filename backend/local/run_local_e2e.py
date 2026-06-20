#!/usr/bin/env python3
"""
Script para ejecutar un flujo E2E local usando LocalStack.

Requisitos previos:
- Tener Docker y docker-compose instalados
- Levantar LocalStack: `docker compose -f docker-compose.localstack.yml up -d`
- Instalar dependencias Python: `pip install boto3`

Este script:
- Crea colas SQS y tablas DynamoDB en LocalStack
- Llama a `ingester.handler` con el CSV de ejemplo
- Procesa los mensajes SQS invocando `processor.handler` (con un stub de Groq)
- Llama a `getter.handler` para obtener resultados

Usar desde la raíz del repo:
python backend/local/run_local_e2e.py
"""
import os
import sys
import time
import json
import types
import importlib.util
from pathlib import Path

# Punto de entrada de LocalStack (por defecto)
LOCALSTACK_ENDPOINT = os.environ.get('LOCALSTACK_ENDPOINT', 'http://localhost:4566')

# Asegurar variables de entorno necesarias
os.environ.setdefault('JOBS_TABLE', 'mediprior-jobs')
os.environ.setdefault('PATIENTS_TABLE', 'mediprior-patients')
os.environ['AWS_ACCESS_KEY_ID'] = 'test'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'test'
os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'

# Monkeypatch boto3 to inject endpoint_url for LocalStack BEFORE cargado de módulos
import boto3 as _boto3
_orig_resource = _boto3.resource
_orig_client = _boto3.client

def _resource(service_name, *args, **kwargs):
    if 'endpoint_url' not in kwargs:
        kwargs['endpoint_url'] = LOCALSTACK_ENDPOINT
    return _orig_resource(service_name, *args, **kwargs)

def _client(service_name, *args, **kwargs):
    if 'endpoint_url' not in kwargs:
        kwargs['endpoint_url'] = LOCALSTACK_ENDPOINT
    return _orig_client(service_name, *args, **kwargs)

_boto3.resource = _resource
_boto3.client = _client

import boto3

ROOT = Path(__file__).resolve().parents[2]

def load_module_from_path(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def ensure_resources():
    print('Creando recursos en LocalStack:', LOCALSTACK_ENDPOINT)
    dynamodb = boto3.resource(
    'dynamodb',
    region_name='us-east-1',
    endpoint_url='http://localhost:4566',
    aws_access_key_id='test',
    aws_secret_access_key='test')
    
    sqs = boto3.client(
    "sqs",
    endpoint_url="http://localhost:4566",
    region_name="us-east-1",
    aws_access_key_id="test",
    aws_secret_access_key="test",
    )

    # Crear DLQ
    dlq = sqs.create_queue(QueueName='mediprior-dlq')
    dlq_attrs = sqs.get_queue_attributes(QueueUrl=dlq['QueueUrl'], AttributeNames=['QueueArn'])
    dlq_arn = dlq_attrs['Attributes']['QueueArn']

    # Crear main queue con redrive policy
    redrive = json.dumps({'deadLetterTargetArn': dlq_arn, 'maxReceiveCount': '3'})
    mainq = sqs.create_queue(QueueName='mediprior-main-queue', Attributes={'VisibilityTimeout': '120', 'RedrivePolicy': redrive})
    mainq_url = mainq['QueueUrl']

    # Crear tablas DynamoDB si no existen
    existing = [t.name for t in dynamodb.tables.all()]
    if 'mediprior-jobs' not in existing:
        print('Creando tabla mediprior-jobs')
        dynamodb.create_table(
            TableName='mediprior-jobs',
            KeySchema=[{'AttributeName': 'jobId', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'jobId', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        ).wait_until_exists()

    if 'mediprior-patients' not in existing:
        print('Creando tabla mediprior-patients')
        dynamodb.create_table(
            TableName='mediprior-patients',
            KeySchema=[{'AttributeName': 'jobId', 'KeyType': 'HASH'}, {'AttributeName': 'patientId', 'KeyType': 'RANGE'}],
            AttributeDefinitions=[{'AttributeName': 'jobId', 'AttributeType': 'S'}, {'AttributeName': 'patientId', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        ).wait_until_exists()

    return {'mainq_url': mainq_url}

def main():
    res = ensure_resources()
    mainq_url = res['mainq_url']

    # Preparar un stub para la librería groq, ya que en pruebas locales no queremos llamar al servicio real
    import sys as _sys
    groq_mod = types.ModuleType('groq')
    def Groq(api_key=None):
        # objeto con estructura mínima usada por el código
        return types.SimpleNamespace(chat=types.SimpleNamespace(completions=types.SimpleNamespace(create=lambda **kwargs: types.SimpleNamespace(choices=[types.SimpleNamespace(message=types.SimpleNamespace(content='{}'))]))))
    groq_mod.Groq = Groq
    _sys.modules['groq'] = groq_mod

    # Cargar módulos lambda desde archivos
    ingester_path = ROOT / 'backend' / 'functions' / 'ingester.py'
    processor_path = ROOT / 'backend' / 'functions' / 'processor.py'
    getter_path = ROOT / 'backend' / 'functions' / 'getter.py'

    # Asegurar que las tablas/colas usadas por los módulos apunten a las creadas
    os.environ['JOBS_TABLE'] = 'mediprior-jobs'
    os.environ['PATIENTS_TABLE'] = 'mediprior-patients'
    os.environ['SQS_QUEUE_URL'] = mainq_url
    os.environ['GROQ_API_KEY'] = 'dummy_key_para_pruebas_locales'

    print('Cargando módulos de funciones...')
    ingester = load_module_from_path('ingester', ingester_path)
    processor = load_module_from_path('processor', processor_path)
    getter = load_module_from_path('getter', getter_path)


    # Leer CSV de ejemplo
    csv_file = ROOT / 'sample-data' / 'pacientes_ejemplo.csv'
    body = csv_file.read_text(encoding='utf-8')

    print('Invocando ingester.handler con CSV de ejemplo...')
    event = {'body': body, 'isBase64Encoded': False}
    resp = ingester.handler(event, None)
    print('Respuesta ingester:', resp)
    try:
        job_id = json.loads(resp['body'])['jobId']
    except Exception:
        print('No se pudo obtener jobId desde la respuesta; abortando')
        return

    # Procesar mensajes en SQS: recibir, invocar processor.handler y borrar mensajes
    sqs = boto3.client(
    "sqs",
    endpoint_url="http://localhost:4566",
    region_name="us-east-1",
    aws_access_key_id="test",
    aws_secret_access_key="test",
    )
    print('Procesando mensajes en SQS...')
    while True:
        r = sqs.receive_message(QueueUrl=mainq_url, MaxNumberOfMessages=10, WaitTimeSeconds=1)
        messages = r.get('Messages', [])
        if not messages:
            break

        # Construir evento similar al de Lambda (Records)
        lambda_event = {
            'Records': [
                {
                    'body': m['Body'], 
                    'messageId': m['MessageId'],
                    'receiptHandle': m['ReceiptHandle'],
                    'eventSource': 'aws:sqs',
                    'awsRegion': 'us-east-1'
                } for m in messages
            ]
        }

        # Sustituir call_groq por una versión determinista para pruebas
        def fake_call_groq(sintomas):
            return {
                'urgencia': 'MODERADO',
                'riesgo': 50,
                'especialidad': 'Medicina General',
                'alerta': '',
                'recomendacion': 'Evaluar en 24 horas',
                'justificacion': 'Síntomas moderados de ejemplo'
            }
        processor.call_groq = fake_call_groq

        # Invocar handler
        try:
            processor.handler(lambda_event, None)
        except Exception as e:
            print('processor raised:', e)

        # Borrar mensajes procesados
        for m in messages:
            sqs.delete_message(QueueUrl=mainq_url, ReceiptHandle=m['ReceiptHandle'])

    # Llamar al getter para obtener resultados
    print('Llamando a getter.handler para jobId=', job_id)
    get_event = {'pathParameters': {'jobId': job_id}}
    get_resp = getter.handler(get_event, None)
    print('Respuesta getter statusCode:', get_resp.get('statusCode'))
    print('Body:', get_resp.get('body'))

if __name__ == '__main__':
    main()
