import os
import json
import boto3
import csv
import uuid
from datetime import datetime
from django.conf import settings

from rest_framework.response import Response
from rest_framework import status

from botocore import exceptions

def trigger_sanitizer(run, refined_epsilons):
 
    event = {
        "job_id": str(run.job.id),
        "run_id": run.run_id,
        "user_email": run.job.user.email,
        "use_default_epsilon": False,    
        "epsilons": refined_epsilons
    }
            
    try:
        # invoke engine
        client = boto3.client(
            "lambda", 
            region_name = os.getenv('AWS_S3_REGION_NAME'),
            aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        )

        response = client.invoke(
            FunctionName = settings.AWS_SANITIZER_LAMBDA,
            Payload = json.dumps(event).encode(),
            InvocationType="Event"
        )
        return Response(response, status=status.HTTP_200_OK)
    except exceptions.ClientError as e:
        print("lambda exception")
        error_response = e.response
        #error_code = error_response['Error']['Code']
        error_message = error_response['Error']['Message']
        return Response({'error': error_message}, status=status.HTTP_400_BAD_REQUEST)


def compute_cost(refined_statistics):
    """Compute the total cost of the refined statistics. Refined_statistics is a json
        encoded string."""
    cost = 0
    for statistic in refined_statistics:
        cost = cost + statistic['epsilon']
    return cost

def create_presigned_url(file_path):
    s3 = boto3.client('s3', config=boto3.session.Config(signature_version='s3v4'), aws_access_key_id=settings.AWS_ACCESS_KEY_ID, aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)

    # The name of your S3 bucket
    bucket_name = settings.AWS_STORAGE_BUCKET_NAME

    # The name of the object you want to generate a signed URL for
    object_name = f'{file_path}'

    # The duration (in seconds) that the signed URL should be valid for
    expiration = 3600*24*3

    # Generate a signed URL for the object
    url = s3.generate_presigned_url(
        ClientMethod='get_object',
        Params={
            'Bucket': bucket_name,
            'Key': object_name
        },
        ExpiresIn=expiration,
        HttpMethod='GET'
    )

    print(f'Signed URL for {object_name}: {url}')
    return url

def send_email_to_user(signed_url, user):
    # Create an SES client
    client = boto3.client('ses', region_name='us-east-1')

    # Specify the email details
    sender = 'staylor@urban.org'
    recipient = user.email
    subject = 'Validation Server Data Release'
    body = f'Dear {user.first_name} {user.last_name}, \n\n \
        Please find your results for download here: \n\n \
        {signed_url}.'

    # Send the email
    response = client.send_email(
        Source=sender,
        Destination={
            'ToAddresses': [
                recipient,
            ],
        },
        Message={
            'Subject': {
                'Data': subject,
            },
            'Body': {
                'Text': {
                    'Data': body,
                },
            },
        },
    )

    print(response)



def generate_unique_filename(extension):
    """
    Generate a unique filename by combining a timestamp and a random string.
    """
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    random_string = uuid.uuid4().hex
    filename = f'{timestamp}_{random_string}{extension}'
    return filename

def get_file_path_for_release(job_id, run_id):
    """Generate s3 path for released results."""
    filename = generate_unique_filename(".csv")
    return os.path.join("release", f'{job_id}', f'{run_id}', os.path.basename(filename))




def upload_csv_to_s3(csv_buffer, filename):
    """Upload csv file to S3"""
    s3 = boto3.client('s3', aws_access_key_id=settings.AWS_ACCESS_KEY_ID, aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)

    s3.put_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, 
                Key=filename, 
                Body=csv_buffer.getvalue(),
                ServerSideEncryption=settings.AWS_S3_OBJECT_PARAMETERS["ServerSideEncryption"],
                SSEKMSKeyId=settings.AWS_S3_OBJECT_PARAMETERS["SSEKMSKeyId"]
        )

