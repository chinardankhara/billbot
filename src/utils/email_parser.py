"""
MIME email parser for extracting content from emails with PDF attachment handling.
"""

import email
import email.policy
from email.message import EmailMessage
from typing import Dict, List, Optional, Union, Tuple
from dataclasses import dataclass


@dataclass
class EmailAttachment:
    """Dataclass for email attachment metadata."""
    filename: str
    content_type: str
    content: bytes
    size: int


@dataclass
class ParsedEmail:
    """Dataclass for parsed email content."""
    subject: str
    sender: str
    body: str
    attachments: List[EmailAttachment]
    
    @property
    def pdf_attachments(self) -> List[EmailAttachment]:
        """Get only PDF attachments."""
        return [att for att in self.attachments if att.content_type == 'application/pdf']
    
    @property
    def has_pdf_attachments(self) -> bool:
        """Check if email has PDF attachments."""
        return len(self.pdf_attachments) > 0


class EmailParser:
    """Parser for MIME emails with attachment handling."""
    
    def __init__(self):
        """Initialize the email parser."""
        pass
    
    def parse_email(self, email_content: Union[str, bytes]) -> ParsedEmail:
        """
        Parse a MIME email and extract all relevant content.
        
        Args:
            email_content: Raw email content as string or bytes
            
        Returns:
            ParsedEmail object with extracted content
        """
        if isinstance(email_content, bytes):
            email_content = email_content.decode('utf-8', errors='ignore')
        
        # Parse the email
        msg = email.message_from_string(email_content, policy=email.policy.default)
        
        # Extract basic info
        subject = self._get_header(msg, 'Subject')
        sender = self._get_header(msg, 'From')
        
        # Extract body content
        body = self._extract_body(msg)
        
        # Extract attachments
        attachments = self._extract_attachments(msg)
        
        return ParsedEmail(
            subject=subject,
            sender=sender,
            body=body,
            attachments=attachments
        )
    
    def _get_header(self, msg: EmailMessage, header_name: str) -> str:
        """Extract header value from email message."""
        header = msg.get(header_name, '')
        return str(header) if header else ''
    
    def _extract_body(self, msg: EmailMessage) -> str:
        """Extract the main body text from email."""
        body_parts = []
        
        # Handle multipart messages
        if msg.is_multipart():
            for part in msg.walk():
                # Skip attachments and focus on main content
                if part.get_content_disposition() == 'attachment':
                    continue
                    
                if part.get_content_type() == 'text/plain':
                    content = part.get_content()
                    if content:
                        body_parts.append(content)
                elif part.get_content_type() == 'text/html':
                    # For HTML, we'll take it as-is for now
                    # In production, you might want to convert HTML to text
                    content = part.get_content()
                    if content:
                        body_parts.append(content)
        else:
            # Single part message
            if msg.get_content_type().startswith('text/'):
                content = msg.get_content()
                if content:
                    body_parts.append(content)
        
        return '\n\n'.join(body_parts)
    
    def _extract_attachments(self, msg: EmailMessage) -> List[EmailAttachment]:
        """
        Extract all attachments from the email.
        
        Returns:
            List of EmailAttachment objects
        """
        attachments = []
        
        for part in msg.walk():
            # Skip multipart containers
            if part.get_content_maintype() == 'multipart':
                continue
                
            # Skip text parts (already handled in body extraction)
            if part.get_content_type().startswith('text/') and part.get_content_disposition() != 'attachment':
                continue
            
            # Get filename
            filename = part.get_filename()
            if filename:
                try:
                    content = part.get_payload(decode=True)
                    if content:
                        attachment = EmailAttachment(
                            filename=filename,
                            content_type=part.get_content_type(),
                            content=content,
                            size=len(content)
                        )
                        attachments.append(attachment)
                except Exception as e:
                    print(f"Error extracting attachment {filename}: {e}")
        
        return attachments
    
    def parse_from_file(self, file_path: str) -> ParsedEmail:
        """
        Parse email from a file.
        
        Args:
            file_path: Path to the email file
            
        Returns:
            ParsedEmail object with extracted content
        """
        with open(file_path, 'rb') as f:
            email_content = f.read()
        
        return self.parse_email(email_content)
    
    def get_attachment_summary(self, parsed_email: ParsedEmail) -> Dict:
        """
        Get a summary of attachments in the email.
        
        Args:
            parsed_email: ParsedEmail object
            
        Returns:
            Dictionary with attachment summary
        """
        total_attachments = len(parsed_email.attachments)
        pdf_count = len(parsed_email.pdf_attachments)
        total_size = sum(att.size for att in parsed_email.attachments)
        
        return {
            "total_attachments": total_attachments,
            "pdf_attachments": pdf_count,
            "total_size_bytes": total_size,
            "attachment_types": list(set(att.content_type for att in parsed_email.attachments))
        } 