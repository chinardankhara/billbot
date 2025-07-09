"""
Payment scheduler with urgent and batch processing
"""

import boto3
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from botocore.exceptions import ClientError

try:
    # Lambda environment - direct imports
    from stripe_client import StripePaymentClient, PaymentResult
except ImportError:
    # Development environment - relative imports
    from .stripe_client import StripePaymentClient, PaymentResult


class PaymentScheduler:
    """
    Payment scheduler that processes invoices in two steps:
    Step A: Urgent scan (due today)
    Step B: Batch scan (due within payment window)
    """
    
    def __init__(
        self,
        table_name: str,
        stripe_client: StripePaymentClient,
        region_name: str = 'us-east-1',
        payment_window_days: int = 7,
        is_production: bool = False
    ):
        """
        Initialize the payment scheduler.
        
        Args:
            table_name: DynamoDB table name
            stripe_client: Configured Stripe client
            region_name: AWS region
            payment_window_days: How many days ahead to process payments
        """
        self.table_name = table_name
        self.stripe_client = stripe_client
        self.payment_window_days = payment_window_days
        self.is_production = is_production
        
        # Initialize DynamoDB
        self.dynamodb = boto3.resource('dynamodb', region_name=region_name)
        self.table = self.dynamodb.Table(table_name)
    
    def run_payment_cycle(self) -> Dict[str, Any]:
        """
        Run the complete payment cycle (urgent + batch processing).
        
        Returns:
            Dict with summary of processing results
        """
        print("🚀 Starting payment cycle...")
        
        results = {
            'urgent_payments': {
                'processed': 0,
                'successful': 0,
                'failed': 0,
                'errors': []
            },
            'batch_payments': {
                'processed': 0,
                'successful': 0,
                'failed': 0,
                'errors': []
            }
        }
        
        # Step A: Handle urgent payments (due today)
        print("⚡ Step A: Processing urgent payments (due today)...")
        urgent_results = self._process_urgent_payments()
        results['urgent_payments'] = urgent_results
        
        # Step B: Handle batch payments (due within window)
        print("📦 Step B: Processing batch payments (due within window)...")
        batch_results = self._process_batch_payments()
        results['batch_payments'] = batch_results
        
        # Summary
        total_processed = urgent_results['processed'] + batch_results['processed']
        total_successful = urgent_results['successful'] + batch_results['successful']
        total_failed = urgent_results['failed'] + batch_results['failed']
        
        print(f"✅ Payment cycle complete!")
        print(f"   Total processed: {total_processed}")
        print(f"   Successful: {total_successful}")
        print(f"   Failed: {total_failed}")
        
        results['summary'] = {
            'total_processed': total_processed,
            'total_successful': total_successful,
            'total_failed': total_failed
        }
        
        return results
    
    def _process_urgent_payments(self) -> Dict[str, Any]:
        """
        Step A: Process payments due today (urgent).
        
        Returns:
            Dict with processing results
        """
        today = datetime.now().strftime('%Y-%m-%d')
        
        try:
            # Query GSI for urgent payments
            urgent_invoices = self._query_invoices_by_status_and_due_date(
                status='RECEIVED',
                due_date=today
            )
            
            print(f"Found {len(urgent_invoices)} urgent payment(s) due today")
            
            results = {
                'processed': 0,
                'successful': 0,
                'failed': 0,
                'errors': []
            }
            
            for invoice in urgent_invoices:
                result = self._process_single_payment(invoice, urgent=True)
                results['processed'] += 1
                
                if result['success']:
                    results['successful'] += 1
                else:
                    results['failed'] += 1
                    results['errors'].append(result['error'])
            
            return results
            
        except Exception as e:
            print(f"Error in urgent payment processing: {e}")
            return {
                'processed': 0,
                'successful': 0,
                'failed': 0,
                'errors': [str(e)]
            }
    
    def _process_batch_payments(self) -> Dict[str, Any]:
        """
        Step B: Process payments due within the payment window.
        
        Returns:
            Dict with processing results
        """
        # Calculate date range for batch processing
        today = datetime.now()
        end_date = (today + timedelta(days=self.payment_window_days)).strftime('%Y-%m-%d')
        
        try:
            # Query GSI for batch payments
            batch_invoices = self._query_invoices_by_status_and_due_date_range(
                status='RECEIVED',
                start_date=today.strftime('%Y-%m-%d'),
                end_date=end_date
            )
            
            print(f"Found {len(batch_invoices)} invoice(s) due within {self.payment_window_days} days")
            
            results = {
                'processed': 0,
                'successful': 0,
                'failed': 0,
                'errors': []
            }
            
            for invoice in batch_invoices:
                # Skip if this was already processed in urgent scan
                if invoice.get('due_date') == today.strftime('%Y-%m-%d'):
                    continue
                    
                result = self._process_single_payment(invoice, urgent=False)
                results['processed'] += 1
                
                if result['success']:
                    results['successful'] += 1
                else:
                    results['failed'] += 1
                    results['errors'].append(result['error'])
            
            return results
            
        except Exception as e:
            print(f"Error in batch payment processing: {e}")
            return {
                'processed': 0,
                'successful': 0,
                'failed': 0,
                'errors': [str(e)]
            }
    
    def _process_single_payment(self, invoice: Dict[str, Any], urgent: bool = False) -> Dict[str, Any]:
        """
        Process a single invoice payment.
        
        Args:
            invoice: Invoice data from DynamoDB
            urgent: Whether this is an urgent payment
            
        Returns:
            Dict with processing result
        """
        try:
            processed_invoice_uuid = invoice['processed_invoice_uuid']
            vendor_name = invoice.get('vendor_name', 'Unknown Vendor')
            invoice_id = invoice.get('invoice_id', 'Unknown Invoice')
            total_amount = invoice.get('total_amount')
            currency = invoice.get('currency', 'USD')
            due_date = invoice.get('due_date', 'Unknown')
            
            print(f"{'🔥 URGENT' if urgent else '📅 BATCH'} Processing payment: {vendor_name} - {invoice_id} - {total_amount} {currency}")
            
            # Validate required fields
            if not total_amount:
                error_msg = f"Missing total_amount for invoice {processed_invoice_uuid}"
                print(f"❌ {error_msg}")
                return {'success': False, 'error': error_msg}
            
            # Choose payment method based on environment
            if self.is_production:
                # Production: Use real payment intents (requires stored payment methods)
                payment_result = self.stripe_client.create_payment_intent(
                    amount=total_amount,
                    currency=currency,
                    vendor_name=vendor_name,
                    invoice_id=invoice_id,
                    processed_invoice_uuid=processed_invoice_uuid,
                    description=f"{'URGENT ' if urgent else ''}Payment for invoice {invoice_id} (due {due_date})"
                )
            else:
                # Demo/Test: Use test payment methods for MVP demonstration
                payment_result = self.stripe_client.create_test_payment_intent(
                    amount=total_amount,
                    currency=currency,
                    vendor_name=vendor_name,
                    invoice_id=invoice_id,
                    processed_invoice_uuid=processed_invoice_uuid,
                    description=f"{'URGENT ' if urgent else ''}Payment for invoice {invoice_id} (due {due_date})",
                    payment_method_type='ach'  # Use ACH for B2B demo
                )
            
            if payment_result.success:
                # Update invoice status in DynamoDB
                self._update_invoice_status(
                    processed_invoice_uuid,
                    'PAYMENT_INITIATED',
                    payment_intent_id=payment_result.payment_intent_id
                )
                
                print(f"✅ Payment initiated: {payment_result.payment_intent_id}")
                return {
                    'success': True,
                    'payment_intent_id': payment_result.payment_intent_id,
                    'invoice_uuid': processed_invoice_uuid
                }
            else:
                error_msg = f"Stripe payment failed for {processed_invoice_uuid}: {payment_result.error_message}"
                print(f"❌ {error_msg}")
                
                # Update invoice status to indicate payment failure
                self._update_invoice_status(
                    processed_invoice_uuid,
                    'PAYMENT_FAILED',
                    error_message=payment_result.error_message
                )
                
                return {'success': False, 'error': error_msg}
                
        except Exception as e:
            error_msg = f"Error processing payment for {invoice.get('processed_invoice_uuid', 'unknown')}: {str(e)}"
            print(f"❌ {error_msg}")
            return {'success': False, 'error': error_msg}
    
    def _query_invoices_by_status_and_due_date(
        self,
        status: str,
        due_date: str
    ) -> List[Dict[str, Any]]:
        """
        Query invoices by status and specific due date using GSI.
        
        Args:
            status: Processing status (e.g., 'RECEIVED')
            due_date: Due date in YYYY-MM-DD format
            
        Returns:
            List of invoice items
        """
        try:
            response = self.table.query(
                IndexName='StatusAndDueDateIndex',
                KeyConditionExpression=boto3.dynamodb.conditions.Key('processing_status').eq(status) & 
                                     boto3.dynamodb.conditions.Key('due_date').eq(due_date)
            )
            return response.get('Items', [])
            
        except ClientError as e:
            print(f"Error querying invoices: {e}")
            return []
    
    def _query_invoices_by_status_and_due_date_range(
        self,
        status: str,
        start_date: str,
        end_date: str
    ) -> List[Dict[str, Any]]:
        """
        Query invoices by status and due date range using GSI.
        
        Args:
            status: Processing status (e.g., 'RECEIVED')
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            List of invoice items
        """
        try:
            response = self.table.query(
                IndexName='StatusAndDueDateIndex',
                KeyConditionExpression=boto3.dynamodb.conditions.Key('processing_status').eq(status) & 
                                     boto3.dynamodb.conditions.Key('due_date').between(start_date, end_date)
            )
            return response.get('Items', [])
            
        except ClientError as e:
            print(f"Error querying invoices: {e}")
            return []
    
    def _update_invoice_status(
        self,
        processed_invoice_uuid: str,
        new_status: str,
        payment_intent_id: str = None,
        error_message: str = None
    ) -> bool:
        """
        Update invoice processing status in DynamoDB.
        
        Args:
            processed_invoice_uuid: Invoice UUID
            new_status: New processing status
            payment_intent_id: Stripe payment intent ID (optional)
            error_message: Error message (optional)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            update_expression = 'SET processing_status = :status, last_updated = :timestamp'
            expression_values = {
                ':status': new_status,
                ':timestamp': datetime.utcnow().isoformat() + 'Z'
            }
            
            if payment_intent_id:
                update_expression += ', payment_intent_id = :payment_id'
                expression_values[':payment_id'] = payment_intent_id
            
            if error_message:
                update_expression += ', error_message = :error'
                expression_values[':error'] = error_message
            
            self.table.update_item(
                Key={'processed_invoice_uuid': processed_invoice_uuid},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values
            )
            
            return True
            
        except ClientError as e:
            print(f"Error updating invoice status: {e}")
            return False 