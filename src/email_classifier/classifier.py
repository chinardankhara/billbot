"""
Email classifier using Google Gemini AI with direct PDF support.
Combines classification logic and CLI interface in a single module.
"""

import os
import sys
import json
import argparse
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from pathlib import Path

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from ..utils.email_parser import EmailParser, ParsedEmail


class ClassificationResult(BaseModel):
    """Pydantic model for classification result."""
    classification: str = Field(description="INVOICE or NOT_INVOICE")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score between 0 and 1")
    reasoning: str = Field(description="Brief explanation of classification")


@dataclass
class EmailClassificationResult:
    """Result of email classification."""
    classification: str
    confidence: float
    reasoning: str
    raw_response: str


class EmailClassifier:
    """Email classifier using Google Gemini AI with direct PDF support."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Gemini classifier.
        
        Args:
            api_key: Gemini API key. If None, will try to get from environment
        """
        if api_key is None:
            api_key = os.getenv('GEMINI_API_KEY')
        
        if not api_key:
            raise ValueError("Gemini API key is required. Set GEMINI_API_KEY environment variable or pass api_key parameter.")
        
        self.client = genai.Client(api_key=api_key)
        
        # Load prompt template
        self.prompt_template = self._load_prompt_template()
    
    def _load_prompt_template(self) -> str:
        """Load the prompt template from markdown file."""
        prompt_path = Path(__file__).parent / 'prompts' / 'binary_classification.md'
        
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"Prompt template not found at {prompt_path}")
    
    def classify_email(self, parsed_email: ParsedEmail) -> EmailClassificationResult:
        """
        Classify an email as INVOICE or NOT_INVOICE.
        
        Args:
            parsed_email: ParsedEmail object with extracted content
            
        Returns:
            EmailClassificationResult with classification details
        """
        # Prepare content parts for the API call
        content_parts = []
        
        # Add email text content
        pdf_note = "**PDF Attachments:** None"
        if parsed_email.has_pdf_attachments:
            pdf_note = f"**PDF Attachments:** {len(parsed_email.pdf_attachments)} PDF(s) attached and included for analysis"
            
        prompt = self.prompt_template.format(
            subject=parsed_email.subject,
            sender=parsed_email.sender,
            body=parsed_email.body,
            pdf_note=pdf_note
        )
        
        content_parts.append(prompt)
        
        # Add PDF attachments directly to content
        for pdf_attachment in parsed_email.pdf_attachments:
            pdf_part = types.Part.from_bytes(
                data=pdf_attachment.content,
                mime_type='application/pdf'
            )
            content_parts.append(pdf_part)
        
        try:
            # Make the API call with structured output
            response = self.client.models.generate_content(
                model="gemini-2.0-flash-exp",
                contents=content_parts,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ClassificationResult,
                    temperature=0.1,  # Low temperature for consistent classification
                    max_output_tokens=1000
                )
            )
            
            # Parse the JSON response
            result_data = json.loads(response.text)
            
            # Validate the response matches our expected format
            classification_result = ClassificationResult(**result_data)
            
            return EmailClassificationResult(
                classification=classification_result.classification,
                confidence=classification_result.confidence,
                reasoning=classification_result.reasoning,
                raw_response=response.text
            )
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON response: {e}")
        except Exception as e:
            raise RuntimeError(f"Classification failed: {e}")
    
    def classify_from_file(self, email_file_path: str) -> EmailClassificationResult:
        """
        Classify an email directly from a file.
        
        Args:
            email_file_path: Path to the email file
            
        Returns:
            EmailClassificationResult with classification details
        """
        parser = EmailParser()
        parsed_email = parser.parse_from_file(email_file_path)
        
        return self.classify_email(parsed_email)
    
    def get_classification_stats(self, results: List[EmailClassificationResult]) -> Dict[str, Any]:
        """
        Get statistics from a batch of classification results.
        
        Args:
            results: List of classification results
            
        Returns:
            Dictionary with classification statistics
        """
        total = len(results)
        if total == 0:
            return {"total": 0}
        
        invoice_count = sum(1 for r in results if r.classification == "INVOICE")
        not_invoice_count = sum(1 for r in results if r.classification == "NOT_INVOICE")
        error_count = sum(1 for r in results if r.classification == "ERROR")
        
        avg_confidence = sum(r.confidence for r in results if r.classification != "ERROR") / max(1, total - error_count)
        
        return {
            "total": total,
            "invoice_count": invoice_count,
            "not_invoice_count": not_invoice_count,
            "error_count": error_count,
            "invoice_percentage": (invoice_count / total) * 100,
            "average_confidence": avg_confidence
        }


def classify_single_email(email_path: str, api_key: str = None) -> None:
    """
    Classify a single email file.
    
    Args:
        email_path: Path to the email file
        api_key: Gemini API key
    """
    try:
        print(f"Classifying email: {email_path}")
        
        # Initialize classifier
        classifier = EmailClassifier(api_key=api_key)
        
        # Classify the email
        result = classifier.classify_from_file(email_path)
        
        # Display results
        print(f"\n{'='*50}")
        print(f"CLASSIFICATION: {result.classification}")
        print(f"CONFIDENCE: {result.confidence:.2f}")
        print(f"REASONING: {result.reasoning}")
        print(f"{'='*50}")
        
    except Exception as e:
        print(f"Error classifying email: {e}")
        sys.exit(1)


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(description="Email classifier using Gemini AI")
    parser.add_argument("--api-key", help="Gemini API key (or set GEMINI_API_KEY env var)")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Single email classification
    single_parser = subparsers.add_parser("single", help="Classify a single email file")
    single_parser.add_argument("email_path", help="Path to the email file")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Check for API key
    api_key = args.api_key or os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("Error: Gemini API key required. Set GEMINI_API_KEY environment variable or use --api-key")
        sys.exit(1)
    
    # Execute command
    if args.command == "single":
        classify_single_email(args.email_path, api_key)


if __name__ == "__main__":
    main() 