FROM python:3.11-slim

WORKDIR /app

# Disable stdout buffering so logs render in real-time in Docker
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "mordomus_bridge.py"]