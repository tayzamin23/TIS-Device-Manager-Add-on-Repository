FROM python:3.12-alpine

WORKDIR /app

COPY backend /app/backend
COPY frontend /app/frontend
COPY run.sh /app/run.sh

RUN pip install --no-cache-dir -r /app/backend/requirements.txt

RUN chmod +x /app/run.sh

EXPOSE 8080

CMD ["/app/run.sh"]
