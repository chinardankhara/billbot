#!/usr/bin/env python3
"""
Comprehensive payment test suite for different payment methods and scenarios
"""

import boto3
from datetime import datetime
from src.payment_scheduler.stripe_client import StripePaymentClient

# Test scenarios to demonstrate
TEST_SCENARIOS = [
    {
        'name': 'Credit Card (Visa) - Success',
        'payment_type': 'card',
        'description': 'Standard credit card payment',
        'expected': 'succeeded'
    },
    {
        'name': 'Credit Card (Amex) - Success', 
        'payment_type': 'card_amex',
        'description': 'American Express card payment',
        'expected': 'succeeded'
    },
    {
        'name': 'Credit Card - Declined',
        'payment_type': 'card_decline',
        'description': 'Card payment that gets declined',
        'expected': 'failed'
    },
    {
        'name': 'ACH Bank Transfer - Success',
        'payment_type': 'ach',
        'description': 'ACH bank account transfer (most common B2B)',
        'expected': 'succeeded'
    },
    {
        'name': 'ACH - Account Closed',
        'payment_type': 'ach_closed',
        'description': 'ACH payment to closed account',
        'expected': 'failed'
    },
    {
        'name': 'ACH - Insufficient Funds',
        'payment_type': 'ach_nsf',
        'description': 'ACH payment with insufficient funds',
        'expected': 'failed'
    },
    {
        'name': 'ACH - Not Authorized',
        'payment_type': 'ach_no_auth',
        'description': 'ACH payment without debit authorization',
        'expected': 'failed'
    },
    {
        'name': 'ACH - Processing (Pending)',
        'payment_type': 'ach_processing',
        'description': 'ACH payment that stays processing (real-world scenario)',
        'expected': 'processing'
    },
    {
        'name': 'ACH - Dispute Risk',
        'payment_type': 'ach_dispute',
        'description': 'ACH payment that triggers dispute',
        'expected': 'succeeded'  # Initially succeeds, then disputes later
    }
]

def run_payment_test_suite():
    """Run comprehensive payment tests across all scenarios"""
    
    print("🚀 Jetty Payment Test Suite")
    print("=" * 60)
    print("Testing various payment methods and failure scenarios")
    print("=" * 60)
    
    try:
        # Initialize Stripe client
        stripe_client = StripePaymentClient()
        print("✅ Stripe client initialized")
        
        results = []
        
        # Test each scenario
        for i, scenario in enumerate(TEST_SCENARIOS, 1):
            print(f"\n🧪 Test {i}/{len(TEST_SCENARIOS)}: {scenario['name']}")
            print("-" * 50)
            print(f"Type: {scenario['payment_type']}")
            print(f"Description: {scenario['description']}")
            print(f"Expected: {scenario['expected']}")
            
            # Sample invoice data for testing
            test_invoice = {
                'vendor_name': 'CPB SOFTWARE (GERMANY) GMBH',
                'invoice_id': f'TEST-{i:03d}',
                'total_amount': f"{453.53 + i}",  # Vary amounts slightly
                'currency': 'USD',  # ACH requires USD
                'processed_invoice_uuid': f'test-uuid-{i:03d}'
            }
            
            try:
                # Run the payment test
                result = stripe_client.create_test_payment_intent(
                    amount=test_invoice['total_amount'],
                    currency=test_invoice['currency'],
                    vendor_name=test_invoice['vendor_name'],
                    invoice_id=test_invoice['invoice_id'],
                    processed_invoice_uuid=test_invoice['processed_invoice_uuid'],
                    payment_method_type=scenario['payment_type']
                )
                
                if result.success:
                    print(f"✅ Payment created: {result.payment_intent_id}")
                    print(f"   Status: {result.status}")
                    print(f"   Dashboard: https://dashboard.stripe.com/test/payments/{result.payment_intent_id}")
                    
                    # Update DynamoDB for demo (optional)
                    update_test_invoice_status(
                        test_invoice['processed_invoice_uuid'],
                        'PAYMENT_SUCCEEDED' if result.status == 'succeeded' else 'PAYMENT_PROCESSING',
                        result.payment_intent_id
                    )
                    
                    results.append({
                        'test': scenario['name'],
                        'status': 'success',
                        'payment_id': result.payment_intent_id,
                        'stripe_status': result.status
                    })
                    
                else:
                    print(f"❌ Payment failed: {result.error_message}")
                    results.append({
                        'test': scenario['name'],
                        'status': 'failed',
                        'error': result.error_message
                    })
                    
            except Exception as e:
                print(f"❌ Test error: {e}")
                results.append({
                    'test': scenario['name'],
                    'status': 'error',
                    'error': str(e)
                })
        
        # Print summary
        print("\n" + "=" * 60)
        print("🎯 TEST SUITE SUMMARY")
        print("=" * 60)
        
        successful = len([r for r in results if r['status'] == 'success'])
        failed = len([r for r in results if r['status'] in ['failed', 'error']])
        
        print(f"Total Tests: {len(results)}")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        print(f"Success Rate: {(successful/len(results)*100):.1f}%")
        
        print("\n📊 Detailed Results:")
        for result in results:
            status_emoji = "✅" if result['status'] == 'success' else "❌"
            print(f"  {status_emoji} {result['test']}")
            if 'payment_id' in result:
                print(f"     Payment ID: {result['payment_id']}")
                print(f"     Stripe Status: {result['stripe_status']}")
            elif 'error' in result:
                print(f"     Error: {result['error']}")
        
        print("\n🔗 View all payments in Stripe Dashboard:")
        print("   https://dashboard.stripe.com/test/payments")
        print("   Filter by metadata: jetty_payment = test")
        
        return results
        
    except Exception as e:
        print(f"❌ Test suite error: {e}")
        return []

def update_test_invoice_status(invoice_uuid: str, status: str, payment_intent_id: str):
    """Update test invoice status in DynamoDB (optional for demo)"""
    try:
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.Table('Invoices')
        
        table.put_item(Item={
            'processed_invoice_uuid': invoice_uuid,
            'processing_status': status,
            'payment_intent_id': payment_intent_id,
            'vendor_name': 'CPB SOFTWARE (GERMANY) GMBH',
            'invoice_id': invoice_uuid.replace('test-uuid-', 'TEST-'),
            'total_amount': '453.53',
            'currency': 'USD',
            'due_date': datetime.now().strftime('%Y-%m-%d'),
            'received_timestamp': datetime.utcnow().isoformat() + 'Z',
            'last_updated': datetime.utcnow().isoformat() + 'Z',
            'extraction_successful': True,
            's3_bucket': 'test-bucket',
            's3_original_key': 'test-email.txt',
            'classification_request_id': 'test-classification-123'
        })
        
        print(f"   ✅ Updated DynamoDB record")
        
    except Exception as e:
        print(f"   ⚠️ Could not update DynamoDB: {e}")

def main():
    print("This test suite will:")
    print("1. Test 9 different payment scenarios")
    print("2. Show various credit card and ACH outcomes")
    print("3. Demonstrate B2B payment failure modes")
    print("4. Create test records in Stripe Dashboard")
    print("5. Update DynamoDB with test data")
    
    choice = input("\nPress Enter to continue, or 'q' to quit: ")
    if choice.lower() == 'q':
        return
    
    results = run_payment_test_suite()
    
    if results:
        print("\n🎉 Test suite completed!")
        print("Check your Stripe Dashboard to see all the test payments.")

if __name__ == "__main__":
    main() 