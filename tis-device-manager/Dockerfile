FROM python:3.12-alpine

WORKDIR /app

# system deps for bcrypt, cryptography
RUN apk add --no-cache gcc musl-dev libffi-dev openssl-dev

COPY backend /app/backend
COPY frontend /app/frontend
COPY run.sh /app/run.sh

RUN pip install --no-cache-dir -r /app/backend/requirements.txt

RUN chmod +x /app/run.sh

EXPOSE 8080

CMD ["/app/run.sh"]
