"""
AWS Lambda handler for payment scheduling
Processes invoices for payment via Stripe
"""

import json
import os
from typing import Dict, Any

# Import our core business logic
# Files are copied to Lambda root, so we import directly by filename
from scheduler import PaymentScheduler
from stripe_client import StripePaymentClient


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler function for payment scheduling
    
    Can be triggered by:
    1. CloudWatch Events (scheduled)
    2. Manual invocation
    3. SQS messages (future enhancement)
    """
    
    # Get required environment variables
    table_name = os.getenv('DYNAMODB_TABLE_NAME')
    stripe_secret_key = os.getenv('STRIPE_SECRET_KEY')
    payment_window_days = int(os.getenv('PAYMENT_WINDOW_DAYS', '7'))
    
    # Check if we're in production or demo mode
    is_production = os.getenv('JETTY_ENV', 'demo').lower() == 'production'
    
    print(f"🌍 Environment: {'PRODUCTION' if is_production else 'DEMO/TEST'}")
    
    if not table_name:
        raise ValueError("DYNAMODB_TABLE_NAME environment variable is required")
    if not stripe_secret_key:
        raise ValueError("STRIPE_SECRET_KEY environment variable is required")
    
    region = os.getenv('AWS_REGION', 'us-east-1')
    
    try:
        print(f"🚀 Payment scheduler starting...")
        print(f"   Table: {table_name}")
        print(f"   Region: {region}")
        print(f"   Payment Window: {payment_window_days} days")
        
        # Initialize Stripe client
        stripe_client = StripePaymentClient(api_key=stripe_secret_key)
        
        # Initialize payment scheduler
        scheduler = PaymentScheduler(
            table_name=table_name,
            stripe_client=stripe_client,
            region_name=region,
            payment_window_days=payment_window_days,
            is_production=is_production
        )
        
        # Run the payment cycle
        results = scheduler.run_payment_cycle()
        
        # Return success response
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Payment cycle completed successfully',
                'results': results
            })
        }
        
    except Exception as e:
        error_msg = f"Error in payment scheduler: {str(e)}"
        print(error_msg)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': error_msg})
        }


def handle_test_invocation(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle test invocation for local testing
    
    Expected event format:
    {
        "test_mode": true,
        "payment_window_days": 7
    }
    """
    print("🧪 Test mode invocation")
    
    # Override environment variables for testing
    if event.get('test_mode'):
        os.environ['PAYMENT_WINDOW_DAYS'] = str(event.get('payment_window_days', 7))
    
    return lambda_handler(event, None) 