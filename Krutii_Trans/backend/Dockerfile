# Бекенд KRUTII TRANS: Flask API, аналітика, ML, симулятор телематики
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=5001 \
    TZ=Europe/Kyiv \
    PYTHONWARNINGS=ignore::DeprecationWarning

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends tzdata && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
EXPOSE 5001
CMD ["python", "docker-entrypoint.py"]
