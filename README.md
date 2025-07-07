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

## Development Setup

1. Install dependencies: `pip install -r requirements.txt`
2. Set up AWS credentials
3. Configure environment variables
4. Deploy infrastructure: `sam deploy`

## Deployment

All AWS resources are defined as Infrastructure as Code using AWS SAM. Lambda dependencies are managed via AWS Lambda Layers built in Docker containers. 