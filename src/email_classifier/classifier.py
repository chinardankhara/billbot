"""
Email classifier for binary classification: INVOICE vs NOT_INVOICE
"""

import json
import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not available, continue with system env vars

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from email_parser import EmailParser, ParsedEmail

MAX_OUTPUT_TOKENS=3600

class ClassificationResult(BaseModel):
    """Pydantic model for structured output from Gemini"""
    classification: str = Field(description="Either 'INVOICE' or 'NOT_INVOICE'")
    reasoning: str = Field(description="Brief explanation of the classification decision")


@dataclass
class EmailClassificationResult:
    """Result of email classification"""
    classification: str
    reasoning: str
    raw_response: str


class EmailClassifier:
    """Binary email classifier using Google Gemini"""
    
    def __init__(self, api_key: str = None):
        """
        Initialize the email classifier.
        
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
        """Load the classification prompt template"""
        prompt_path = Path(__file__).parent / "prompts" / "binary_classification.md"
        return prompt_path.read_text()
    
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
                    "response_schema": ClassificationResult,
                    "temperature": 0.0,
                    "max_output_tokens": MAX_OUTPUT_TOKENS
                }
            )
        
            # Parse the JSON response
            result_data = json.loads(response.text)
            
            # Validate the response matches our expected format
            classification_result = ClassificationResult(**result_data)
            
            return EmailClassificationResult(
                classification=classification_result.classification,
                reasoning=classification_result.reasoning,
                raw_response=response.text
            )
            
        except Exception as e:
            raise RuntimeError(f"Classification failed: {e}")
    
    def classify_email_content(self, email_content: str) -> EmailClassificationResult:
        """
        Classify an email from raw content.
        
        Args:
            email_content: Raw email content as string or bytes
            
        Returns:
            EmailClassificationResult with classification details
        """
        parsed_email = self.email_parser.parse_email(email_content)
        return self.classify_email(parsed_email)

    def classify_email_file(self, file_path: str) -> EmailClassificationResult:
        """
        Classify an email from a file.
        
        Args:
            file_path: Path to the email file
            
        Returns:
            EmailClassificationResult with classification details
        """
        parsed_email = self.email_parser.parse_from_file(file_path)
        return self.classify_email(parsed_email) 