#!/usr/bin/env python3
"""
Example usage script for the Jetty Email Classifier.
"""

import os
from src.utils.email_parser import EmailParser
from src.email_classifier.classifier import EmailClassifier


def main():
    """Demonstrate email classification capabilities."""
    print("🚀 Jetty Email Classifier Demo")
    print("=" * 50)
    
    # Path to sample email file
    sample_email_path = "sample_emails/testemail.txt"
    
    try:
        # Check if sample email file exists
        if not os.path.exists(sample_email_path):
            print(f"❌ Sample email file not found: {sample_email_path}")
            print("Please make sure the sample email file exists.")
            return
        
        # Initialize components
        parser = EmailParser()
        classifier = EmailClassifier()
        
        print(f"\n📧 Processing email from: {sample_email_path}")
        
        # Parse email from file
        parsed_email = parser.parse_from_file(sample_email_path)
        
        # Display email info
        print(f"\n📋 Email Information:")
        print("-" * 50)
        print(f"   Subject: {parsed_email.subject}")
        print(f"   From: {parsed_email.sender}")
        print(f"   Attachments: {len(parsed_email.attachments)}")
        if parsed_email.has_pdf_attachments:
            print(f"   PDF Attachments: {len(parsed_email.pdf_attachments)}")
            for pdf in parsed_email.pdf_attachments:
                print(f"     - {pdf.filename} ({pdf.size} bytes)")
        
        # Classify the email
        print(f"\n🤖 Running AI Classification...")
        result = classifier.classify_email(parsed_email)
        
        # Display classification results
        print(f"\n📊 Classification Results:")
        print("-" * 50)
        print(f"   🏷️  Classification: {result.classification}")
        print(f"   🎯 Confidence: {result.confidence:.2f}")
        print(f"   💭 Reasoning: {result.reasoning}")
        
        print(f"\n✅ Classification completed successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nMake sure you have:")
        print("1. Set the GEMINI_API_KEY environment variable")
        print("2. Installed all required dependencies: pip install -r requirements.txt")
        print("3. Have internet connectivity")
        print(f"4. The sample email file exists at: {sample_email_path}")


if __name__ == "__main__":
    main() 