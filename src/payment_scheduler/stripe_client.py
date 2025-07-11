"""
Stripe payment client for processing invoice payments
"""

import stripe
import os
from typing import Dict, Any, Optional
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class PaymentResult:
    """Result of a payment attempt"""
    success: bool
    payment_intent_id: Optional[str]
    status: Optional[str]
    error_message: Optional[str]
    stripe_response: Optional[Dict[str, Any]]


class StripePaymentClient:
    """Handles Stripe payment processing for invoices"""
    
    def __init__(self, api_key: str = None):
        """
        Initialize the Stripe client.
        
        Args:
            api_key: Stripe secret key. If None, will try to get from STRIPE_SECRET_KEY env var
        """
        self.api_key = api_key or os.getenv('STRIPE_SECRET_KEY')
        if not self.api_key:
            raise ValueError("STRIPE_SECRET_KEY not found. Please set the environment variable or pass api_key parameter.")
        
        stripe.api_key = self.api_key
    
    def create_payment_intent(
        self,
        amount: str,
        currency: str,
        vendor_name: str,
        invoice_id: str,
        processed_invoice_uuid: str,
        description: str = None
    ) -> PaymentResult:
        """
        Create a Stripe Payment Intent for an invoice.
        
        Args:
            amount: Payment amount (e.g., "453.53")
            currency: Currency code (e.g., "EUR", "USD")
            vendor_name: Name of the vendor/payee
            invoice_id: Invoice ID from vendor
            processed_invoice_uuid: Our internal invoice UUID
            description: Optional payment description
            
        Returns:
            PaymentResult with payment details
        """
        try:
            # Convert amount to cents (Stripe expects integer cents)
            amount_cents = int(float(amount) * 100)
            
            # Create description if not provided
            if not description:
                description = f"Payment for invoice {invoice_id} from {vendor_name}"
            
            # Create the payment intent (without auto-confirm for now)
            payment_intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency=currency.lower(),
                description=description,
                metadata={
                    'vendor_name': vendor_name,
                    'invoice_id': invoice_id,
                    'processed_invoice_uuid': processed_invoice_uuid,
                    'billbot_payment': 'true'
                },
                # Don't auto-confirm - payment method needs to be added first
                # In production, you'd either:
                # 1. Store vendor payment methods and confirm with them
                # 2. Use ACH/bank transfers for B2B payments
                # 3. Create intents that require manual approval
                payment_method_types=['card', 'us_bank_account'],  # B2B payment methods
                automatic_payment_methods={'enabled': True}
            )
            
            return PaymentResult(
                success=True,
                payment_intent_id=payment_intent.id,
                status=payment_intent.status,
                error_message=None,
                stripe_response=payment_intent
            )
            
        except stripe.error.StripeError as e:
            print(f"Stripe error creating payment intent: {e}")
            return PaymentResult(
                success=False,
                payment_intent_id=None,
                status=None,
                error_message=str(e),
                stripe_response=None
            )
        except Exception as e:
            print(f"Error creating payment intent: {e}")
            return PaymentResult(
                success=False,
                payment_intent_id=None,
                status=None,
                error_message=str(e),
                stripe_response=None
            )
    
    def get_payment_status(self, payment_intent_id: str) -> Dict[str, Any]:
        """
        Get the current status of a payment intent.
        
        Args:
            payment_intent_id: The Stripe Payment Intent ID
            
        Returns:
            Dict with payment status information
        """
        try:
            payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            return {
                'success': True,
                'status': payment_intent.status,
                'amount': payment_intent.amount,
                'currency': payment_intent.currency,
                'payment_intent': payment_intent
            }
        except stripe.error.StripeError as e:
            print(f"Stripe error retrieving payment: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def create_test_payment_intent(
        self,
        amount: str,
        currency: str,
        vendor_name: str,
        invoice_id: str,
        processed_invoice_uuid: str,
        description: str = None,
        payment_method_type: str = 'card'
    ) -> PaymentResult:
        """
        Create and confirm a test payment intent with various test payment methods.
        FOR TESTING ONLY - uses Stripe test payment method tokens.
        
        Args:
            amount: Payment amount (e.g., "453.53")
            currency: Currency code (e.g., "EUR", "USD")
            vendor_name: Name of the vendor/payee
            invoice_id: Invoice ID from vendor
            processed_invoice_uuid: Our internal invoice UUID
            description: Optional payment description
            payment_method_type: Type of test payment ('card', 'ach', 'ach_fail', etc.)
            
        Returns:
            PaymentResult with payment details
        """
        try:
            # Convert amount to cents (Stripe expects integer cents)
            amount_cents = int(float(amount) * 100)
            
            # Create description if not provided
            if not description:
                description = f"TEST-{payment_method_type.upper()} Payment for invoice {invoice_id} from {vendor_name}"
            
            # Use Stripe's pre-built test payment method tokens
            # This is safer than creating raw card data
            test_payment_methods = {
                'card': 'pm_card_visa',                          # Visa card (succeeds)
                'card_decline': 'pm_card_chargeDeclined',        # Always declines  
                'card_amex': 'pm_card_amex',                     # American Express
                'card_mastercard': 'pm_card_mastercard',         # Mastercard
                'ach': 'pm_usBankAccount_success',               # ACH bank account (succeeds)
                'ach_closed': 'pm_usBankAccount_accountClosed',  # Account closed
                'ach_nsf': 'pm_usBankAccount_insufficientFunds', # Insufficient funds
                'ach_no_auth': 'pm_usBankAccount_debitNotAuthorized', # Debits not authorized
                'ach_no_account': 'pm_usBankAccount_noAccount',  # No account found
                'ach_dispute': 'pm_usBankAccount_dispute',       # Triggers dispute
                'ach_processing': 'pm_usBankAccount_processing', # Stays processing indefinitely
            }
            
            test_payment_method_id = test_payment_methods.get(payment_method_type, 'pm_card_visa')
            
            # Determine payment method types based on test type
            if payment_method_type.startswith('ach'):
                payment_method_types = ['us_bank_account']
            else:
                payment_method_types = ['card']
            
            # Create and confirm the payment intent with test payment method
            payment_intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency=currency.lower(),
                description=description,
                metadata={
                    'vendor_name': vendor_name,
                    'invoice_id': invoice_id,
                    'processed_invoice_uuid': processed_invoice_uuid,
                    'billbot_payment': 'test',
                    'test_payment_type': payment_method_type
                },
                payment_method_types=payment_method_types,
                payment_method=test_payment_method_id,
                confirm=True,
                return_url='https://test-billbot.com/complete'
            )
            
            return PaymentResult(
                success=True,
                payment_intent_id=payment_intent.id,
                status=payment_intent.status,
                error_message=None,
                stripe_response=payment_intent
            )
            
        except stripe.error.StripeError as e:
            print(f"Stripe error creating test payment intent: {e}")
            return PaymentResult(
                success=False,
                payment_intent_id=None,
                status=None,
                error_message=str(e),
                stripe_response=None
            )
        except Exception as e:
            print(f"Error creating test payment intent: {e}")
            return PaymentResult(
                success=False,
                payment_intent_id=None,
                status=None,
                error_message=str(e),
                stripe_response=None
            )

    def cancel_payment(self, payment_intent_id: str) -> Dict[str, Any]:
        """
        Cancel a payment intent.
        
        Args:
            payment_intent_id: The Stripe Payment Intent ID
            
        Returns:
            Dict with cancellation result
        """
        try:
            payment_intent = stripe.PaymentIntent.cancel(payment_intent_id)
            return {
                'success': True,
                'status': payment_intent.status,
                'payment_intent': payment_intent
            }
        except stripe.error.StripeError as e:
            print(f"Stripe error cancelling payment: {e}")
            return {
                'success': False,
                'error': str(e)
            } 