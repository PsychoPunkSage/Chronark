FROM python:3.9

COPY requirements.txt .
RUN python -m pip install -r requirements.txt

WORKDIR /app
COPY openCreditCard.py /app/openCreditCard.py

CMD ["python", "openCreditCard.py"]