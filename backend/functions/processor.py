import json
import boto3
import os
from groq import Groq
from datetime import datetime, timezone

dynamodb = boto3.resource('dynamodb')

jobs_table = dynamodb.Table(os.environ['JOBS_TABLE'])
patients_table = dynamodb.Table(os.environ['PATIENTS_TABLE'])

client = Groq(api_key=os.environ['GROQ_API_KEY'])

PROMPT_TEMPLATE = """Eres un asistente de priorizacion clinica para postas medicas rurales del Peru.
NO diagnosticas enfermedades. UNICAMENTE priorizas pacientes para atencion temprana.

Dado el siguiente reporte de sintomas en texto libre, responde UNICAMENTE con JSON valido.
Sin texto adicional, sin markdown, sin explicaciones, sin bloques de codigo.

Sintomas: {sintomas}

Responde exactamente con esta estructura JSON:
{{
  "urgencia": "CRITICO o MODERADO o LEVE",
  "riesgo": numero entre 0 y 100,
  "especialidad": "nombre de especialidad medica",
  "alerta": "diagnostico presuntivo breve",
  "recomendacion": "accion inmediata recomendada",
  "justificacion": "explicacion clinica breve de por que esta prioridad"
}}"""


def call_groq(sintomas):
    prompt = PROMPT_TEMPLATE.format(sintomas=sintomas)

    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=500
    )

    content = completion.choices[0].message.content.strip()
    return json.loads(content)


def update_job_progress(job_id):
    result = jobs_table.update_item(
        Key={'jobId': job_id},
        UpdateExpression='SET processedPatients = processedPatients + :inc',
        ExpressionAttributeValues={':inc': 1},
        ReturnValues='ALL_NEW'
    )
    attrs = result['Attributes']
    processed = int(attrs['processedPatients'])
    total = int(attrs['totalPatients'])

    if processed >= total:
        jobs_table.update_item(
            Key={'jobId': job_id},
            UpdateExpression='SET #s = :s',
            ExpressionAttributeNames={'#s': 'status'},
            ExpressionAttributeValues={':s': 'COMPLETED'}
        )


def handler(event, context):
    for record in event['Records']:
        message = json.loads(record['body'])
        job_id = message['jobId']
        patient_id = message['patientId']
        sintomas = message['sintomas']

        try:
            groq_result = call_groq(sintomas)

            urgencia = groq_result.get('urgencia', 'LEVE').upper()
            if urgencia not in ['CRITICO', 'MODERADO', 'LEVE']:
                urgencia = 'LEVE'

            patients_table.update_item(
                Key={'jobId': job_id, 'patientId': patient_id},
                UpdateExpression='''SET
                    urgencia = :u,
                    riesgo = :r,
                    especialidad = :e,
                    alerta = :a,
                    recomendacion = :rec,
                    justificacion = :j,
                    #s = :s,
                    updatedAt = :t
                ''',
                ExpressionAttributeNames={'#s': 'status'},
                ExpressionAttributeValues={
                    ':u': urgencia,
                    ':r': int(groq_result.get('riesgo', 50)),
                    ':e': groq_result.get('especialidad', 'Medicina General'),
                    ':a': groq_result.get('alerta', ''),
                    ':rec': groq_result.get('recomendacion', ''),
                    ':j': groq_result.get('justificacion', ''),
                    ':s': 'DONE',
                    ':t': datetime.now(timezone.utc).isoformat()
                }
            )

        except Exception as e:
            patients_table.update_item(
                Key={'jobId': job_id, 'patientId': patient_id},
                UpdateExpression='SET #s = :s, errorMsg = :e',
                ExpressionAttributeNames={'#s': 'status'},
                ExpressionAttributeValues={
                    ':s': 'FAILED',
                    ':e': str(e)
                }
            )
            raise e

        finally:
            update_job_progress(job_id)
