# Use the official AWS Lambda Python 3.10 base image
FROM public.ecr.aws/lambda/python:3.10-x86_64
# Copy the function code and prompts into the Lambda task root directory
COPY src/utils/email_parser.py ${LAMBDA_TASK_ROOT}/email_parser.py
COPY src/email_classifier/classifier.py ${LAMBDA_TASK_ROOT}/email_classifier.py
COPY src/email_classifier/prompts/ ${LAMBDA_TASK_ROOT}/prompts/
COPY lambda_function.py ${LAMBDA_TASK_ROOT}/

# Copy requirements.txt and install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt --target "${LAMBDA_TASK_ROOT}"

# Set the CMD to your handler (filename.handler_function)
CMD [ "lambda_function.lambda_handler" ] 