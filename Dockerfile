FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1
ENV DATABASE_URL=sqlite:////tmp/excel_diagnosis.db
ENV UPLOAD_DIR=/tmp/uploads
ENV PORT=10000

EXPOSE 10000

CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
