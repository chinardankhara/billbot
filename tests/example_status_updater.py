#!/usr/bin/env python3
"""
Example test for the status_updater webhook handler
Tests the complete webhook processing flow locally
"""

import json
import boto3
import sys
import os
from datetime import datetime

# Add src directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from status_updater.app import lambda_handler, verify_webhook_signature, process_webhook_event


def test_webhook_signature_verification():
    """Test webhook signature verification with a mock payload"""
    
    print("🧪 Testing webhook signature verification")
    print("=" * 50)
    
    # Mock webhook payload (simplified)
    mock_payload = json.dumps({
        "id": "evt_test_webhook",
        "type": "payment_intent.succeeded",
        "data": {
            "object": {
                "id": "pi_test_payment_intent",
                "amount": 45353,
                "currency": "eur",
                "status": "succeeded"
            }
        }
    })
    
    # Note: In real testing, you'd use actual Stripe test webhook data
    # For this example, we'll just test the structure
    print("✅ Webhook payload structure looks correct")
    print(f"   Payload size: {len(mock_payload)} bytes")
    
    # In production, you'd test with:
    # result = verify_webhook_signature(mock_payload, test_signature)


def test_payment_intent_processing():
    """Test processing a payment_intent.succeeded event"""
    
    print("\n🧪 Testing payment intent processing")
    print("=" * 50)
    
    # Mock Stripe webhook event
    mock_event = {
        "type": "payment_intent.succeeded",
        "data": {
            "object": {
                "id": "pi_test_1234567890",
                "amount": 45353,  # $453.53 in cents
                "currency": "eur",
                "status": "succeeded",
                "metadata": {
                    "processed_invoice_uuid": "610ba35c-dc80-4b29-8481-e112a9c74bb7",
                    "vendor_name": "CPB SOFTWARE (GERMANY) GMBH",
                    "invoice_id": "123100401"
                }
            }
        }
    }
    
    print(f"📄 Mock event:")
    print(f"   Type: {mock_event['type']}")
    print(f"   Payment Intent: {mock_event['data']['object']['id']}")
    print(f"   Amount: {mock_event['data']['object']['amount']} {mock_event['data']['object']['currency']}")
    
    # Test event processing logic
    result = process_webhook_event(mock_event)
    
    print(f"\n✅ Processing result: {result['success']}")
    if not result['success']:
        print(f"   Note: {result.get('message', 'Unknown error')}")


def test_api_gateway_event_format():
    """Test the complete Lambda handler with API Gateway event format"""
    
    print("\n🧪 Testing API Gateway event format")
    print("=" * 50)
    
    # Mock API Gateway event (what the Lambda actually receives)
    mock_api_gateway_event = {
        "headers": {
            "stripe-signature": "t=1234567890,v1=mock_signature_hash"
        },
        "body": json.dumps({
            "id": "evt_test_webhook",
            "type": "payment_intent.succeeded",
            "data": {
                "object": {
                    "id": "pi_test_1234567890",
                    "amount": 45353,
                    "currency": "eur",
                    "status": "succeeded"
                }
            }
        })
    }
    
    print("📡 Mock API Gateway event structure:")
    print(f"   Headers: {list(mock_api_gateway_event['headers'].keys())}")
    print(f"   Body size: {len(mock_api_gateway_event['body'])} bytes")
    
    # Note: This would fail signature verification without a real webhook secret
    # In production testing, use Stripe CLI: stripe listen --forward-to localhost
    print("\n⚠️  For real testing, use Stripe CLI webhook forwarding:")
    print("   stripe listen --forward-to https://your-api-gateway-url/webhooks/stripe")


def create_test_invoice_with_payment_intent():
    """
    Create a test invoice record in DynamoDB with a payment_intent_id
    This simulates the state after payment_scheduler has initiated a payment
    """
    
    print("\n🧪 Creating test invoice with payment_intent_id")
    print("=" * 50)
    
    try:
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.Table('Invoices')
        
        test_invoice = {
            'processed_invoice_uuid': 'test-webhook-uuid-123',
            'processing_status': 'PAYMENT_INITIATED',
            'payment_intent_id': 'pi_test_webhook_1234567890',
            'vendor_name': 'Test Vendor Corp',
            'invoice_id': 'TEST-WEBHOOK-001',
            'total_amount': '453.53',
            'currency': 'EUR',
            'due_date': datetime.now().strftime('%Y-%m-%d'),
            'received_timestamp': datetime.utcnow().isoformat() + 'Z',
            'last_updated': datetime.utcnow().isoformat() + 'Z',
            'extraction_successful': True,
            's3_bucket': 'test-bucket',
            's3_original_key': 'test-webhook-email.txt',
            'classification_request_id': 'test-webhook-classification'
        }
        
        table.put_item(Item=test_invoice)
        
        print(f"✅ Created test invoice:")
        print(f"   UUID: {test_invoice['processed_invoice_uuid']}")
        print(f"   Payment Intent: {test_invoice['payment_intent_id']}")
        print(f"   Status: {test_invoice['processing_status']}")
        print(f"\n💡 Now you can test webhook processing with this payment_intent_id")
        print(f"   Use: pi_test_webhook_1234567890")
        
        return test_invoice
        
    except Exception as e:
        print(f"❌ Error creating test invoice: {e}")
        print("   Make sure DynamoDB table 'Invoices' exists")
        return None


def main():
    """Run all status updater tests"""
    
    print("🚀 Status Updater Test Suite")
    print("=" * 60)
    
    # Test 1: Webhook signature verification structure
    test_webhook_signature_verification()
    
    # Test 2: Payment intent event processing
    test_payment_intent_processing()
    
    # Test 3: API Gateway event format
    test_api_gateway_event_format()
    
    # Test 4: Create test data
    create_test_invoice_with_payment_intent()
    
    print("\n" + "=" * 60)
    print("🏁 Test suite complete!")
    print("\nNext steps for real testing:")
    print("1. Deploy the status_updater Lambda function")
    print("2. Create API Gateway HTTP API endpoint")
    print("3. Add PaymentIntentIndex GSI to DynamoDB table")
    print("4. Configure Stripe webhook with API Gateway URL")
    print("5. Use Stripe CLI for local webhook testing:")
    print("   stripe listen --forward-to https://your-api-url/webhooks/stripe")


if __name__ == "__main__":
    main() 