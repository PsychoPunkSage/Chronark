FROM python:3.12.0-slim

WORKDIR /app/helper/

COPY ./hredis.py .
COPY ./requirements.txt .
COPY ./.env .

RUN pip install -r requirements.txt