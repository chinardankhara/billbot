"""
AWS Lambda handler for email classification
Processes S3 events and sends results to SQS
"""

import json
import boto3
import os
from email_classifier import EmailClassifier


def lambda_handler(event, context):
    """
    AWS Lambda handler function
    
    Supports:
    - S3 events (when email is uploaded to S3)
    - Direct invocation with email content
    """
    
    try:
        # Initialize classifier
        classifier = EmailClassifier()
        
        # Determine event type and process accordingly
        if 'Records' in event and event['Records'][0]['eventSource'] == 'aws:s3':
            return handle_s3_event(event, classifier, context)
        elif 'email_content' in event:
            return handle_direct_invocation(event, classifier)
        else:
            raise ValueError("Unsupported event format. Expected S3 event or direct invocation with 'email_content'.")
            
    except Exception as e:
        error_msg = f"Error processing event: {str(e)}"
        print(error_msg)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': error_msg})
        }


def handle_s3_event(event, classifier, context):
    """Handle S3 bucket events (when email files are uploaded)"""
    
    s3_client = boto3.client('s3')
    sqs_url = os.getenv('SQS_URL')
    sqs_client = boto3.client('sqs') if sqs_url else None
    
    results = []
    
    for record in event['Records']:
        bucket_name = record['s3']['bucket']['name']
        object_key = record['s3']['object']['key']
        
        print(f"Processing email: s3://{bucket_name}/{object_key}")
        
        try:
            response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
            email_content = response['Body'].read()
            
            classification_result = classifier.classify_email_content(email_content)
            
            result = {
                'bucket': bucket_name,
                'key': object_key,
                'classification': classification_result.classification,
                'reasoning': classification_result.reasoning,
                'aws_request_id': context.aws_request_id if context else 'unknown'
            }
            results.append(result)
            print(f"Classification successful: {classification_result.classification}")
            
            if sqs_client:
                sqs_client.send_message(
                    QueueUrl=sqs_url,
                    MessageBody=json.dumps(result)
                )
                print(f"Successfully sent result to SQS.")
            
        except Exception as e:
            error_msg = f"Error classifying {object_key}: {str(e)}"
            print(error_msg)
            results.append({'bucket': bucket_name, 'key': object_key, 'error': error_msg})
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': f'Processed {len(results)} email(s)',
            'results': results
        })
    }


def handle_direct_invocation(event, classifier):
    """Handle direct function invocation with email content"""
    
    email_content = event['email_content']
    classification_result = classifier.classify_email_content(email_content)
    
    result = {
        'classification': classification_result.classification,
        'reasoning': classification_result.reasoning
    }
    
    print(f"Direct invocation classification successful: {classification_result.classification}")
    
    return {
        'statusCode': 200,
        'body': json.dumps(result)
    } 