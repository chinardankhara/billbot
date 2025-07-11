"""
Status Updater Lambda Function for Stripe Webhooks
Handles payment_intent.succeeded events to update invoice status to PAID
"""

import json
import os
import boto3
import stripe
from datetime import datetime
from typing import Dict, Any, Optional
from botocore.exceptions import ClientError


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler for Stripe webhook events
    
    This function handles incoming Stripe webhooks to update invoice status
    when payments succeed. It performs the following steps:
    
    1. Verify webhook signature for security
    2. Process payment_intent.succeeded events
    3. Query DynamoDB using PaymentIntentIndex GSI
    4. Update invoice status to PAID
    
    Infrastructure Requirements (see comments below for setup details):
    - API Gateway HTTP API endpoint (POST /webhooks/stripe)
    - Endpoint URL registered in Stripe Dashboard webhooks
    - STRIPE_WEBHOOK_SECRET environment variable
    - DynamoDB table with PaymentIntentIndex GSI
    
    Args:
        event: API Gateway event containing webhook payload
        context: Lambda context object
        
    Returns:
        Dict with HTTP response for API Gateway
    """
    
    print("🔔 Stripe webhook received")
    
    try:
        # Extract webhook data from API Gateway event
        headers = event.get('headers', {})
        body = event.get('body', '')
        
        # Get Stripe signature header (case-insensitive lookup)
        stripe_signature = None
        for key, value in headers.items():
            if key.lower() == 'stripe-signature':
                stripe_signature = value
                break
        
        if not stripe_signature:
            print("❌ Missing Stripe-Signature header")
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing Stripe-Signature header'})
            }
        
        # Verify webhook signature and construct event
        webhook_event = verify_webhook_signature(body, stripe_signature)
        if not webhook_event:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Invalid webhook signature'})
            }
        
        print(f"✅ Webhook signature verified. Event type: {webhook_event['type']}")
        
        # Process the webhook event
        result = process_webhook_event(webhook_event)
        
        if result['success']:
            print(f"✅ Webhook processed successfully")
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Webhook processed successfully',
                    'details': result
                })
            }
        else:
            print(f"⚠️ Webhook processing failed: {result.get('error')}")
            return {
                'statusCode': 200,  # Return 200 to acknowledge receipt
                'body': json.dumps({
                    'message': 'Webhook acknowledged but processing failed',
                    'error': result.get('error')
                })
            }
            
    except Exception as e:
        error_msg = f"Error processing webhook: {str(e)}"
        print(f"❌ {error_msg}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': error_msg})
        }


def verify_webhook_signature(payload: str, signature: str) -> Optional[Dict[str, Any]]:
    """
    Verify Stripe webhook signature for security
    
    This is a critical security step that ensures the webhook came from Stripe
    and prevents forged requests from malicious actors.
    
    Args:
        payload: Raw webhook payload
        signature: Stripe-Signature header value
        
    Returns:
        Parsed webhook event if valid, None if invalid
    """
    
    # Get webhook signing secret from environment
    webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')
    if not webhook_secret:
        print("❌ STRIPE_WEBHOOK_SECRET environment variable not set")
        return None
    
    try:
        # Use Stripe's built-in signature verification
        event = stripe.Webhook.construct_event(
            payload, signature, webhook_secret
        )
        return event
        
    except ValueError as e:
        print(f"❌ Invalid payload: {e}")
        return None
    except stripe.error.SignatureVerificationError as e:
        print(f"❌ Invalid signature: {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error verifying signature: {e}")
        return None


def process_webhook_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process the verified webhook event
    
    Args:
        event: Verified Stripe webhook event
        
    Returns:
        Dict with processing result
    """
    
    event_type = event['type']
    
    # We only care about successful payment intents
    if event_type != 'payment_intent.succeeded':
        print(f"ℹ️ Ignoring event type: {event_type}")
        return {
            'success': True,
            'message': f'Event type {event_type} ignored (not payment_intent.succeeded)',
            'action': 'ignored'
        }
    
    # Extract payment intent data
    payment_intent = event['data']['object']
    payment_intent_id = payment_intent['id']
    amount = payment_intent['amount']  # Amount in cents
    currency = payment_intent['currency']
    
    print(f"💰 Payment succeeded: {payment_intent_id}")
    print(f"   Amount: {amount} {currency}")
    
    # Update the corresponding invoice in DynamoDB
    return update_invoice_status(payment_intent_id, payment_intent)


def update_invoice_status(payment_intent_id: str, payment_intent: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update invoice status to PAID using PaymentIntentIndex GSI
    
    Args:
        payment_intent_id: Stripe Payment Intent ID
        payment_intent: Full payment intent object from webhook
        
    Returns:
        Dict with update result
    """
    
    # Get DynamoDB table name from environment
    table_name = os.getenv('DYNAMODB_TABLE_NAME')
    if not table_name:
        return {
            'success': False,
            'error': 'DYNAMODB_TABLE_NAME environment variable not set'
        }
    
    # Initialize DynamoDB
    region = os.getenv('AWS_REGION', 'us-east-1')
    dynamodb = boto3.resource('dynamodb', region_name=region)
    table = dynamodb.Table(table_name)
    
    try:
        # Query the PaymentIntentIndex GSI to find the invoice
        print(f"🔍 Querying PaymentIntentIndex for payment_intent_id: {payment_intent_id}")
        
        response = table.query(
            IndexName='PaymentIntentIndex',
            KeyConditionExpression='payment_intent_id = :payment_id',
            ExpressionAttributeValues={
                ':payment_id': payment_intent_id
            }
        )
        
        items = response.get('Items', [])
        
        if not items:
            error_msg = f"No invoice found for payment_intent_id: {payment_intent_id}"
            print(f"❌ {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'payment_intent_id': payment_intent_id
            }
        
        if len(items) > 1:
            print(f"⚠️ Multiple invoices found for payment_intent_id: {payment_intent_id}")
        
        # Update the first (should be only) invoice found
        invoice = items[0]
        processed_invoice_uuid = invoice['processed_invoice_uuid']
        
        print(f"📄 Found invoice: {processed_invoice_uuid}")
        print(f"   Vendor: {invoice.get('vendor_name', 'Unknown')}")
        print(f"   Invoice ID: {invoice.get('invoice_id', 'Unknown')}")
        print(f"   Current status: {invoice.get('processing_status', 'Unknown')}")
        
        # Update invoice status to PAID
        update_timestamp = datetime.utcnow().isoformat() + 'Z'
        
        update_response = table.update_item(
            Key={'processed_invoice_uuid': processed_invoice_uuid},
            UpdateExpression='SET processing_status = :status, last_updated = :timestamp, payment_succeeded_at = :payment_time',
            ExpressionAttributeValues={
                ':status': 'PAID',
                ':timestamp': update_timestamp,
                ':payment_time': update_timestamp
            },
            ReturnValues='UPDATED_NEW'
        )
        
        print(f"✅ Invoice status updated to PAID")
        print(f"   UUID: {processed_invoice_uuid}")
        print(f"   Payment Intent: {payment_intent_id}")
        print(f"   Timestamp: {update_timestamp}")
        
        return {
            'success': True,
            'message': 'Invoice status updated to PAID',
            'processed_invoice_uuid': processed_invoice_uuid,
            'payment_intent_id': payment_intent_id,
            'updated_attributes': update_response.get('Attributes', {}),
            'action': 'updated'
        }
        
    except ClientError as e:
        error_msg = f"DynamoDB error: {e.response['Error']['Message']}"
        print(f"❌ {error_msg}")
        return {
            'success': False,
            'error': error_msg,
            'payment_intent_id': payment_intent_id
        }
    except Exception as e:
        error_msg = f"Unexpected error updating invoice: {str(e)}"
        print(f"❌ {error_msg}")
        return {
            'success': False,
            'error': error_msg,
            'payment_intent_id': payment_intent_id
        }
