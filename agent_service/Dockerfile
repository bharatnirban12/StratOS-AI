FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install requirements (allowing pip to resolve versions)
COPY agent_service/requirements.txt agent_service/requirements.txt
RUN pip install --no-cache-dir torch sentence-transformers -r agent_service/requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu




# Copy full project
COPY . .

# Set Python path
ENV PYTHONPATH=/app

# Run the agent service
CMD ["python", "agent_service/main.py"]
