FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p /app/media && chmod 700 /app/media
EXPOSE 8000
EXPOSE 8080
# Railway injeta $PORT — usa a porta dinâmica, fallback 8080 (padrão Railway).
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8080}"]
