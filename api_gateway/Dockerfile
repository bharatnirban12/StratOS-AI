FROM python:3.10-slim

WORKDIR /app

# Install dependencies first (cached layer)
COPY api_gateway/requirements.txt api_gateway/requirements.txt
RUN pip install --no-cache-dir -r api_gateway/requirements.txt

# Copy full project (shared, result_service, api_gateway)
COPY . .

# Set Python path
ENV PYTHONPATH=/app

# Run the API gateway
CMD ["python", "api_gateway/main.py"]