# Jetty Infrastructure

Minimal, transferable infrastructure configuration for deploying Jetty on AWS using Docker containers and basic AWS CLI commands.

## Philosophy: Transferable Binaries > Service-Specific Templates

- ✅ **Docker containers** for portability
- ✅ **Simple IAM JSON policies** for clarity  
- ✅ **Basic AWS CLI commands** for deployment
- ❌ No CloudFormation/CDK/SAM vendor lock-in

## Prerequisites
- AWS CLI configured (`aws configure`)
- Docker installed
- Stripe account (for payments)
- Google Cloud account (for Gemini AI)

## Deployment

### 1. Create DynamoDB Table
```bash
aws dynamodb create-table --cli-input-json file://infra/dynamodb/table-schema.json
```

### 2. Create IAM Roles for Each Lambda
```bash
# Create role for status-updater
aws iam create-role \
  --role-name jetty-status-updater-role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "lambda.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# Attach policy
aws iam put-role-policy \
  --role-name jetty-status-updater-role \
  --policy-name jetty-status-updater-policy \
  --policy-document file://infra/iam/status-updater-policy.json

# Repeat for other Lambda functions...
```

### 3. Build & Deploy Docker Images
```bash
# Build and push each Lambda
cd lambda_functions/status_updater
docker build -t jetty-status-updater .
aws ecr create-repository --repository-name jetty-status-updater
docker tag jetty-status-updater:latest {account}.dkr.ecr.{region}.amazonaws.com/jetty-status-updater:latest
docker push {account}.dkr.ecr.{region}.amazonaws.com/jetty-status-updater:latest
```

### 4. Create Lambda Functions
```bash
# Create Lambda function from Docker image
aws lambda create-function \
  --function-name jetty-status-updater \
  --package-type Image \
  --code ImageUri={account}.dkr.ecr.{region}.amazonaws.com/jetty-status-updater:latest \
  --role arn:aws:iam::{account}:role/jetty-status-updater-role \
  --environment Variables='{
    "STRIPE_WEBHOOK_SECRET":"whsec_...",
    "DYNAMODB_TABLE_NAME":"Invoices"
  }'

# Repeat for other Lambda functions...
```

### 5. Setup API Gateway (for Stripe webhooks)
```bash
# Create HTTP API for webhook endpoint
aws apigatewayv2 create-api \
  --name jetty-webhooks \
  --protocol-type HTTP

# Add POST /webhooks/stripe route to status-updater Lambda
```

## Files Structure

```
infra/
├── iam/                         # IAM policies for each Lambda
│   ├── email-classifier-policy.json
│   ├── invoice-extractor-policy.json 
│   ├── payment-scheduler-policy.json
│   └── status-updater-policy.json
├── dynamodb/
│   └── table-schema.json        # DynamoDB table definition
└── README.md                    # This file
```

## Architecture Flow

**Email → Classifier → Extractor → Scheduler → Status Updater**

1. **Email** arrives at SES → stored in S3
2. **email-classifier** λ processes email → sends to SQS if invoice  
3. **invoice-extractor** λ extracts data → stores in DynamoDB
4. **payment-scheduler** λ processes invoices → initiates Stripe payments
5. **status-updater** λ receives Stripe webhooks → updates invoice status to PAID

## Testing
```bash
# Test each component locally
python3 tests/example_classifier_usage.py
python3 tests/example_invoice_extraction.py  
python3 tests/test_payment_scheduler_with_stripe.py
python3 tests/example_status_updater.py
```

## Environment Variables (per Lambda)
```bash
# email-classifier
GEMINI_API_KEY=...

# invoice-extractor  
GEMINI_API_KEY=...
DYNAMODB_TABLE_NAME=Invoices

# payment-scheduler
STRIPE_API_KEY=sk_...
DYNAMODB_TABLE_NAME=Invoices

# status-updater
STRIPE_WEBHOOK_SECRET=whsec_...
DYNAMODB_TABLE_NAME=Invoices
``` 