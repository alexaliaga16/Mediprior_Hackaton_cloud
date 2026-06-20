import json
import os
import boto3
from boto3.dynamodb.conditions import Key
from decimal import Decimal

dynamodb = boto3.resource("dynamodb")
jobs_table = dynamodb.Table(os.environ["JOBS_TABLE"])
patients_table = dynamodb.Table(os.environ["PATIENTS_TABLE"])


def deserialize(obj):
    if isinstance(obj, dict):
        return {k: deserialize(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [deserialize(i) for i in obj]
    elif isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    return obj


def calculate_metrics(patients):
    critical = 0
    moderate = 0
    mild = 0
    for patient in patients:
        urgency = patient.get("urgencia", "")
        if urgency == "CRITICO":
            critical += 1
        elif urgency == "MODERADO":
            moderate += 1
        elif urgency == "LEVE":
            mild += 1
    return {
        "critical": critical,
        "moderate": moderate,
        "mild": mild
    }


def get_job(job_id):
    response = jobs_table.get_item(Key={"jobId": job_id})
    return response.get("Item")


def get_patients(job_id):
    response = patients_table.query(
        KeyConditionExpression=Key("jobId").eq(job_id)
    )
    return response.get("Items", [])


def handler(event, context):
    try:
        job_id = event["pathParameters"]["jobId"]

        job = get_job(job_id)
        if not job:
            return {
                "statusCode": 404,
                "headers": {"Access-Control-Allow-Origin": "*"},
                "body": json.dumps({"message": "Job not found"})
            }

        patients = get_patients(job_id)

        # Deserializar Decimals de DynamoDB
        job = deserialize(job)
        patients = [deserialize(p) for p in patients]

        # Ordenar por riesgo descendente
        patients.sort(key=lambda x: x.get("riesgo", 0), reverse=True)

        metrics = calculate_metrics(patients)

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "job": job,
                "metrics": metrics,
                "patients": patients
            })
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"message": str(e)})
        }
