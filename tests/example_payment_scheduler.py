#!/usr/bin/env python3
"""
Example usage of the BillBot Payment Scheduler
"""

from src.payment_scheduler.scheduler import PaymentScheduler
from src.payment_scheduler.stripe_client import StripePaymentClient

def main():
    print("🚀 BillBot Payment Scheduler Demo")
    print("=" * 50)
    
    # Initialize the Stripe client
    try:
        stripe_client = StripePaymentClient()
        print("✅ Stripe client initialized")
    except ValueError as e:
        print(f"❌ Error initializing Stripe client: {e}")
        print("\nMake sure you have:")
        print("1. Set the STRIPE_SECRET_KEY environment variable")
        print("2. Installed Stripe: pip install stripe")
        return
    
    # Initialize the payment scheduler
    try:
        scheduler = PaymentScheduler(
            table_name='Invoices',  # Your DynamoDB table name
            stripe_client=stripe_client,
            payment_window_days=7  # Process payments due within 7 days
        )
        print("✅ Payment scheduler initialized")
    except Exception as e:
        print(f"❌ Error initializing payment scheduler: {e}")
        print("\nMake sure you have:")
        print("1. AWS credentials configured")
        print("2. DynamoDB table 'Invoices' exists")
        print("3. GSI 'StatusAndDueDateIndex' configured")
        return
    
    print(f"\n🔄 Running payment cycle...")
    print("-" * 50)
    
    try:
        # Run the complete payment cycle
        results = scheduler.run_payment_cycle()
        
        print("\n📊 Payment Cycle Results:")
        print("=" * 50)
        
        # Display urgent payments results
        urgent = results['urgent_payments']
        print(f"⚡ URGENT PAYMENTS (due today):")
        print(f"   Processed: {urgent['processed']}")
        print(f"   Successful: {urgent['successful']}")
        print(f"   Failed: {urgent['failed']}")
        if urgent['errors']:
            print(f"   Errors: {len(urgent['errors'])}")
            for error in urgent['errors'][:3]:  # Show first 3 errors
                print(f"     - {error}")
        
        print()
        
        # Display batch payments results
        batch = results['batch_payments']
        print(f"📦 BATCH PAYMENTS (due within 7 days):")
        print(f"   Processed: {batch['processed']}")
        print(f"   Successful: {batch['successful']}")
        print(f"   Failed: {batch['failed']}")
        if batch['errors']:
            print(f"   Errors: {len(batch['errors'])}")
            for error in batch['errors'][:3]:  # Show first 3 errors
                print(f"     - {error}")
        
        print()
        
        # Display summary
        summary = results['summary']
        print(f"📈 TOTAL SUMMARY:")
        print(f"   Total Processed: {summary['total_processed']}")
        print(f"   Total Successful: {summary['total_successful']}")
        print(f"   Total Failed: {summary['total_failed']}")
        
        success_rate = 0
        if summary['total_processed'] > 0:
            success_rate = (summary['total_successful'] / summary['total_processed']) * 100
        
        print(f"   Success Rate: {success_rate:.1f}%")
        
        print("=" * 50)
        
    except Exception as e:
        print(f"❌ Error running payment cycle: {e}")
        print("\nMake sure you have:")
        print("1. STRIPE_SECRET_KEY environment variable set")
        print("2. AWS credentials configured")
        print("3. DynamoDB table 'Invoices' exists with GSI 'StatusAndDueDateIndex'")
        print("4. Internet connectivity for Stripe API")

if __name__ == "__main__":
    main() 