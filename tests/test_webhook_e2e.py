#!/usr/bin/env python3
"""
End-to-end webhook test: Trigger Stripe webhook → Create matching invoice → Verify update
"""

import boto3
import subprocess
import json
import time
import re
from datetime import datetime

def trigger_stripe_webhook():
    """Trigger a Stripe webhook and capture the generated payment intent ID"""
    
    print("🎯 Triggering Stripe webhook...")
    
    try:
        # Trigger webhook (Stripe CLI generates random payment intent ID)
        result = subprocess.run([
            'stripe', 'trigger', 'payment_intent.succeeded'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Webhook triggered successfully")
            
            # Extract payment intent ID from Stripe CLI output
            # Look for patterns like "pi_..." in the output
            output = result.stdout + result.stderr
            pi_match = re.search(r'pi_[a-zA-Z0-9_]+', output)
            
            if pi_match:
                payment_intent_id = pi_match.group(0)
                print(f"   Generated Payment Intent: {payment_intent_id}")
                return payment_intent_id
            else:
                print("⚠️  Could not extract payment intent ID from output:")
                print(f"   Output: {output}")
                # Fallback: use a test ID and send webhook manually
                return "pi_test_fallback_" + str(int(time.time()))
        else:
            print(f"❌ Error triggering webhook:")
            print(f"   stderr: {result.stderr}")
            print(f"   stdout: {result.stdout}")
            return None
            
    except FileNotFoundError:
        print("❌ Stripe CLI not found. Install with: brew install stripe/stripe-cli/stripe")
        return None
    except Exception as e:
        print(f"❌ Error running stripe CLI: {e}")
        return None

def create_test_invoice_with_payment_intent(payment_intent_id):
    """Create a test invoice with the given payment intent ID"""
    
    print(f"\n📄 Creating test invoice for payment intent: {payment_intent_id}")
    
    # Initialize DynamoDB
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    table = dynamodb.Table('Invoices')
    
    test_uuid = f"test-webhook-{int(time.time())}"
    
    test_invoice = {
        'processed_invoice_uuid': test_uuid,
        'processing_status': 'PAYMENT_INITIATED',
        'payment_intent_id': payment_intent_id,
        'vendor_name': 'E2E Test Vendor',
        'invoice_id': 'E2E-TEST-001',
        'total_amount': '20.00',
        'currency': 'USD',
        'due_date': datetime.now().strftime('%Y-%m-%d'),
        'received_timestamp': datetime.utcnow().isoformat() + 'Z',
        'last_updated': datetime.utcnow().isoformat() + 'Z',
        'extraction_successful': True,
        's3_bucket': 'test-bucket',
        's3_original_key': 'test-e2e-email.txt',
        'classification_request_id': 'test-e2e-classification'
    }
    
    try:
        table.put_item(Item=test_invoice)
        print(f"✅ Created test invoice:")
        print(f"   UUID: {test_uuid}")
        print(f"   Payment Intent: {payment_intent_id}")
        print(f"   Status: PAYMENT_INITIATED")
        
        return test_uuid
        
    except Exception as e:
        print(f"❌ Error creating test invoice: {e}")
        return None

def send_webhook_manually(payment_intent_id):
    """Send a webhook manually if Stripe CLI doesn't work"""
    
    print(f"\n🔧 Sending webhook manually for: {payment_intent_id}")
    
    webhook_payload = {
        "id": "evt_test_webhook",
        "object": "event",
        "api_version": "2020-08-27",
        "created": int(time.time()),
        "data": {
            "object": {
                "id": payment_intent_id,
                "object": "payment_intent",
                "amount": 2000,
                "currency": "usd",
                "status": "succeeded"
            }
        },
        "livemode": False,
        "pending_webhooks": 1,
        "request": {
            "id": "req_test",
            "idempotency_key": None
        },
        "type": "payment_intent.succeeded"
    }
    
    try:
        import requests
        
        # Your API Gateway webhook URL
        webhook_url = "https://qdot6d8anh.execute-api.us-east-1.amazonaws.com/webhooks/stripe"
        
        # Note: In real usage, you'd need proper Stripe signature
        # For testing, we'll assume signature verification can be disabled
        response = requests.post(
            webhook_url,
            json=webhook_payload,
            headers={
                'Content-Type': 'application/json',
                'Stripe-Signature': 'test_signature'  # This will fail signature verification
            }
        )
        
        print(f"   Response: {response.status_code}")
        if response.status_code == 200:
            print("✅ Webhook sent successfully")
            return True
        else:
            print(f"❌ Webhook failed: {response.text}")
            return False
            
    except ImportError:
        print("❌ requests library not available. Install with: pip install requests")
        return False
    except Exception as e:
        print(f"❌ Error sending webhook: {e}")
        return False

def check_invoice_update(uuid, max_attempts=6):
    """Check if the invoice status was updated to PAID (with retries)"""
    
    print(f"\n🔍 Checking invoice update (up to {max_attempts} attempts)...")
    
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    table = dynamodb.Table('Invoices')
    
    for attempt in range(max_attempts):
        try:
            response = table.get_item(Key={'processed_invoice_uuid': uuid})
            
            if 'Item' in response:
                invoice = response['Item']
                status = invoice.get('processing_status', 'Unknown')
                
                print(f"📄 Invoice: {uuid} (attempt {attempt + 1})")
                print(f"   Status: {status}")
                print(f"   Last Updated: {invoice.get('last_updated', 'Unknown')}")
                
                if status == 'PAID':
                    print(f"🎉 SUCCESS! Invoice status updated to PAID")
                    return True
                else:
                    print(f"⚠️  Status is still: {status}")
                    if attempt < max_attempts - 1:
                        print(f"   Waiting 3 seconds before retry...")
                        time.sleep(3)
            else:
                print(f"❌ Invoice not found: {uuid}")
                return False
                
        except Exception as e:
            print(f"❌ Error checking invoice: {e}")
            return False
    
    print(f"❌ Invoice status did not update to PAID after {max_attempts} attempts")
    return False

def main():
    """Run complete end-to-end webhook test"""
    
    print("🚀 End-to-End Webhook Test")
    print("=" * 50)
    
    # Step 1: Trigger webhook and get payment intent ID
    payment_intent_id = trigger_stripe_webhook()
    if not payment_intent_id:
        print("❌ Could not trigger webhook or get payment intent ID")
        return False
    
    # Step 2: Create test invoice with the payment intent ID
    uuid = create_test_invoice_with_payment_intent(payment_intent_id)
    if not uuid:
        return False
    
    # Step 3: Wait for webhook processing
    print("\n⏳ Waiting 5 seconds for webhook to process...")
    time.sleep(5)
    
    # Step 4: Check results (with retries)
    success = check_invoice_update(uuid)
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 END-TO-END TEST PASSED!")
        print("   Webhook system is working correctly!")
    else:
        print("❌ END-TO-END TEST FAILED")
        print("   Possible issues:")
        print("   1. Webhook signature verification failed")
        print("   2. API Gateway not configured correctly") 
        print("   3. Lambda function error")
        print("   4. DynamoDB permissions issue")
        print("   Check CloudWatch logs for details")
    
    return success

if __name__ == "__main__":
    main() 