FROM python:3.10-slim

WORKDIR /app

# Install dependencies first (cached layer)
COPY orchestrator/requirements.txt orchestrator/requirements.txt
RUN pip install --no-cache-dir -r orchestrator/requirements.txt

# Copy full project
COPY . .

# Set Python path
ENV PYTHONPATH=/app

# Run the orchestrator
CMD ["python", "orchestrator/main.py"]