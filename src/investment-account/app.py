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
# Customer Activity
CUSTOMER_ACTIVITY_SERVICE_HOST = os.environ.get('CUSTOMER_ACTIVITY_SERVICE_HOST')
CUSTOMER_ACTIVITY_SERVICE_PORT = os.environ.get('CUSTOMER_ACTIVITY_SERVICE_PORT')
CUSTOMER_ACTIVITY_SERVICE_URL = f'http://{CUSTOMER_ACTIVITY_SERVICE_HOST}:{CUSTOMER_ACTIVITY_SERVICE_PORT}'

db_client = MongoClient(
    username=MONGO_DB_USERNAME, 
    password=MONGO_DB_PASSWORD, 
    host=MONGO_DB_HOST, 
    port=int(MONGO_DB_PORT)
)

data = db_client.investments
investment_db = data.investment

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
        MONGO_DB_HOST=MONGO_DB_HOST, 
        MONGO_DB_PORT=MONGO_DB_PORT, 
        MONGO_DB_PASSWORD=MONGO_DB_PASSWORD, 
        MONGO_DB_USERNAME=MONGO_DB_USERNAME, 
        cache=cache,
        MEMCACHED_HOST=MEMCACHED_HOST, 
        MEMCACHED_PORT=MEMCACHED_PORT
    )

# ===================================================================================================================================================================================== #

@app.route('/investment', methods=['POST'])
def investment():
    data = request.json
    amount = data.get('amount')
    username = data.get('username')
    duration = data.get('duration')
    invested_in = data.get('invested_in')
    investment_type = data.get('investment_type')

    eligibility, max_invest_amount, account_number = check_eligibility(int(amount), username)

    if not eligibility:
        return jsonify({"status": "denied", "message": "Not eligible for investment"}), 400
    
    else:
        if int(amount) > max_invest_amount:
            return jsonify({"status": "pending", "message": "Investment Amount exceeds Max allowable capacity"}), 200

        investment_id = get_investment_id(username, amount, duration, invested_in, investment_type)
        investment_data = {
            "investment_id": investment_id,
            "username": username,
            "amount": amount,
            "duration": duration,
            "date": datetime.now(),
            "invested_in": invested_in,
            "investment_type": investment_type,
            "status": "approved",
        }

        # Deduct `amount` from User Balance:
        resp = response = requests.get(f'{CUSTOMER_INFO_SERVICE_URL}/getCustomerInfo/{username}')
        if resp.status_code != 200:
            return  jsonify({"status": "error", "message": "Unexpected"}), 404
        customer_data = response.json()
        acc_balance = customer_data.get('acc_balance')
        dmat_balance = customer_data.get('dmat_balance')

        remaining_balance = int(acc_balance) - int(amount)
        response = requests.put(f'{CUSTOMER_INFO_SERVICE_URL}/updateCustomerInfo', json={"username": username, "acc_balance": remaining_balance})
        if response.status_code!= 200:
            return jsonify({"status": "error", "message": "Can't update the balance"}), 404
        
        response = requests.put(f'{CUSTOMER_INFO_SERVICE_URL}/updateCustomerInfo', json={"username": username, "dmat_balance": int(dmat_balance) + int(amount)})
        if response.status_code!= 200:
            return jsonify({"status": "error", "message": "Can't update the balance"}), 404

        # Send the Txn details to <Customer Activity>
        activity_data = {
            "username": username,
            "from": account_number,
            "to": investment_id,
            "timestamp": datetime.now().isoformat(),
            "transaction_type": f"Investment: {investment_type}",
            "transaction_amount": amount,
            "comments": f"in {invested_in}"
        }

        response = requests.post(f'{CUSTOMER_ACTIVITY_SERVICE_URL}/updateCustomerActivity', json=activity_data)
        if response.status_code != 200:
            return f'Failed to Update Activity  <br>Status Code: {response.status_code} <br>Error: {response.json()}'

        investment_db.insert_one(investment_data)

        return jsonify({"status": "approved", "message": "Investment Successful"})

@app.route('/get_investment/<string:investment_id>', methods=['GET'])
def get_investment(investment_id):
    # Check cache first
    investment = cache.get(investment_id)
    if investment:
        return investment
    
    investment = investment_db.find_one({"investment_id": investment_id}, {"_id": 0})
    if not investment:
        return jsonify({"status": "error", "message": "Investment not found"}), 404
    
    cache.set(investment_id, investment) 
    return jsonify(investment), 200

@app.route('/investments/<string:username>', methods=['GET'])
def get_all_investments(username):
    investment = list(investment_db.find({"username": username}, {"_id": 0}))
    
    if not investment:
        return jsonify({"status": "error", "message": "No Investments found for this user"}), 400
    
    return jsonify(investment), 200

@app.route('/redeem_investment', methods=['POST'])
def redeem_investment():
    jsonData = request.json
    username = jsonData.get('username')
    investment_id = jsonData.get('investment_id')
    amount_redeem = jsonData.get('amount_redeem')

    investment = investment_db.find_one({"investment_id": investment_id}, {"_id": 0})
    if not investment:
        return jsonify({"status": "error", "message": "Investment not found"}), 404

    if investment.get('status')!= 'approved':
        return jsonify({"status": "error", "message": "Investment not approved"}), 400
    
    invested_amount = int(investment.get('amount'))
    investment_type = investment.get('investment_type')
    invested_in = investment.get('invested_in')
    
    resp = response = requests.get(f'{CUSTOMER_INFO_SERVICE_URL}/getCustomerInfo/{username}')
    if resp.status_code != 200:
        return  jsonify({"status": "error", "message": "Unexpected"}), 404
    customer_data = response.json()
    acc_balance = customer_data.get('acc_balance')
    dmat_balance = customer_data.get('dmat_balance')
    account_number = customer_data.get('account_number')

    if int(amount_redeem) > invested_amount:
        return jsonify({"status": "error", "message": "Investment amount is less than redeem amount"}), 400
    
    remaining_investment = invested_amount - int(amount_redeem)

    if remaining_investment == 0:
        investment_db.delete_one({"investment_id": investment_id})
    else:
        investment_db.update_one({"investment_id": investment_id}, {"$set": {"amount": remaining_investment}})

    # Update User Dmat/account balance
    remaining_balance = int(acc_balance) + int(amount_redeem)
    response = requests.put(f'{CUSTOMER_INFO_SERVICE_URL}/updateCustomerInfo', json={"username": username, "acc_balance": remaining_balance})
    if response.status_code!= 200:
        return jsonify({"status": "error", "message": "Can't update the balance <ACCOUNT>"}), 404
    
    response = requests.put(f'{CUSTOMER_INFO_SERVICE_URL}/updateCustomerInfo', json={"username": username, "dmat_balance": int(dmat_balance) - int(amount_redeem)})
    if response.status_code!= 200:
        return jsonify({"status": "error", "message": "Can't update the balance <DMAT>"}), 404

    # Send the Txn details to <Customer Activity>
    activity_data = {
        "username": username,
        "to": account_number,
        "from": investment_id,
        "timestamp": datetime.now().isoformat(),
        "transaction_type": "Investment: Redeem",
        "transaction_amount": amount_redeem,
        "comments": f"from {investment_type}:{invested_in}"
    }

    response = requests.post(f'{CUSTOMER_ACTIVITY_SERVICE_URL}/updateCustomerActivity', json=activity_data)
    if response.status_code != 200:
        return f'Failed to Update Activity  <br>Status Code: {response.status_code} <br>Error: {response.json()}'

    return jsonify({"status": "success", "message": "Investment Redeemed Successfully"}), 200

# ===================================================================================================================================================================================== #

def get_investment_id(username, amount, duration, property_value, down_payment):
    unique_string = f"{username}_{amount}_{duration}_{property_value}_{down_payment}"
    hash_object = hashlib.sha256(unique_string.encode())
    hex_dig = hash_object.hexdigest()
    digits = ''.join(filter(str.isdigit, hex_dig))
    investment_id = '3' + digits[:15]
    investment_id = investment_id.ljust(16, '0')

    return investment_id

def check_eligibility(amount, username):
    # Get customer info
    response = requests.get(f'{CUSTOMER_INFO_SERVICE_URL}/getCustomerInfo/{username}')

    if response.status_code != 200:
        return False, 0, customer_data.get("account_number")
    
    customer_data = response.json()
    total_balance = customer_data.get("acc_balance")

    if int(total_balance) > amount:
        return True, int(total_balance), customer_data.get("account_number")
    
    return False, 0, customer_data.get("account_number")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=SELF_PORT, debug=True)