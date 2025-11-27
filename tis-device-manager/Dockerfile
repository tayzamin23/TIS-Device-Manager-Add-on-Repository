FROM python:3.12-slim

WORKDIR /app

COPY backend/requirements.txt /app/requirements.txt

RUN apt-get update \
    && apt-get install -y gcc python3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY backend /app/backend
COPY run.sh /app/run.sh

RUN pip install --no-cache-dir -r /app/requirements.txt

RUN chmod +x /app/run.sh

EXPOSE 8080

CMD ["/app/run.sh"]
