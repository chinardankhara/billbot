# Use AWS Lambda Python runtime
FROM public.ecr.aws/lambda/python:3.10-x86_64

# Copy requirements and install dependencies
COPY requirements.txt ${LAMBDA_TASK_ROOT}
RUN pip install -r requirements.txt

# Copy business logic (must be copied to build context first)
COPY app.py ${LAMBDA_TASK_ROOT}

# Copy the Lambda handler
COPY lambda_function.py ${LAMBDA_TASK_ROOT}

# Set the CMD to your handler
CMD ["lambda_function.lambda_handler"] 