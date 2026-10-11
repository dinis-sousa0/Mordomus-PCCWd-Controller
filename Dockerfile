FROM python:3.11-slim

WORKDIR /app

# Install pyyaml dependency
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy script and configuration folder 
COPY . /app/

# Ensure Python output prints immediately to stdout
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src

CMD ["python", "src/main.py"]