import json
import uuid
import csv
import boto3
import os
from datetime import datetime, timezone

dynamodb = boto3.resource('dynamodb')
sqs = boto3.client('sqs')

jobs_table = dynamodb.Table(os.environ['JOBS_TABLE'])
patients_table = dynamodb.Table(os.environ['PATIENTS_TABLE'])
sqs_queue_url = os.environ['SQS_QUEUE_URL']


def handler(event, context):
    try:
        # Parsear el body
        body = event.get('body', '')
        if event.get('isBase64Encoded', False):
            import base64
            body = base64.b64decode(body).decode('utf-8')

        # Parsear CSV
        lines = body.strip().split('\n')
        reader = csv.DictReader(lines)
        patients = list(reader)

        if not patients:
            return response(400, {'error': 'CSV vacío o inválido'})

        if len(patients) > 30:
            return response(400, {'error': 'Máximo 30 pacientes por batch'})

        # Generar jobId
        job_id = str(uuid.uuid4())
        total = len(patients)
        timestamp = datetime.now(timezone.utc).isoformat()

        # 1. Crear Job con status CREATING
        jobs_table.put_item(Item={
            'jobId': job_id,
            'totalPatients': total,
            'processedPatients': 0,
            'status': 'CREATING',
            'timestamp': timestamp
        })

        # 2. Enviar mensajes a SQS
        failed = False
        for patient in patients:
            patient_id = str(uuid.uuid4())
            nombre = patient.get('nombre', '').strip()
            sintomas = patient.get('sintomas', '').strip()

            if not nombre or not sintomas:
                continue

            message = {
                'jobId': job_id,
                'patientId': patient_id,
                'nombre': nombre,
                'sintomas': sintomas
            }

            try:
                sqs.send_message(
                    QueueUrl=sqs_queue_url,
                    MessageBody=json.dumps(message)
                )

                # Crear registro PENDING en Patients
                patients_table.put_item(Item={
                    'jobId': job_id,
                    'patientId': patient_id,
                    'nombre': nombre,
                    'sintomas': sintomas,
                    'status': 'PENDING',
                    'timestamp': timestamp
                })

            except Exception as e:
                failed = True
                break

        # 3. Actualizar status del Job
        if failed:
            jobs_table.update_item(
                Key={'jobId': job_id},
                UpdateExpression='SET #s = :s',
                ExpressionAttributeNames={'#s': 'status'},
                ExpressionAttributeValues={':s': 'FAILED'}
            )
            return response(500, {'error': 'Error enviando mensajes a SQS'})

        jobs_table.update_item(
            Key={'jobId': job_id},
            UpdateExpression='SET #s = :s',
            ExpressionAttributeNames={'#s': 'status'},
            ExpressionAttributeValues={':s': 'PROCESSING'}
        )

        return response(200, {
            'jobId': job_id,
            'totalPatients': total,
            'status': 'PROCESSING'
        })

    except Exception as e:
        return response(500, {'error': str(e)})


def response(status_code, body):
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Methods': 'POST, GET, OPTIONS'
        },
        'body': json.dumps(body)
    }
