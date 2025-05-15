FROM python:3.11-slim

# Set environment variables for Python
# - PYTHONDONTWRITEBYTECODE=1 prevents Python from writing .pyc files to disk (keeps container clean)
# - PYTHONUNBUFFERED=1 ensures stdout/stderr is unbuffered (logs show up immediately)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /code

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

# Install pip requirements first for better cache
COPY ./api/requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /code/requirements.txt

# Copy the rest of the application code
COPY ./app /code/app

# Expose the port FastAPI will run on
EXPOSE 8000

# Run the app with uvicorn, using multiple workers for production
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
