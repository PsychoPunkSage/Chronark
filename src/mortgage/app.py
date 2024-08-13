import os
import hashlib
import requests
from datetime import datetime
from pymongo import MongoClient
from pymemcache.client import base
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

SELF_PORT = os.environ.get('SELF_PORT')
MONGO_DB_HOST = os.environ.get('MONGO_DB_HOST')
MONGO_DB_PORT = os.environ.get('MONGO_DB_PORT')
MONGO_DB_USERNAME = os.environ.get('MONGO_DB_USERNAME')
MONGO_DB_PASSWORD = os.environ.get('MONGO_DB_PASSWORD')
MEMCACHED_HOST = os.environ.get('MEMCACHED_HOST')
MEMCACHED_PORT = os.environ.get('MEMCACHED_PORT')
# Customer Info
CUSTOMER_INFO_SERVICE_HOST = os.environ.get('CUSTOMER_INFO_SERVICE_HOST')
CUSTOMER_INFO_SERVICE_PORT = os.environ.get('CUSTOMER_INFO_SERVICE_PORT')
CUSTOMER_INFO_SERVICE_URL = f'http://{CUSTOMER_INFO_SERVICE_HOST}:{CUSTOMER_INFO_SERVICE_PORT}'

db_client = MongoClient(
    username=MONGO_DB_USERNAME, 
    password=MONGO_DB_PASSWORD, 
    host=MONGO_DB_HOST, 
    port=int(MONGO_DB_PORT)
)

data = db_client.loans
mortgage_collection = data.mortgage

# MEMCACHED Setup
cache = base.Client(
    (MEMCACHED_HOST, int(MEMCACHED_PORT))
)

# ===================================================================================================================================================================================== #

@app.route('/', methods=['GET'])
def index():
    return render_template(
        'index.html', 
        m_client=db_client, 
        MONGO_HOST=MONGO_DB_HOST, 
        MONGO_PORT=MONGO_DB_PORT, 
        MONGO_PASSWORD=MONGO_DB_PASSWORD, 
        MONGO_USERNAME=MONGO_DB_USERNAME, 
        cache=cache,
        MEMCACHED_HOST=MEMCACHED_HOST, 
        MEMCACHED_PORT=MEMCACHED_PORT
    )

# ===================================================================================================================================================================================== #

@app.route('/apply_mortgage', methods=['POST'])
def apply_mortgage():
    data = request.json
    username = data.get('username')
    amount = data.get('amount')
    term = data.get('term')
    property_value = data.get('property_value')
    down_payment = data.get('down_payment')
    
    interest_rate = 7 # %
    # Check eligibility (simplified example)
    eligibility, max_mortgage_amount = check_eligibility(username, property_value, down_payment)
    if not eligibility:
        return jsonify({"status": "denied", "message": "Not eligible for mortgage"}), 400
    if int(amount) > max_mortgage_amount:
        return jsonify({"status": "denied", "message": "Requested amount exceeds max mortgage limit"}), 400

    # Create mortgage application
    mortgage_data = {
        "mortgage_id": get_mortgage_id(username, amount, term, interest_rate, property_value, down_payment),
        "username": username,
        "amount": amount,
        "term": term,
        "interest_rate": interest_rate,
        "property_value": property_value,
        "down_payment": down_payment,
        "status": "approved",
        "application_date": datetime.now(),
        "monthly_payment": calculate_monthly_payment(amount, term, interest_rate),
        "outstanding_balance": amount
    }
    mortgage_collection.insert_one(mortgage_data)

    return jsonify({"status": "pending", "approved": "Mortgage application accepted"}), 200

@app.route('/mortgage/<mortgage_id>', methods=['GET'])
def get_mortgage(mortgage_id):
    # Check cache first
    mortgage = cache.get(mortgage_id)
    if mortgage:
        return mortgage
    
    mortgage = mortgage_collection.find_one({"mortgage_id": mortgage_id}, {"_id": 0})
    if not mortgage:
        return jsonify({"status": "error", "message": "Mortgage not found"}), 404
    
    # Cache the mortgage details for future requests
    cache.set(mortgage_id, mortgage)
    return jsonify(mortgage), 200

@app.route('/mortgages/<username>', methods=['GET'])
def get_all_mortgages(username):
    mortgages = list(mortgage_collection.find({"username": username}, {"_id": 0}))
    
    if not mortgages:
        return jsonify({"status": "error", "message": "No mortgages found for this user"}), 400
    
    return jsonify(mortgages), 200

@app.route('/pay_mortgage', methods=['POST'])
def pay_mortgage():
    jsonData = request.json
    mortgage_id = jsonData.get('mortgage_id')
    pay_amount = jsonData.get('amount')
    username = jsonData.get('username')

    mortgage = mortgage_collection.find_one({"mortgage_id": mortgage_id}, {"_id": 0})
    if not mortgage:
        return jsonify({"status": "error", "message": "Mortgage not found"}), 404
    
    response = requests.get(f'{CUSTOMER_INFO_SERVICE_URL}/getCustomerInfo/{username}')
    if response.status_code != 200:
        return jsonify({"status": "error", "message": "Unexpected"}), 404
    customer_data = response.json()
    acc_balance = customer_data.get('acc_balance')
    
    if int(pay_amount) > int(acc_balance):
        return jsonify({"status": "error", "message": "Insufficient funds"}), 400
    
    # Update customer's account balance
    new_balance = int(acc_balance) - int(pay_amount)
    response = requests.put(f'{CUSTOMER_INFO_SERVICE_URL}/updateCustomerInfo', json={"username": username, "acc_balance": new_balance})
    if response.status_code != 200:
        return jsonify({"status": "error", "message": "Can't update the balance"}), 404

    # Update mortgage status
    outstanding_balance = mortgage.get("outstanding_balance")
    if int(outstanding_balance) > int(pay_amount):
        mortgage_collection.update_one({"mortgage_id": mortgage_id}, {"$set": {"outstanding_balance": int(outstanding_balance) - int(pay_amount)}})
        return jsonify({"status": "success", "message": "Partial Payment successful"}), 200
    else:
        mortgage_collection.delete_one({"mortgage_id": mortgage_id})
        return jsonify({"status": "success", "message": "Mortgage fully paid off"}), 200

# ===================================================================================================================================================================================== #

def check_eligibility(username, property_value, down_payment):
    '''
      Eligibility based on down payment and property value.
      
      Returns:
        Boolean value indicating eligibility
        Maximum mortgage amount if eligible
    '''
    # Get customer info
    response = requests.get(f'{CUSTOMER_INFO_SERVICE_URL}/getCustomerInfo/{username}')

    if response.status_code != 200:
        return False, 0
    
    down_payment_ratio = int(down_payment) / int(property_value)

    if down_payment_ratio >= 0.2:
        return True, 0.8 * int(property_value)
    else:
        return False, 0

def calculate_monthly_payment(amount, term, interest_rate):
    '''
      Calculate monthly payment based on mortgage amount, term, and interest rate.
    '''
    amount = float(amount)  # Convert amount to float
    term = int(term)  # Convert term to integer

    monthly_rate = interest_rate / 12 / 100
    num_payments = term * 12
    monthly_payment = (amount * monthly_rate) / (1 - (1 + monthly_rate) ** -num_payments)

    return round(monthly_payment, 2)

def get_mortgage_id(username, amount, term, interest_rate, property_value, down_payment):
    unique_string = f"{username}_{amount}_{term}_{interest_rate}_{property_value}_{down_payment}"
    hash_object = hashlib.sha256(unique_string.encode())
    hex_dig = hash_object.hexdigest()
    digits = ''.join(filter(str.isdigit, hex_dig))
    mortgage_id = '2' + digits[:15]
    mortgage_id = mortgage_id.ljust(16, '0')

    return mortgage_id

# ===================================================================================================================================================================================== #

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=SELF_PORT, debug=True)