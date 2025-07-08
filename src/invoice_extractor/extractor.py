"""
Invoice data extractor using Google Gemini
"""

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not available, continue with system env vars

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from ..utils.email_parser import EmailParser, ParsedEmail

MAX_OUTPUT_TOKENS = 12000


class InvoiceData(BaseModel):
    """Pydantic model for structured output from Gemini"""
    vendor_name: Optional[str] = Field(description="The company or individual issuing the invoice")
    invoice_id: Optional[str] = Field(description="The vendor's reference number/ID for this invoice")
    due_date: Optional[str] = Field(description="When payment is due (YYYY-MM-DD format)")
    total_amount: Optional[str] = Field(description="The final amount to be paid (numeric only)")
    currency: Optional[str] = Field(description="The currency code (e.g., USD, EUR, GBP)")


@dataclass
class InvoiceExtractionResult:
    """Result of invoice data extraction"""
    vendor_name: Optional[str]
    invoice_id: Optional[str]
    due_date: Optional[str]
    total_amount: Optional[str]
    currency: Optional[str]
    raw_response: str
    extraction_successful: bool


class InvoiceExtractor:
    """Invoice data extractor using Google Gemini"""
    
    def __init__(self, api_key: str = None):
        """
        Initialize the invoice extractor.
        
        Args:
            api_key: Gemini API key. If None, will try to get from GEMINI_API_KEY env var
        """
        # Get API key
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found. Please set the environment variable or pass api_key parameter.")
        
        # Initialize Gemini client
        self.client = genai.Client(api_key=self.api_key)
        
        # Load prompt template
        self.prompt_template = self._load_prompt_template()
        
        # Initialize email parser
        self.email_parser = EmailParser()
    
    def _load_prompt_template(self) -> str:
        """Load the extraction prompt template"""
        prompt_path = Path(__file__).parent / "prompts" / "invoice_extraction.md"
        return prompt_path.read_text()
    
    def extract_from_email(self, parsed_email: ParsedEmail) -> InvoiceExtractionResult:
        """
        Extract invoice data from a parsed email.
        
        Args:
            parsed_email: ParsedEmail object with extracted content
            
        Returns:
            InvoiceExtractionResult with extracted invoice data
        """
        # Prepare content parts for the API call
        content_parts = []
        
        # Add email text content
        pdf_note = "**PDF Attachments:** None"
        if parsed_email.has_pdf_attachments:
            pdf_note = f"**PDF Attachments:** {len(parsed_email.pdf_attachments)} PDF(s) attached and included for analysis"
        
        # Use string replacement instead of format to avoid conflicts
        prompt = self.prompt_template.replace('{subject}', parsed_email.subject)
        prompt = prompt.replace('{sender}', parsed_email.sender)
        prompt = prompt.replace('{body}', parsed_email.body)
        prompt = prompt.replace('{pdf_note}', pdf_note)
        
        content_parts.append(prompt)
        
        # Add PDF attachments directly to content
        for pdf_attachment in parsed_email.pdf_attachments:
            pdf_part = types.Part.from_bytes(
                data=pdf_attachment.content,
                mime_type='application/pdf'
            )
            content_parts.append(pdf_part)

        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash", 
                contents=content_parts,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": InvoiceData,
                    "temperature": 0.0,
                    "max_output_tokens": MAX_OUTPUT_TOKENS
                }
            )
        
            # Parse the JSON response
            result_data = json.loads(response.text)
            
            # Validate the response matches our expected format
            invoice_data = InvoiceData(**result_data)
            
            return InvoiceExtractionResult(
                vendor_name=invoice_data.vendor_name,
                invoice_id=invoice_data.invoice_id,
                due_date=invoice_data.due_date,
                total_amount=invoice_data.total_amount,
                currency=invoice_data.currency,
                raw_response=response.text,
                extraction_successful=True
            )
            
        except Exception as e:
            print(f"Extraction failed: {e}")
            return InvoiceExtractionResult(
                vendor_name=None,
                invoice_id=None,
                due_date=None,
                total_amount=None,
                currency=None,
                raw_response=str(e),
                extraction_successful=False
            )
    
    def extract_from_email_content(self, email_content: str) -> InvoiceExtractionResult:
        """
        Extract invoice data from raw email content.
        
        Args:
            email_content: Raw email content as string or bytes
            
        Returns:
            InvoiceExtractionResult with extracted invoice data
        """
        parsed_email = self.email_parser.parse_email(email_content)
        return self.extract_from_email(parsed_email)

    def extract_from_email_file(self, file_path: str) -> InvoiceExtractionResult:
        """
        Extract invoice data from an email file.
        
        Args:
            file_path: Path to the email file
            
        Returns:
            InvoiceExtractionResult with extracted invoice data
        """
        parsed_email = self.email_parser.parse_from_file(file_path)
        return self.extract_from_email(parsed_email) 