#!/usr/bin/env python3
"""
Test script to set an existing invoice's due_date to today for payment testing
"""

import boto3
from datetime import datetime

def update_invoice_due_date():
    """Update the existing invoice to have due_date = today for testing"""
    
    # Initialize DynamoDB
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    table = dynamodb.Table('Invoices')
    
    # The existing invoice UUID from your screenshot
    existing_uuid = "610ba35c-dc80-4b29-8481-e112a9c74bb7"
    
    # Set due_date to today
    today = datetime.now().strftime('%Y-%m-%d')
    
    try:
        # Update the invoice's due_date
        response = table.update_item(
            Key={'processed_invoice_uuid': existing_uuid},
            UpdateExpression='SET due_date = :due_date',
            ExpressionAttributeValues={':due_date': today},
            ReturnValues='UPDATED_NEW'
        )
        
        print(f"✅ Updated invoice {existing_uuid}")
        print(f"   New due_date: {today}")
        print(f"   Updated attributes: {response.get('Attributes', {})}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating invoice: {e}")
        return False

def main():
    print("🧪 Setting up test data for payment scheduler")
    print("=" * 50)
    
    if update_invoice_due_date():
        print("\n🎯 Now run the payment scheduler again:")
        print("python example_payment_scheduler.py")
        print("\nThis should find 1 urgent payment due today!")
    else:
        print("\n❌ Failed to update test data")

if __name__ == "__main__":
    main() 