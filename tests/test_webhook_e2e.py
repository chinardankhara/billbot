#!/usr/bin/env python3
"""
End-to-end webhook test: Create invoice → Trigger Stripe webhook → Verify update
"""

import boto3
import subprocess
import json
import time
from datetime import datetime

def create_test_invoice_for_webhook():
    """Create a test invoice that we can use for webhook testing"""
    
    # Initialize DynamoDB
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    table = dynamodb.Table('Invoices')
    
    # Create a test payment intent ID that matches what Stripe might generate
    test_payment_intent_id = "pi_test_e2e_" + str(int(time.time()))
    test_uuid = f"test-webhook-{int(time.time())}"
    
    test_invoice = {
        'processed_invoice_uuid': test_uuid,
        'processing_status': 'PAYMENT_INITIATED',
        'payment_intent_id': test_payment_intent_id,
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
        print(f"   Payment Intent: {test_payment_intent_id}")
        print(f"   Status: PAYMENT_INITIATED")
        
        return test_payment_intent_id, test_uuid
        
    except Exception as e:
        print(f"❌ Error creating test invoice: {e}")
        return None, None

def trigger_stripe_webhook_for_payment(payment_intent_id):
    """Trigger a Stripe webhook for a specific payment intent"""
    
    print(f"\n🎯 Triggering Stripe webhook for: {payment_intent_id}")
    
    try:
        # Trigger webhook with specific payment intent ID
        result = subprocess.run([
            'stripe', 'trigger', 'payment_intent.succeeded',
            '--add', f'payment_intent:id={payment_intent_id}'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ Webhook triggered successfully")
            print(f"   Output: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ Error triggering webhook: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error running stripe CLI: {e}")
        print("   Make sure you have Stripe CLI installed and configured")
        return False

def check_invoice_update(uuid):
    """Check if the invoice status was updated to PAID"""
    
    print(f"\n🔍 Checking invoice update...")
    
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    table = dynamodb.Table('Invoices')
    
    try:
        response = table.get_item(Key={'processed_invoice_uuid': uuid})
        
        if 'Item' in response:
            invoice = response['Item']
            status = invoice.get('processing_status', 'Unknown')
            
            print(f"📄 Invoice: {uuid}")
            print(f"   Status: {status}")
            print(f"   Last Updated: {invoice.get('last_updated', 'Unknown')}")
            
            if status == 'PAID':
                print(f"🎉 SUCCESS! Invoice status updated to PAID")
                return True
            else:
                print(f"⚠️  Status is still: {status}")
                return False
        else:
            print(f"❌ Invoice not found: {uuid}")
            return False
            
    except Exception as e:
        print(f"❌ Error checking invoice: {e}")
        return False

def main():
    """Run complete end-to-end webhook test"""
    
    print("🚀 End-to-End Webhook Test")
    print("=" * 50)
    
    # Step 1: Create test invoice
    payment_intent_id, uuid = create_test_invoice_for_webhook()
    if not payment_intent_id:
        return False
    
    # Step 2: Wait a moment for consistency
    print("\n⏳ Waiting 2 seconds for DynamoDB consistency...")
    time.sleep(2)
    
    # Step 3: Trigger webhook
    if not trigger_stripe_webhook_for_payment(payment_intent_id):
        return False
    
    # Step 4: Wait for webhook processing
    print("\n⏳ Waiting 5 seconds for webhook processing...")
    time.sleep(5)
    
    # Step 5: Check results
    success = check_invoice_update(uuid)
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 END-TO-END TEST PASSED!")
        print("   Webhook system is working correctly!")
    else:
        print("❌ END-TO-END TEST FAILED")
        print("   Check CloudWatch logs for details")
    
    return success

if __name__ == "__main__":
    main() 