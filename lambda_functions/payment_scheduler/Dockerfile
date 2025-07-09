# Use AWS Lambda Python base image
FROM public.ecr.aws/lambda/python:3.10-x86_64

# Copy requirements and install dependencies
COPY requirements.txt ${LAMBDA_TASK_ROOT}
RUN pip install -r requirements.txt

# Copy source code from src/ directory
COPY src/payment_scheduler/*.py ${LAMBDA_TASK_ROOT}/
COPY src/utils/ ${LAMBDA_TASK_ROOT}/utils/

# Copy Lambda-specific files
COPY lambda_functions/payment_scheduler/lambda_function.py ${LAMBDA_TASK_ROOT}

# Debug: List files to verify structure
RUN ls -la ${LAMBDA_TASK_ROOT}/ && echo "Files copied successfully"

# Set the CMD to your handler
CMD ["lambda_function.lambda_handler"] 