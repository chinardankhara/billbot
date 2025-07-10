"""
AWS Lambda handler for Stripe webhook status updates
Processes payment_intent.succeeded events to update invoice status
"""

import json
import os
from typing import Dict, Any

# Import our core business logic
# Files are copied to Lambda root, so we import directly by filename
from app import lambda_handler as status_updater_handler


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda entry point for status updater
    
    This function receives Stripe webhooks via API Gateway and delegates
    to the status_updater business logic to process payment status updates.
    
    Expected event format from API Gateway:
    {
        "headers": {
            "stripe-signature": "t=1234567890,v1=abc123..."
        },
        "body": "{\"id\": \"evt_...\", \"type\": \"payment_intent.succeeded\", ...}"
    }
    
    Environment Variables Required:
    - STRIPE_WEBHOOK_SECRET: Webhook signing secret from Stripe Dashboard
    - DYNAMODB_TABLE_NAME: Name of the invoices DynamoDB table
    - AWS_REGION: AWS region (auto-populated by Lambda)
    
    Returns:
        HTTP response dict for API Gateway
    """
    
    try:
        # Delegate to the main business logic
        return status_updater_handler(event, context)
        
    except Exception as e:
        error_msg = f"Error in Lambda handler: {str(e)}"
        print(error_msg)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': error_msg})
        } 