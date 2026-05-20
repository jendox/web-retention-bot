FROM python:3.13-alpine

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY shared/ /tmp/shared/
COPY viber/ /app/

RUN pip install --no-cache-dir /tmp/shared \
    && pip install --no-cache-dir /app

EXPOSE 8092

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8092", "--workers", "1"]