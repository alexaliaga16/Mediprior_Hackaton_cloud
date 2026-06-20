"""
en processor.py hace:

from utils.job_progress import increment_processed_patients

increment_processed_patients(
    jobs_table,
    job_id
)
"""

def increment_processed_patients(jobs_table, job_id):

    response = jobs_table.update_item(
        Key={
            "jobId": job_id
        },
        UpdateExpression="ADD processedPatients :inc",
        ExpressionAttributeValues={
            ":inc": 1
        },
        ReturnValues="ALL_NEW"
    )

    updated_job = response["Attributes"]

    if (
        updated_job["processedPatients"]
        >= updated_job["totalPatients"]
    ):

        jobs_table.update_item(
            Key={
                "jobId": job_id
            },
            UpdateExpression="SET #s = :completed",
            ExpressionAttributeNames={
                "#s": "status"
            },
            ExpressionAttributeValues={
                ":completed": "COMPLETED"
            }
        )

    return updated_job