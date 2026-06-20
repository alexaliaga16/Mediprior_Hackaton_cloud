import json
import boto3
import os
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource('dynamodb')

jobs_table = dynamodb.Table(os.environ['JOBS_TABLE'])
patients_table = dynamodb.Table(os.environ['PATIENTS_TABLE'])


def handler(event, context):
    try:
        job_id = event['pathParameters']['jobId']

        # Obtener Job
        job_result = jobs_table.get_item(Key={'jobId': job_id})
        job = job_result.get('Item')

        if not job:
            return response(404, {'error': 'Job no encontrado'})

        # Obtener todos los pacientes del job
        patients_result = patients_table.query(
            KeyConditionExpression=Key('jobId').eq(job_id)
        )
        patients = patients_result.get('Items', [])

        # Convertir Decimal a int/float para JSON
        job = deserialize(job)
        patients = [deserialize(p) for p in patients]

        # Ordenar por urgencia: CRITICO primero
        order = {'CRITICO': 0, 'MODERADO': 1, 'LEVE': 2}
        patients.sort(key=lambda x: order.get(x.get('urgencia', 'LEVE'), 3))

        return response(200, {
            'job': job,
            'patients': patients
        })

    except Exception as e:
        return response(500, {'error': str(e)})


def deserialize(obj):
    if isinstance(obj, dict):
        return {k: deserialize(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [deserialize(i) for i in obj]
    elif hasattr(obj, '__class__') and obj.__class__.__name__ == 'Decimal':
        return int(obj) if obj % 1 == 0 else float(obj)
    return obj


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
