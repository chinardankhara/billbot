# Use the official AWS Lambda Python 3.10 base image
FROM public.ecr.aws/lambda/python:3.10-x86_64

# Copy the core business logic from src
COPY src/utils/email_parser.py ${LAMBDA_TASK_ROOT}/email_parser.py
COPY src/extractor.py ${LAMBDA_TASK_ROOT}/invoice_extractor.py
COPY src/dynamo_writer.py ${LAMBDA_TASK_ROOT}/dynamo_writer.py
COPY src/invoice_extractor/prompts/ ${LAMBDA_TASK_ROOT}/prompts/

# Copy the Lambda function handler
COPY lambda_functions/invoice_extractor/lambda_function.py ${LAMBDA_TASK_ROOT}/

# Copy requirements.txt and install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt --target "${LAMBDA_TASK_ROOT}"

# Set the CMD to your handler (filename.handler_function)
CMD [ "lambda_function.lambda_handler" ] 