"""
AWS Lambda handler for invoice data extraction
Processes SQS messages from email classification and extracts invoice data
"""

import json
import boto3
import os
from typing import Dict, Any

# Import our core business logic  
# Note: Files are copied to Lambda root, so we import directly by filename
from invoice_extractor import InvoiceExtractor
from dynamo_writer import InvoiceDynamoWriter


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler function for invoice extraction
    
    Processes SQS messages containing classification results.
    Only processes messages where classification = "INVOICE"
    """
    
    # Get required environment variables
    table_name = os.getenv('DYNAMODB_TABLE_NAME')
    if not table_name:
        raise ValueError("DYNAMODB_TABLE_NAME environment variable is required")
    
    region = os.getenv('AWS_REGION', 'us-east-1')
    
    try:
        # Initialize extractor and DynamoDB writer
        extractor = InvoiceExtractor()
        dynamo_writer = InvoiceDynamoWriter(table_name, region)
        
        # Initialize S3 client for downloading email files
        s3_client = boto3.client('s3')
        
        # Process SQS records
        processed_count = 0
        extracted_count = 0
        
        for record in event['Records']:
            try:
                # Parse the SQS message body
                message_body = json.loads(record['body'])
                
                print(f"Processing message: {message_body}")
                
                # Check if this is an invoice classification
                classification = message_body.get('classification')
                if classification != 'INVOICE':
                    print(f"Skipping non-invoice classification: {classification}")
                    processed_count += 1
                    continue
                
                # Extract required fields from the message
                bucket = message_body.get('bucket')
                key = message_body.get('key')
                aws_request_id = message_body.get('aws_request_id', 'unknown')
                
                if not bucket or not key:
                    print(f"Missing bucket or key in message: {message_body}")
                    processed_count += 1
                    continue
                
                print(f"Processing invoice: s3://{bucket}/{key}")
                
                # Download email content from S3
                response = s3_client.get_object(Bucket=bucket, Key=key)
                email_content = response['Body'].read()
                
                # Extract invoice data
                extraction_result = extractor.extract_from_email_content(email_content)
                
                print(f"Extraction result: success={extraction_result.extraction_successful}")
                if extraction_result.extraction_successful:
                    print(f"Extracted data: vendor={extraction_result.vendor_name}, "
                          f"invoice_id={extraction_result.invoice_id}, "
                          f"amount={extraction_result.total_amount}")
                
                # Write to DynamoDB
                write_result = dynamo_writer.write_invoice(
                    extraction_result=extraction_result,
                    s3_bucket=bucket,
                    s3_key=key,
                    aws_request_id=aws_request_id
                )
                
                if write_result['success']:
                    extracted_count += 1
                    print(f"Successfully processed invoice: {write_result['processed_invoice_uuid']}")
                else:
                    print(f"Failed to write to DynamoDB: {write_result.get('error')}")
                
                processed_count += 1
                
            except Exception as e:
                print(f"Error processing record: {str(e)}")
                print(f"Record: {record}")
                processed_count += 1
                continue
        
        # Return summary
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Processed {processed_count} message(s), extracted {extracted_count} invoice(s)',
                'processed_count': processed_count,
                'extracted_count': extracted_count
            })
        }
        
    except Exception as e:
        error_msg = f"Error in lambda handler: {str(e)}"
        print(error_msg)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': error_msg})
        }


def handle_direct_invocation(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle direct function invocation for testing
    
    Expected event format:
    {
        "test_message": {
            "bucket": "test-bucket",
            "key": "test-email.txt", 
            "classification": "INVOICE",
            "aws_request_id": "test-123"
        }
    }
    """
    test_message = event.get('test_message')
    if not test_message:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'test_message required for direct invocation'})
        }
    
    # Simulate SQS event structure
    simulated_event = {
        'Records': [{
            'body': json.dumps(test_message)
        }]
    }
    
    return lambda_handler(simulated_event, None) 