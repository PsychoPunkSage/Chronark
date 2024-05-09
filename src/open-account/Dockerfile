FROM python:3.9

COPY requirements.txt .
RUN python -m pip install -r requirements.txt

WORKDIR /app
COPY openAccount.py /app/openAccount.py

CMD ["python", "openAccount.py"]
