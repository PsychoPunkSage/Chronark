import os
import hashlib
import requests
from datetime import datetime
from pymongo import MongoClient
from flask import Flask, render_template, request, jsonify

from jaeger_client import Config
from flask_opentracing import FlaskTracing

app = Flask(__name__)

# Fetch environment variables
SELF_PORT = os.environ.get('SELF_PORT')
MONGO_DB_HOST = os.environ.get('MONGO_DB_HOST')
MONGO_DB_PORT = os.environ.get('MONGO_DB_PORT')
MONGO_DB_USERNAME = os.environ.get('MONGO_DB_USERNAME')
MONGO_DB_PASSWORD = os.environ.get('MONGO_DB_PASSWORD')
# Customer Info
CUSTOMER_INFO_SERVICE_HOST = os.environ.get('CUSTOMER_INFO_SERVICE_HOST')
CUSTOMER_INFO_SERVICE_PORT = os.environ.get('CUSTOMER_INFO_SERVICE_PORT')
CUSTOMER_INFO_SERVICE_URL = f'http://{CUSTOMER_INFO_SERVICE_HOST}:{CUSTOMER_INFO_SERVICE_PORT}'
# Customer Activity
CUSTOMER_ACTIVITY_SERVICE_HOST = os.environ.get('CUSTOMER_ACTIVITY_SERVICE_HOST')
CUSTOMER_ACTIVITY_SERVICE_PORT = os.environ.get('CUSTOMER_ACTIVITY_SERVICE_PORT')
CUSTOMER_ACTIVITY_SERVICE_URL = f'http://{CUSTOMER_ACTIVITY_SERVICE_HOST}:{CUSTOMER_ACTIVITY_SERVICE_PORT}'
# Jaegar integration
JAEGER_AGENT_HOST = os.environ.get('JAEGER_AGENT_HOST')
JAEGER_AGENT_PORT = os.environ.get('JAEGER_AGENT_PORT')
JAEGER_SERVICE_URL = 'http://' + JAEGER_AGENT_HOST + ':' + JAEGER_AGENT_PORT

def init_tracer():
    config = Config(
        config={
            'sampler': {
                'type': 'const',
                'param': 1,
            },
            'local_agent': {
                'reporting_host': JAEGER_AGENT_HOST,
                'reporting_port': JAEGER_AGENT_PORT,
            },
            'logging': True,
        },
        service_name='ms-credit-card',
    )
    return config.initialize_tracer()

tracer = init_tracer()
tracing = FlaskTracing(tracer, True, app)

def trace_mongo_operation(scope, operation: str, collection_name: str, query: dict):
    span = scope.span
    
    span.set_tag('db.type', 'mongodb')
    span.set_tag('db.collection', collection_name)
    span.set_tag('db.operation', operation)
    span.log_kv({'query': query})

# ================================================================================================ #

# MongoDB connection
client = MongoClient(
    host=MONGO_DB_HOST,
    port=int(MONGO_DB_PORT),
    username=MONGO_DB_USERNAME,
    password=MONGO_DB_PASSWORD
)

# Database and collection initialization
db = client.credit_card
credit_card_collection = db.info

class CreditCard:
    def __init__(self, account_number="", username="", secret_passcode="", balance="", credit_card=""):
        self.username = username
        self.account_number = account_number
        self.credit_card = credit_card
        self.balance = balance
        self.secret_passcode = secret_passcode

# ===================================================================================================================================================================================== #

@app.route('/', methods=['GET'])
@tracing.trace()
def index():
    with tracer.start_active_span('/credit-card/') as scope:
        return render_template(
            'index.html', 
            m_client=client, 
            MONGO_DB_HOST=MONGO_DB_HOST, 
            MONGO_DB_PORT=MONGO_DB_PORT, 
            MONGO_DB_PASSWORD=MONGO_DB_PASSWORD, 
            MONGO_DB_USERNAME=MONGO_DB_USERNAME,
        )

# ===================================================================================================================================================================================== #

@app.route('/get_credit_card_info/<string:username>', methods=['GET'])
@tracing.trace()
def get_credit_card_info(username):
    with tracer.start_active_span('/credit-card/get_credit_card_info/<uname>') as scope:
        card = credit_card_collection.find_one({"username": username}, {"_id": 0})

        if not card:
            return jsonify({"status": "error", "message": "No Credit Card found for this user"}), 400

        return jsonify(card), 200


# ===================================================================================================================================================================================== #

@app.route('/generate_credit_card', methods=['POST'])
@tracing.trace()
def generate_credit_card():
    with tracer.start_active_span('/credit-card/generate_credit_card') as scope:
        data = request.json
        username = data.get('username')
        account_number = data.get('account_number')
        secret_passcode = data.get('secret_passcode')
        balance = data.get('balance')

        if not account_number or not secret_passcode or not balance:
            return jsonify({"message": "Missing required fields"}), 400

        credit_card = generate_credit_card_number(username, account_number, secret_passcode, balance)
        resp, code = update_credit_card_number(username, account_number, credit_card, balance, secret_passcode)

        if code != 200:
            return jsonify({"message": resp}), code
        else:
            return jsonify({"credit_card_number": credit_card}), 200

# ===================================================================================================================================================================================== #

@app.route('/deposit_funds', methods=['POST'])
@tracing.trace()
def deposit_funds():
    with tracer.start_active_span('/credit-card/deposit_funds') as scope:
        data = request.json
        username = data.get('username')
        deposit_amount = data.get('deposit_amount')

        with tracer.start_active_span('mongo_insert') as mongo_span:
            trace_mongo_operation(mongo_span, 'find', 'credit-card/deposit_funds', username)
            credit_card_data = credit_card_collection.find_one({"username": username})

        account_number = credit_card_data.get('account_number')
        credit_card = credit_card_data.get('credit_card')

        if not credit_card_data:
            return jsonify({"message": "Credit Card not found"}), 404

        # ===== Updating Balance =====
        with tracer.start_active_span('/credit-card/deposit_funds/getCustomerInfo') as ccScope:
            resp = response = requests.get(f'{CUSTOMER_INFO_SERVICE_URL}/getCustomerInfo/{username}')
            
        if resp.status_code != 200:
            return  jsonify({"status": "error", "message": "Unexpected"}), 404
        customer_data = response.json()
        acc_balance = customer_data.get('acc_balance')

        if int(deposit_amount) > int(acc_balance):
            return jsonify({"status": "declined", "message": "Fund Amount exceeds your bank balance"}), 404

        remaining_balance = int(acc_balance) - int(deposit_amount)

        with tracer.start_active_span('/credit-card/deposit_funds/updateCustomerInfo') as ccScope:
            response = requests.put(f'{CUSTOMER_INFO_SERVICE_URL}/updateCustomerInfo', json={"username": username, "acc_balance": remaining_balance})

        if response.status_code!= 200:
            return jsonify({"status": "error", "message": "Can't update the balance"}), 404
        # ===== ================ =====

        new_balance = int(credit_card_data['balance']) + int(deposit_amount)

        with tracer.start_active_span('mongo_insert') as mongo_span:
            trace_mongo_operation(mongo_span, 'update', 'credit-card/deposit_funds', account_number)
            credit_card_collection.update_one(
                {"account_number": account_number},
                {"$set": {"balance": new_balance}}
            )

        # Send the Txn details to <Customer Activity>
        activity_data = {
            "username": username,
            "from": account_number,
            "to": credit_card,
            "timestamp": datetime.now().isoformat(),
            "transaction_type": f"CREDIT CARD",
            "transaction_amount": deposit_amount,
            "comments": f"Fund Deposit"
        }

        with tracer.start_active_span('/credit-card/deposit_funds/updateCustomerActivity') as ccScope:
            response = requests.post(f'{CUSTOMER_ACTIVITY_SERVICE_URL}/updateCustomerActivity', json=activity_data)
        if response.status_code != 200:
            return f'Failed to Update Activity  <br>Status Code: {response.status_code} <br>Error: {response.json()}'


        return jsonify({"message": "Deposit successful", "new_balance": new_balance}), 200

# ===================================================================================================================================================================================== #

@app.route('/withdraw_funds', methods=['POST'])
@tracing.trace()
def withdraw_funds():
    with tracer.start_active_span('/credit-card/withdraw_funds') as scope:
        data = request.json
        username = data.get('username')
        withdraw_amount = data.get('withdraw_amount')

        with tracer.start_active_span('mongo_insert') as mongo_span:
            trace_mongo_operation(mongo_span, 'find', 'credit-card/withdraw_funds', username)
            account_data = credit_card_collection.find_one({"username": username})
        account_number = account_data.get('account_number')
        credit_card = account_data.get('credit_card')

        if not account_data:
            return jsonify({"message": "Account not found"}), 404

        current_balance = account_data['balance']

        if int(withdraw_amount) > int(current_balance):
            return jsonify({"message": "Insufficient funds"}), 400

        new_balance = int(current_balance) - int(withdraw_amount)

        with tracer.start_active_span('mongo_insert') as mongo_span:
            trace_mongo_operation(mongo_span, 'update', 'credit-card/withdraw_funds', username)
            credit_card_collection.update_one(
                {"username": username},
                {"$set": {"balance": new_balance}}
            )

        # ===== Updating Balance =====
        with tracer.start_active_span('/credit-card/withdraw_funds/getCustomerInfo') as ccScope:
            resp = response = requests.get(f'{CUSTOMER_INFO_SERVICE_URL}/getCustomerInfo/{username}')

        if resp.status_code != 200:
            return  jsonify({"status": "error", "message": "Unexpected"}), 404
        customer_data = response.json()
        acc_balance = customer_data.get('acc_balance')

        remaining_balance = int(acc_balance) + int(withdraw_amount)

        with tracer.start_active_span('/credit-card/withdraw_funds/updateCustomerActivity') as ccScope:
            response = requests.put(f'{CUSTOMER_INFO_SERVICE_URL}/updateCustomerInfo', json={"username": username, "acc_balance": remaining_balance})

        if response.status_code!= 200:
            return jsonify({"status": "error", "message": "Can't update the balance"}), 404
        # ===== ================ =====

        # Send the Txn details to <Customer Activity>
        activity_data = {
            "username": username,
            "to": account_number,
            "from": credit_card,
            "timestamp": datetime.now().isoformat(),
            "transaction_type": f"CREDIT CARD",
            "transaction_amount": withdraw_amount,
            "comments": f"Fund Withdraw"
        }

        with tracer.start_active_span('/credit-card/withdraw_funds/updateCustomerActivity') as ccScope:
            response = requests.post(f'{CUSTOMER_ACTIVITY_SERVICE_URL}/updateCustomerActivity', json=activity_data)

        if response.status_code != 200:
            return f'Failed to Update Activity  <br>Status Code: {response.status_code} <br>Error: {response.json()}'

        return jsonify({"message": "Withdrawal successful", "new_balance": new_balance}), 200

# ===================================================================================================================================================================================== #

def generate_credit_card_number(username, account_number, secret_passcode, balance):
    """
    Generate a unique 16-digit credit card number using the account number, secret passcode, and balance.
    """
    hashed_twice = hashlib.sha256(f"{username}_{account_number}_{secret_passcode}_{balance}".encode()).hexdigest()
    credit_card_number = "7" + str(int(hashed_twice, 16) % (10 ** 15))
    return credit_card_number

def update_credit_card_number(username, account_number, new_credit_card_number, balance, secret_passcode):
    """
    Update the MongoDB database with the new credit card number.
    If the account does not exist, it will be inserted.
    """

    with tracer.start_active_span('mongo_insert') as mongo_span:
        trace_mongo_operation(mongo_span, 'find', 'credit-card/update_credit_card_number', account_number)
        account_data = credit_card_collection.find_one({"account_number": account_number})

    # ===== Updating Balance =====
    with tracer.start_active_span('/credit-card/update_credit_card_number/getCustomerInfo/<username>') as ccScope:
        resp = response = requests.get(f'{CUSTOMER_INFO_SERVICE_URL}/getCustomerInfo/{username}')
    if resp.status_code != 200:
        return  jsonify({"status": "error", "message": "Unexpected"}), 404
    customer_data = response.json()
    acc_balance = customer_data.get('acc_balance')

    if int(balance) > int(acc_balance):
        return jsonify({"status": "declined", "message": "Fund Amount exceeds your bank balance"}), 404
    
    remaining_balance = int(acc_balance) - int(balance)

    with tracer.start_active_span('/credit-card/update_credit_card_number/updateCustomerInfo') as ccScope:
        response = requests.put(f'{CUSTOMER_INFO_SERVICE_URL}/updateCustomerInfo', json={"username": username, "acc_balance": remaining_balance})

    if response.status_code!= 200:
        return jsonify({"status": "error", "message": "Can't update the balance"}), 404
    # ===== ================ =====

    if account_data:
        with tracer.start_active_span('mongo_insert') as mongo_span:
            trace_mongo_operation(mongo_span, 'update', 'credit-card/update_credit_card_number', account_number)
            credit_card_collection.update_one(
                {"account_number": account_number}, 
                {"$set": {
                    "credit_card": new_credit_card_number, 
                    "username": username, 
                    "balance": balance, 
                    "secret_passcode": secret_passcode
                }}
            )
    else:
        with tracer.start_active_span('mongo_insert') as mongo_span:
            trace_mongo_operation(mongo_span, 'insert', 'credit-card/update_credit_card_number', account_number)
            credit_card_collection.insert_one({
                "account_number": account_number,
                "username": username,
                "credit_card": new_credit_card_number,
                "balance": balance,
                "secret_passcode": secret_passcode
            })

    with tracer.start_active_span('/credit-card/update_credit_card_number/updateCustomerInfo') as ccScope:
        response = requests.put(f'{CUSTOMER_INFO_SERVICE_URL}/updateCustomerInfo', json={"username": username, "credit_card": new_credit_card_number})
    if response.status_code!= 200:
        return jsonify({"status": "error", "message": "Can't update the balance"}), 404

    # Send the Txn details to <Customer Activity>
    activity_data = {
        "username": username,
        "from": account_number,
        "to": new_credit_card_number,
        "timestamp": datetime.now().isoformat(),
        "transaction_type": f"CREDIT CARD",
        "transaction_amount": balance,
        "comments": f"Created"
    }

    with tracer.start_active_span('/credit-card/update_credit_card_number/updateCustomerActivity') as ccScope:
        response = requests.post(f'{CUSTOMER_ACTIVITY_SERVICE_URL}/updateCustomerActivity', json=activity_data)

    if response.status_code != 200:
        return f'Failed to Update Activity  <br>Status Code: {response.status_code} <br>Error: {response.json()}', 404
    
    return jsonify({"status": "approved", "message": "Credit card info has been updated"}), 200
        

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(SELF_PORT), debug=True)
