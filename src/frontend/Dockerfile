FROM python:3.12.0-slim

WORKDIR /app/src/frontend

COPY . .

RUN pip install -r requirements.txt

CMD ["python", "app.py"]