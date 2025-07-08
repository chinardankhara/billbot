"""
DynamoDB writer for invoice data
"""

import boto3
import uuid
from datetime import datetime
from typing import Optional
from botocore.exceptions import ClientError

from .extractor import InvoiceExtractionResult


class InvoiceDynamoWriter:
    """Handles writing extracted invoice data to DynamoDB"""
    
    def __init__(self, table_name: str, region_name: str = 'us-east-1'):
        """
        Initialize the DynamoDB writer.
        
        Args:
            table_name: Name of the DynamoDB table
            region_name: AWS region for DynamoDB
        """
        self.table_name = table_name
        self.dynamodb = boto3.resource('dynamodb', region_name=region_name)
        self.table = self.dynamodb.Table(table_name)
    
    def write_invoice(
        self,
        extraction_result: InvoiceExtractionResult,
        s3_bucket: str,
        s3_key: str,
        aws_request_id: str
    ) -> dict:
        """
        Write extracted invoice data to DynamoDB.
        
        Args:
            extraction_result: Result from invoice extraction
            s3_bucket: Source S3 bucket
            s3_key: Source S3 object key
            aws_request_id: Original classification request ID
            
        Returns:
            dict: Response from DynamoDB put_item operation
        """
        # Generate UUID for this invoice record
        processed_invoice_uuid = str(uuid.uuid4())
        
        # Current timestamp
        received_timestamp = datetime.utcnow().isoformat() + 'Z'
        
        # Prepare the item for DynamoDB
        item = {
            'processed_invoice_uuid': processed_invoice_uuid,
            'processing_status': 'RECEIVED',
            's3_original_key': s3_key,
            'received_timestamp': received_timestamp
        }
        
        # Add extracted data if extraction was successful
        if extraction_result.extraction_successful:
            if extraction_result.vendor_name:
                item['vendor_name'] = extraction_result.vendor_name
            if extraction_result.invoice_id:
                item['invoice_id'] = extraction_result.invoice_id
            if extraction_result.due_date:
                item['due_date'] = extraction_result.due_date
            if extraction_result.total_amount:
                item['total_amount'] = extraction_result.total_amount
            if extraction_result.currency:
                item['currency'] = extraction_result.currency
        
        # Add metadata
        item['extraction_successful'] = extraction_result.extraction_successful
        item['s3_bucket'] = s3_bucket
        item['classification_request_id'] = aws_request_id
        
        try:
            response = self.table.put_item(Item=item)
            print(f"Successfully wrote invoice to DynamoDB: {processed_invoice_uuid}")
            return {
                'success': True,
                'processed_invoice_uuid': processed_invoice_uuid,
                'dynamodb_response': response
            }
            
        except ClientError as e:
            error_msg = f"Failed to write to DynamoDB: {e.response['Error']['Message']}"
            print(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'processed_invoice_uuid': processed_invoice_uuid
            }
    
    def update_processing_status(
        self,
        processed_invoice_uuid: str,
        new_status: str
    ) -> dict:
        """
        Update the processing status of an invoice.
        
        Args:
            processed_invoice_uuid: The UUID of the invoice record
            new_status: New processing status (e.g., 'PAYMENT_SUBMITTED', 'PAID')
            
        Returns:
            dict: Response from DynamoDB update operation
        """
        try:
            response = self.table.update_item(
                Key={'processed_invoice_uuid': processed_invoice_uuid},
                UpdateExpression='SET processing_status = :status',
                ExpressionAttributeValues={':status': new_status},
                ReturnValues='UPDATED_NEW'
            )
            print(f"Updated status for {processed_invoice_uuid} to {new_status}")
            return {
                'success': True,
                'updated_attributes': response.get('Attributes', {})
            }
            
        except ClientError as e:
            error_msg = f"Failed to update status: {e.response['Error']['Message']}"
            print(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    def get_invoice(self, processed_invoice_uuid: str) -> Optional[dict]:
        """
        Retrieve an invoice record by UUID.
        
        Args:
            processed_invoice_uuid: The UUID of the invoice record
            
        Returns:
            dict or None: The invoice record if found
        """
        try:
            response = self.table.get_item(
                Key={'processed_invoice_uuid': processed_invoice_uuid}
            )
            return response.get('Item')
            
        except ClientError as e:
            print(f"Failed to get invoice: {e.response['Error']['Message']}")
            return None 