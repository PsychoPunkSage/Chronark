import os
import hashlib
import requests
from datetime import datetime
from pymongo import MongoClient
from pymemcache.client import base
from flask import Flask, render_template, request, jsonify

from jaeger_client import Config, Span
from flask_opentracing import FlaskTracing

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
        service_name='ms-personal-lend',
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

def trace_memcached_operation(scope, operation: str, key: str, value: str = None):
    span = scope.span
    
    span.set_tag('cache.type', 'memcached')
    span.set_tag('cache.operation', operation)
    span.set_tag('cache.key', key)
    
    if value:
        span.set_tag('cache.value', value)  # Optionally log value for 'set' operations
    
    span.log_kv({'key': key, 'value': value if value else 'N/A'})

# ================================================================================================ #

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
@tracing.trace()
def index():
    with tracer.start_active_span('/personal-lend/') as scope:
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

@app.route('/apply', methods=['POST'])
@tracing.trace()
def apply_loan():
    with tracer.start_active_span('/personal-lend/apply') as scope:
        data = request.json
        loan_term = data.get('term')
        username = data.get('username')
        loan_amount = data.get('amount')
        loan_purpose = data.get('purpose')

        # Check eligibility
        eligibility, max_loan_amount, account_number = check_eligibility(username)
        if not eligibility:
            return jsonify({"status": "denied", "message": "Not eligible for loan"}), 400
        else:
            if int(loan_amount) > max_loan_amount:
                return jsonify({"status": "pending", "message": "Loan Amount exceeds Max allowable capacity"}), 200

            loan_id = get_loan_id(username, loan_amount, loan_term, loan_purpose)
            # Create loan application
            loan_data = {
                "loan_id": loan_id,
                "term": loan_term,
                "username": username,
                "amount": loan_amount,
                "purpose": loan_purpose,
                "status": "approved"
            }

            # Send the Txn details to <Customer Activity>
            activity_data = {
                "username": username,
                "from": account_number,
                "to": loan_id,
                "timestamp": datetime.now().isoformat(),
                "transaction_type": "Loan",
                "transaction_amount": loan_amount,
                "comments": loan_purpose
            }

            with tracer.start_active_span('/personal-lend/apply/updateCustomerActivity') as loanScope:
                response = requests.post(f'{CUSTOMER_ACTIVITY_SERVICE_URL}/updateCustomerActivity', json=activity_data)

            if response.status_code != 200:
                return f'Failed to Update Activity  <br>Status Code: {response.status_code} <br>Error: {response.json()}'

            with tracer.start_active_span('mongo_insert') as mongo_span:
                trace_mongo_operation(mongo_span, 'insert', 'personal_lending/apply_loan', loan_data)
                personal_lending.insert_one(loan_data)

            return jsonify({"status": "approved", "message": "Loan application accepted"}), 200

@app.route('/loan/<loan_id>', methods=['GET'])
@tracing.trace()
def get_loan(loan_id):
    with tracer.start_active_span('/personal-lend/loan/<loan_id>') as scope:
        # Check cache first
        with tracer.start_active_span('memcached_get') as cache_span:
            trace_memcached_operation(cache_span, 'get', loan_id)
            loan = cache.get(loan_id)

        if loan:
            return loan

        with tracer.start_active_span('mongo_insert') as mongo_span:
            trace_mongo_operation(mongo_span, 'find', 'personal_lending/loan/<loan_id>', {'loan_id': loan_id})
            loan = personal_lending.find_one({"loan_id": loan_id}, {"_id": 0})

        if not loan:
            return jsonify({"status": "error", "message": "Loan not found"}), 404

        # Cache the loan details for future requests
        with tracer.start_active_span('memcached_set') as cache_span:
            trace_memcached_operation(cache_span, 'set', loan_id, str(loan))
            cache.set(loan_id, loan)
            
        return jsonify(loan), 200

@app.route('/loans/<username>', methods=['GET'])
@tracing.trace()
def get_all_loans(username):
    with tracer.start_active_span('/personal-lend/loans/<uname>') as scope:

        with tracer.start_active_span('mongo_insert') as mongo_span:
            trace_mongo_operation(mongo_span, 'find', 'personal_lending/loans/<uname>', {"username": username})
            loans = list(personal_lending.find({"username": username}, {"_id": 0}))

        if not loans:
            return jsonify({"status": "error", "message": "No loans found for this user"}), 400

        return jsonify(loans), 200

@app.route('/pay_loan', methods=['POST'])
@tracing.trace()
def pay_loan():
    with tracer.start_active_span('/personal-lend/pay_loan') as scope:
        jsonData = request.json
        loan_id = jsonData.get('loanId')
        pay_amount = jsonData.get('amount')
        username = jsonData.get('username')

        # Check cache first
        with tracer.start_active_span('mongo_insert') as mongo_span:
            trace_mongo_operation(mongo_span, 'find', 'personal_lending/pay_loan', {"loan_id": loan_id})
            loan = personal_lending.find_one({"loan_id": loan_id}, {"_id": 0})

        if not loan:
            return jsonify({"status": "error", "message": "Loan not found"}), 404

        with tracer.start_active_span('/personal-lend/getCustomerInfo/<uname>') as loan1Scope:
            resp = response = requests.get(f'{CUSTOMER_INFO_SERVICE_URL}/getCustomerInfo/{username}')

        if resp.status_code != 200:
            return  jsonify({"status": "error", "message": "Unexpected"}), 404
        customer_data = response.json()
        acc_balance = customer_data.get('acc_balance')
        account_number = customer_data.get('account_number')

        if int(pay_amount) > acc_balance:
            return jsonify({"status": "error", "message": "Insufficient funds"}), 400

        # Update customer's account balance
        ###########
        # VERY BIGGGG LOOPHOLE... Amount should be updated after loan has been repayed....
        ###########
        new_balance = acc_balance - int(pay_amount)

        with tracer.start_active_span('/personal-lend/updateCustomerInfo') as loan1Scope:
            response = requests.put(f'{CUSTOMER_INFO_SERVICE_URL}/updateCustomerInfo', json={"username": username, "acc_balance": new_balance})

        if response.status_code!= 200:
            return jsonify({"status": "error", "message": "Can't update the balance"}), 404

        # Send the Txn details to <Customer Activity>
        activity_data = {
            "username": username,
            "to": account_number,
            "from": loan_id,
            "timestamp": datetime.now().isoformat(),
            "transaction_type": "Loan",
            "transaction_amount": pay_amount,
            "comments": "REPAYMENT"
        }

        with tracer.start_active_span('/personal-lend/updateCustomerActivity') as loan1Scope:
            response = requests.post(f'{CUSTOMER_ACTIVITY_SERVICE_URL}/updateCustomerActivity', json=activity_data)

        if response.status_code != 200:
            return f'Failed to Update Activity  <br>Status Code: {response.status_code} <br>Error: {response.json()}'


        # Update loan status
        loan_amt = loan.get("amount")
        if int(loan_amt) > int(pay_amount):
            with tracer.start_active_span('mongo_insert') as mongo_span:
                trace_mongo_operation(mongo_span, 'update', 'personal_lending/pay_loan', {"loan_id": loan_id})
                personal_lending.update_one({"loan_id": loan_id}, {"$set": {"amount": int(loan_amt)-int(pay_amount)}})

            return jsonify({"status": "success", "message": "Partial Payment successful"}), 200

        else:
            with tracer.start_active_span('mongo_insert') as mongo_span:
                trace_mongo_operation(mongo_span, 'delete', 'personal_lending/pay_loan', {"loan_id": loan_id})  
                personal_lending.delete_one({"loan_id": loan_id})

            return jsonify({"status": "success", "message": "Loan fully paid off"}), 200

# ===================================================================================================================================================================================== #

def check_eligibility(username):
    '''
      If the 
        (Acc balance + Dmat Balance) > 5000 then Max-loan = 2*(Acc balance + Dmat Balance)

      Returns:
        Boolean value indicating eligibility
        Maximum loan amount if eligible
    '''
    # Get customer info
    with tracer.start_active_span('/personal-lend/getCustomerInfo/<uname>') as loanScope:
        response = requests.get(f'{CUSTOMER_INFO_SERVICE_URL}/getCustomerInfo/{username}')

        if response.status_code != 200:
            return False, 0, customer_data.get("account_number")

        customer_data = response.json()
        total_balance = customer_data.get("acc_balance") + customer_data.get("dmat_balance")

        if total_balance >= 4500:
            return True, 2*(total_balance), customer_data.get("account_number")
        else:
            return False, 0, customer_data.get("account_number")

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