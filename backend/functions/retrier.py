import json
import boto3
import os

sqs = boto3.client('sqs')

dlq_url = os.environ['DLQ_URL']
main_queue_url = os.environ['SQS_QUEUE_URL']


def handler(event, context):
    try:
        requeued = 0
        
        while True:
            # Leer mensajes de la DLQ en lotes de 10
            response = sqs.receive_message(
                QueueUrl=dlq_url,
                MaxNumberOfMessages=10,
                WaitTimeSeconds=1
            )
            
            messages = response.get('Messages', [])
            if not messages:
                break
            
            for msg in messages:
                # Reenviar a la cola principal
                sqs.send_message(
                    QueueUrl=main_queue_url,
                    MessageBody=msg['Body']
                )
                
                # Eliminar de la DLQ
                sqs.delete_message(
                    QueueUrl=dlq_url,
                    ReceiptHandle=msg['ReceiptHandle']
                )
                
                requeued += 1

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'requeued': requeued,
                'message': f'{requeued} pacientes reenviados para reprocesamiento'
            })
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': str(e)})
        }

