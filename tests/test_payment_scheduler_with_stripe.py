#!/usr/bin/env python3
"""
Test payment scheduler with actual Stripe payments using test cards
"""

import boto3
from datetime import datetime
from src.payment_scheduler.stripe_client import StripePaymentClient

def test_single_payment():
    """Test a single payment with the test Stripe card"""
    
    print("🧪 Testing single payment with Stripe test card")
    print("=" * 50)
    
    try:
        # Initialize Stripe client
        stripe_client = StripePaymentClient()
        print("✅ Stripe client initialized")
        
        # Sample invoice data (like from your DynamoDB)
        test_invoice = {
            'vendor_name': 'CPB SOFTWARE (GERMANY) GMBH',
            'invoice_id': '123100401',
            'total_amount': '453.53',
            'currency': 'EUR',
            'processed_invoice_uuid': '610ba35c-dc80-4b29-8481-e112a9c74bb7'
        }
        
        print(f"\n💳 Processing test payment:")
        print(f"   Vendor: {test_invoice['vendor_name']}")
        print(f"   Invoice: {test_invoice['invoice_id']}")
        print(f"   Amount: {test_invoice['total_amount']} {test_invoice['currency']}")
        
        # Create test payment intent with ACH (more realistic for B2B)
        result = stripe_client.create_test_payment_intent(
            amount=test_invoice['total_amount'],
            currency=test_invoice['currency'],
            vendor_name=test_invoice['vendor_name'],
            invoice_id=test_invoice['invoice_id'],
            processed_invoice_uuid=test_invoice['processed_invoice_uuid'],
            payment_method_type='ach'  # Use ACH for B2B demo
        )
        
        if result.success:
            print(f"\n✅ Payment successful!")
            print(f"   Payment Intent ID: {result.payment_intent_id}")
            print(f"   Status: {result.status}")
            print(f"\n🔗 Check in Stripe Dashboard:")
            print(f"   https://dashboard.stripe.com/test/payments/{result.payment_intent_id}")
            
            # Update DynamoDB status to show payment was processed
            update_invoice_status(
                test_invoice['processed_invoice_uuid'],
                'PAYMENT_SUCCEEDED',
                result.payment_intent_id
            )
            
        else:
            print(f"\n❌ Payment failed!")
            print(f"   Error: {result.error_message}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

def update_invoice_status(invoice_uuid: str, status: str, payment_intent_id: str):
    """Update invoice status in DynamoDB"""
    try:
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.Table('Invoices')
        
        table.update_item(
            Key={'processed_invoice_uuid': invoice_uuid},
            UpdateExpression='SET processing_status = :status, payment_intent_id = :payment_id, last_updated = :timestamp',
            ExpressionAttributeValues={
                ':status': status,
                ':payment_id': payment_intent_id,
                ':timestamp': datetime.utcnow().isoformat() + 'Z'
            }
        )
        print(f"✅ Updated DynamoDB status to {status}")
        
    except Exception as e:
        print(f"⚠️ Could not update DynamoDB: {e}")

def main():
    print("🚀 BillBot Payment Test with Real Stripe Integration")
    print("=" * 60)
    
    print("\nThis test will:")
    print("1. Create a Stripe Payment Intent")
    print("2. Use a test credit card (4242424242424242)")
    print("3. Actually charge the test card")
    print("4. Update the invoice status in DynamoDB")
    print("5. Show you the result in Stripe Dashboard")
    
    input("\nPress Enter to continue...")
    
    test_single_payment()

if __name__ == "__main__":
    main() 