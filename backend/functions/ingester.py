import json
import uuid
import csv
import boto3
import os
import base64
import re
from datetime import datetime, timezone

dynamodb = boto3.resource('dynamodb')
sqs = boto3.client('sqs')

jobs_table = dynamodb.Table(os.environ['JOBS_TABLE'])
patients_table = dynamodb.Table(os.environ['PATIENTS_TABLE'])
sqs_queue_url = os.environ['SQS_QUEUE_URL']


def extract_csv_from_multipart(body, content_type):
    # Extraer boundary
    boundary_match = re.search(r'boundary=(.+)', content_type)
    if not boundary_match:
        return body
    
    boundary = boundary_match.group(1).strip()
    
    # Buscar el contenido del archivo
    parts = body.split(f'--{boundary}')
    for part in parts:
        if 'filename=' in part and 'Content-Type' in part:
            # Extraer solo el contenido después de los headers
            content_start = part.find('\r\n\r\n')
            if content_start == -1:
                content_start = part.find('\n\n')
                if content_start != -1:
                    return part[content_start + 2:].strip()
            else:
                return part[content_start + 4:].strip()
    
    return body


def handler(event, context):
    print("EVENT HEADERS:", json.dumps(dict(list(event.get('headers', {}).items())[:5])))
    
    try:
        body = event.get('body', '')
        content_type = event.get('headers', {}).get('content-type', '')
        
        # Decodificar base64 si es necesario
        if event.get('isBase64Encoded', False):
            body = base64.b64decode(body).decode('utf-8')
        
        # Si es multipart, extraer el CSV
        if 'multipart/form-data' in content_type:
            body = extract_csv_from_multipart(body, content_type)
        
        print("CSV BODY PREVIEW:", body[:200])
        
        # Parsear CSV
        lines = body.strip().split('\n')
        lines = [l.strip() for l in lines if l.strip()]
        reader = csv.DictReader(lines)
        patients = list(reader)

        print(f"PATIENTS COUNT: {len(patients)}")

        if not patients:
            return response(400, {'error': 'CSV vacío o inválido'})

        if len(patients) > 30:
            return response(400, {'error': 'Máximo 30 pacientes por batch'})

        job_id = str(uuid.uuid4())
        total = len(patients)
        timestamp = datetime.now(timezone.utc).isoformat()

        # Crear Job con status CREATING
        jobs_table.put_item(Item={
            'jobId': job_id,
            'totalPatients': total,
            'processedPatients': 0,
            'status': 'CREATING',
            'timestamp': timestamp
        })

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

                patients_table.put_item(Item={
                    'jobId': job_id,
                    'patientId': patient_id,
                    'nombre': nombre,
                    'sintomas': sintomas,
                    'status': 'PENDING',
                    'timestamp': timestamp
                })

            except Exception as e:
                print(f"SQS ERROR: {str(e)}")
                failed = True
                break

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
        print(f"ERROR: {str(e)}")
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
