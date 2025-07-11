#!/usr/bin/env python3
"""
Example usage of the BillBot Email Classifier
"""

from src.email_classifier.classifier import EmailClassifier

def main():
    print("🚀 BillBot Email Classifier Demo")
    print("=" * 50)
    
    # Initialize the classifier
    try:
        classifier = EmailClassifier()
    except ValueError as e:
        print(f"❌ Error initializing classifier: {e}")
        print("\nMake sure you have:")
        print("1. Set the GEMINI_API_KEY environment variable")
        print("2. Installed all required dependencies: pip install -r requirements.txt")
        return
    
    # Email file to classify
    email_file = "sample_emails/testemail.txt"
    
    print(f"\n📧 Processing email from: {email_file}")
    
    try:
        # Parse the email first to show information
        parsed_email = classifier.email_parser.parse_from_file(email_file)
        
        print("\n📋 Email Information:")
        print("-" * 50)
        print(f"   Subject: {parsed_email.subject}")
        print(f"   From: {parsed_email.sender}")
        print(f"   Attachments: {len(parsed_email.attachments)}")
        print(f"   PDF Attachments: {len(parsed_email.pdf_attachments)}")
        for pdf in parsed_email.pdf_attachments:
            print(f"     - {pdf.filename} ({len(pdf.content)} bytes)")
        
        print("\n🤖 Running AI Classification...")
        
        # Classify the email
        result = classifier.classify_email(parsed_email)
        
        # Display results
        print("✅ Classification Complete!")
        print("=" * 50)
        print(f"📊 RESULT: {result.classification}")
        print(f"💭 REASONING: {result.reasoning}")
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