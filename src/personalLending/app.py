import hashlib
import os
from pymongo import MongoClient
from pymemcache.client import base
from flask import Flask, render_template, request, jsonify
import requests

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
personal_lending = data.personal_lending

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
    loan_amount = data.get('amount')
    
    # Check eligibility (simplified example)
    eligibility, max_loan_amount = check_eligibility(username)
    if not eligibility:
        return jsonify({"status": "denied", "message": "Not eligible for loan"}), 400
    else:
        if int(loan_amount) > max_loan_amount:
            return jsonify({"status": "pending", "message": "Loan Amount exceeds Max allowable capacity"}), 200
        # Create loan application
        loan_data = {
            "loan_id": get_loan_id(username, data["amount"], data["term"], data["purpose"]),
            "username": username,
            "amount": data['amount'],
            "term": data['term'],
            "purpose": data['purpose'],
            "status": "approved"
        }
        personal_lending.insert_one(loan_data)

        return jsonify({"status": "pending", "approved": "Loan application accepted"}), 200

@app.route('/loan/<loan_id>', methods=['GET'])
def get_loan(loan_id):
    # Check cache first
    loan = cache.get(loan_id)
    if loan:
        return loan
    
    loan = personal_lending.find_one({"loan_id": loan_id}, {"_id": 0})
    if not loan:
        return jsonify({"status": "error", "message": "Loan not found"}), 404
    
    # Cache the loan details for future requests
    cache.set(loan_id, loan) 
    return jsonify(loan), 200

@app.route('/loans/<username>', methods=['GET'])
def get_all_loans(username):
    loans = list(personal_lending.find({"username": username}, {"_id": 0}))
    
    if not loans:
        return jsonify({"status": "error", "message": "No loans found for this user"}), 400
    
    return jsonify(loans), 200

@app.route('/pay_loan', methods=['POST'])
def pay_loan():
    jsonData = request.json
    loan_id = jsonData.get('loanId')
    pay_amount = jsonData.get('amount')
    username = jsonData.get('username')

    # Check cache first
    loan = personal_lending.find_one({"loan_id": loan_id}, {"_id": 0})
    if not loan:
        return jsonify({"status": "error", "message": "Loan not found"}), 404
    
    resp = response = requests.get(f'{CUSTOMER_INFO_SERVICE_URL}/getCustomerInfo/{username}')
    if resp.status_code != 200:
        return  jsonify({"status": "error", "message": "Unexpected"}), 404
    customer_data = response.json()
    acc_balance = customer_data.get('acc_balance')
    
    if int(pay_amount) > acc_balance:
        return jsonify({"status": "error", "message": "Insufficient funds"}), 400
    
    # Update customer's account balance
    ###########
    # VERY BIGGGG LOOPHOLE... Amount should be updated after loan has been repayed....
    ###########
    new_balance = acc_balance - int(pay_amount)
    response = requests.put(f'{CUSTOMER_INFO_SERVICE_URL}/updateCustomerInfo', json={"username": username, "acc_balance": new_balance})
    if response.status_code!= 200:
        return jsonify({"status": "error", "message": "Can't update the balance"}), 404

    # Update loan status
    loan_amt = loan.get("amount")
    if int(loan_amt) > int(pay_amount):
        personal_lending.update_one({"loan_id": loan_id}, {"$set": {"amount": int(loan_amt)-int(pay_amount)}})
        return jsonify({"status": "success", "message": "Partial Payment successful"}), 200
    
    else:
        personal_lending.delete_one({"loan_id": loan_id})
        return jsonify({"status": "success", "message": "Loan fully paid off"}), 200

def check_eligibility(username):
    '''
      If the 
        (Acc balance + Dmat Balance) > 5000 then Max-loan = 2*(Acc balance + Dmat Balance)

      Returns:
        Boolean value indicating eligibility
        Maximum loan amount if eligible
    '''
    # Get customer info
    response = requests.get(f'{CUSTOMER_INFO_SERVICE_URL}/getCustomerInfo/{username}')

    if response.status_code != 200:
        return False, 0
    
    customer_data = response.json()
    total_balance = customer_data.get("acc_balance") + customer_data.get("dmat_balance")

    if total_balance >= 4500:
        return True, 2*(total_balance)
    else:
        return False, 0

def get_loan_id(username, amount, term, purpose):
    unique_string = f"{username}_{amount}_{term}_{purpose}"
    hash_object = hashlib.sha256(unique_string.encode())
    hex_dig = hash_object.hexdigest()
    digits = ''.join(filter(str.isdigit, hex_dig))
    loan_id = '1' + digits[:15]
    loan_id = loan_id.ljust(16, '0')

    return loan_id


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=SELF_PORT, debug=True)