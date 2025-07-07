# Jetty

A serverless, AI-powered accounts payable (AP) platform designed to automate the entire lifecycle of an invoice for small to medium-sized businesses.

## Project Vision

Jetty eliminates manual data entry, provides intelligent filtering of incoming financial communications, and creates a secure, auditable trail for all vendor payments using a decoupled, event-driven, serverless architecture on AWS.

## Architecture Overview

**Visual Flow:**
```
[Email In] -> AWS SES -> S3 Bucket -> [Trigger] -> (L1) Classifier -> SQS Queue -> [Trigger] -> (L2) Extractor -> DynamoDB -> [Trigger] -> (L3) Payment Scheduler -> Stripe API -> [Webhook] -> (L4) Status Updater -> DynamoDB
```

### Components

1. **Lambda 1: `jetty-classifier`** - The "Triage Nurse" - Classifies incoming emails
2. **Lambda 2: `jetty-extractor`** - The "Data Specialist" - Extracts invoice data using Gemini AI
3. **Lambda 3: `jetty-payment-scheduler`** - The "Payment Initiator" - Schedules payments via Stripe
4. **Lambda 4: `jetty-status-updater`** - The "Accountant" - Handles payment status updates

## Project Structure

```
jetty/
├── README.md
├── pyproject.toml
├── infra/                    # IaC templates (SAM/CDK)
├── src/
│   ├── lambda_classifier/      # Email classification Lambda
│   ├── lambda_extractor/       # Invoice data extraction Lambda
│   ├── lambda_payment/         # Payment scheduler Lambda
│   ├── lambda_status_updater/  # Stripe webhook handler Lambda
│   └── layers/                 # Shared dependencies
└── tests/
```

## Quick Start: Email Classifier

The email classifier is a standalone component that can classify emails as `INVOICE` or `NOT_INVOICE` using Google's Gemini AI.

### Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   # or for development
   pip install -e .
   ```

2. **Set up Gemini API key:**
   ```bash
   export GEMINI_API_KEY="your-gemini-api-key"
   ```

3. **Run the example:**
   ```bash
   python example_usage.py
   ```

### Usage

#### Command Line Interface

```bash
# Classify a single email file
python -m src.email_classifier.classifier single sample_emails/testemail.txt
```

#### Programmatic Usage

```python
from src.utils.email_parser import EmailParser
from src.email_classifier.classifier import EmailClassifier

# Initialize components
parser = EmailParser()
classifier = EmailClassifier()

# Parse and classify an email
parsed_email = parser.parse_from_file("sample_emails/testemail.txt")
result = classifier.classify_email(parsed_email)

print(f"Classification: {result.classification}")
print(f"Confidence: {result.confidence}")
print(f"Reasoning: {result.reasoning}")
```

### Features

- **MIME Email Parsing**: Extracts text from email bodies and headers (supports .txt and .eml formats)
- **Direct PDF Processing**: Uses Gemini's native PDF vision capabilities (no text extraction needed)
- **Structured Output**: Uses Gemini 2.0 Flash with structured JSON output for consistency
- **Batch Processing**: Classify multiple emails at once
- **Confidence Scoring**: Each classification includes a confidence score
- **Detailed Reasoning**: AI provides explanation for each classification
- **Reusable Components**: Email parser can be shared with invoice extractor and other modules

### Architecture

The email classifier follows a modular design with separation of concerns:

- **`utils/email_parser.py`**: Handles MIME parsing and attachment extraction (reusable across modules)
- **`email_classifier/classifier.py`**: Unified module with Gemini AI classification and CLI interface
- **`email_classifier/prompts/`**: Stores prompt templates in markdown files for easy modification
- **Direct PDF Support**: Uses Gemini's native PDF processing instead of text extraction

## Full Platform Development

For the complete serverless AP platform architecture:

### Development Setup

1. Install dependencies: `pip install -e .`
2. Set up AWS credentials
3. Configure environment variables
4. Deploy infrastructure: `sam deploy`

### Deployment

All AWS resources are defined as Infrastructure as Code using AWS SAM. Lambda dependencies are managed via AWS Lambda Layers built in Docker containers. 