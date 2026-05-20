FROM python:3.13-alpine

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY shared/ /tmp/shared
COPY telegram/ /app/

RUN pip install --no-cache-dir /tmp/shared \
    && pip install --no-cache-dir /app

EXPOSE 8091

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8091", "--workers", "1"]
