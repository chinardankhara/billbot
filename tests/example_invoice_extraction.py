#!/usr/bin/env python3
"""
Example usage of the BillBot Invoice Extractor
"""

from src.invoice_extractor.extractor import InvoiceExtractor

def main():
    print("🚀 BillBot Invoice Extractor Demo")
    print("=" * 50)
    
    # Initialize the extractor
    try:
        extractor = InvoiceExtractor()
    except ValueError as e:
        print(f"❌ Error initializing extractor: {e}")
        print("\nMake sure you have:")
        print("1. Set the GEMINI_API_KEY environment variable")
        print("2. Installed all required dependencies: pip install -r requirements.txt")
        return
    
    # Email file to extract data from
    email_file = "sample_emails/testemail.txt"
    
    print(f"\n📧 Processing email from: {email_file}")
    
    try:
        # Extract invoice data
        result = extractor.extract_from_email_file(email_file)
        
        # Display results
        print("\n📊 Invoice Extraction Results:")
        print("=" * 50)
        
        if result.extraction_successful:
            print("✅ Extraction Successful!")
            print(f"📝 Vendor Name: {result.vendor_name or 'Not found'}")
            print(f"🔢 Invoice ID: {result.invoice_id or 'Not found'}")
            print(f"📅 Due Date: {result.due_date or 'Not found'}")
            print(f"💰 Total Amount: {result.total_amount or 'Not found'}")
            print(f"💱 Currency: {result.currency or 'Not found'}")
        else:
            print("❌ Extraction Failed!")
            print(f"Error: {result.raw_response}")
        
        print("=" * 50)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nMake sure you have:")
        print("1. Set the GEMINI_API_KEY environment variable")
        print("2. Installed all required dependencies: pip install -r requirements.txt")
        print("3. Have internet connectivity")
        print(f"4. The sample email file exists at: {email_file}")

if __name__ == "__main__":
    main() 