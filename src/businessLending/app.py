import os
import hashlib
import requests
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

data = db_client.bloans
business_lending = data.business_lending

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

@app.route('/apply', methods=['POST'])
def apply_loan():
    data = request.json
    username = data.get('username')
    bloan_amount = data.get('amount')
    
    # Check eligibility
    eligibility, max_bloan_amount = check_eligibility(username)
    if not eligibility:
        return jsonify({"status": "denied", "message": "Not eligible for bloan"}), 400
    else:
        if int(bloan_amount) > max_bloan_amount:
            return jsonify({"status": "pending", "message": "Business Loan Amount exceeds Max allowable capacity"}), 200
        # Create bloan application
        loan_data = {
            "bloan_id": get_bloan_id(username, data["amount"], data["term"], data["purpose"]),
            "term": data['term'],
            "username": username,
            "amount": data['amount'],
            "purpose": data['purpose'],
            "status": "approved"
        }
        business_lending.insert_one(loan_data)

        return jsonify({"status": "approved", "message": "Business Loan application accepted"}), 200

@app.route('/bloan/<bloan_id>', methods=['GET'])
def get_bloan(bloan_id):
    # Check cache first
    bloan = cache.get(bloan_id)
    if bloan:
        return bloan
    
    bloan = business_lending.find_one({"bloan_id": bloan_id}, {"_id": 0})
    if not bloan:
        return jsonify({"status": "error", "message": "Business Loan not found"}), 404
    
    # Cache the bloan details for future requests
    cache.set(bloan_id, bloan) 
    return jsonify(bloan), 200

@app.route('/bloans/<username>', methods=['GET'])
def get_all_bloans(username):
    bloans = list(business_lending.find({"username": username}, {"_id": 0}))
    
    if not bloans:
        return jsonify({"status": "error", "message": "No bloans found for this business"}), 400
    
    return jsonify(bloans), 200

@app.route('/pay_loan', methods=['POST'])
def pay_loan():
    jsonData = request.json
    bloan_id = jsonData.get('bloan_id')
    pay_amount = jsonData.get('amount')
    username = jsonData.get('username')

    # Check cache first
    bloan = business_lending.find_one({"bloan_id": bloan_id}, {"_id": 0})
    if not bloan:
        return jsonify({"status": "error", "message": "Business Loan not found"}), 404
    
    resp = response = requests.get(f'{CUSTOMER_INFO_SERVICE_URL}/updateCustomerInfo/{username}')
    if resp.status_code != 200:
        return  jsonify({"status": "error", "message": "Unexpected"}), 404
    customer_data = response.json()
    acc_balance = customer_data.get('acc_balance')
    
    if int(pay_amount) > acc_balance:
        return jsonify({"status": "error", "message": "Insufficient funds"}), 400
    
    # Update business's account balance
    ###########
    # VERY BIGGGG LOOPHOLE... Amount should be updated after bloan has been repayed....
    ###########
    new_balance = acc_balance - int(pay_amount)
    response = requests.put(f'{CUSTOMER_INFO_SERVICE_URL}/updateCustomerInfo', json={"username": username, "acc_balance": new_balance})
    if response.status_code!= 200:
        return jsonify({"status": "error", "message": "Can't update the balance"}), 404

    # Update bloan status
    loan_amt = bloan.get("amount")
    if int(loan_amt) > int(pay_amount):
        business_lending.update_one({"bloan_id": bloan_id}, {"$set": {"amount": int(loan_amt)-int(pay_amount)}})
        return jsonify({"status": "success", "message": "Partial Payment successful"}), 200
    
    else:
        business_lending.delete_one({"bloan_id": bloan_id})
        return jsonify({"status": "success", "message": "Business Loan fully paid off"}), 200

# ===================================================================================================================================================================================== #

def check_eligibility(username):
    '''
      If the 
        (Acc balance + Business Assets Value) > 10000 then Max-bloan = 2*(Acc balance + Business Assets Value)

      Returns:
        Boolean value indicating eligibility
        Maximum bloan amount if eligible
    '''
    # Get business info
    response = requests.get(f'{CUSTOMER_INFO_SERVICE_URL}/getCustomerInfo/{username}')

    if response.status_code != 200:
        return False, 0
    
    customer_data = response.json()
    total_balance = customer_data.get("acc_balance") + customer_data.get("assets_value")

    if total_balance >= 10000:
        return True, 2*(total_balance)
    else:
        return False, 0

def get_bloan_id(username, amount, term, purpose):
    unique_string = f"{username}_{amount}_{term}_{purpose}"
    hash_object = hashlib.sha256(unique_string.encode())
    hex_dig = hash_object.hexdigest()
    digits = ''.join(filter(str.isdigit, hex_dig))
    bloan_id = '4' + digits[:15]
    bloan_id = bloan_id.ljust(16, '0')

    return bloan_id


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=SELF_PORT, debug=True)
