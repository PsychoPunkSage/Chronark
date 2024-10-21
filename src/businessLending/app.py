from datetime import datetime
import os
import hashlib
import requests
from pymongo import MongoClient
from pymemcache.client import base
from flask import Flask, render_template, request, jsonify

from jaeger_client import Config
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
        service_name='ms-business-lending',
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
@tracing.trace()
def index():
    with tracer.start_active_span('/b-lend/') as scope:
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
def apply_bloan():
    with tracer.start_active_span('/b-lend/apply') as scope:
        data = request.json
        username = data.get('username')
        bloan_amount = data.get('amount')
        term = data.get('term')
        purpose = data.get('purpose')

        # Check eligibility
        eligibility, max_bloan_amount, account_number = check_eligibility(username)
        if not eligibility:
            return jsonify({"status": "denied", "message": "Not eligible for bloan"}), 400
        else:
            if int(bloan_amount) > max_bloan_amount:
                return jsonify({"status": "pending", "message": "Business Loan Amount exceeds Max allowable capacity"}), 200

            bloan_id = get_bloan_id(username, bloan_amount, term, purpose)
            # Create bloan application
            loan_data = {
                "bloan_id": bloan_id,
                "term": term,
                "username": username,
                "amount": bloan_amount,
                "purpose": purpose,
                "status": "approved"
            }

            # Send the Txn details to <Customer Activity>
            activity_data = {
                "username": username,
                "from": account_number,
                "to": bloan_id,
                "timestamp": datetime.now().isoformat(),
                "transaction_type": "B-Loan",
                "transaction_amount": bloan_amount,
                "comments": purpose
            }

            with tracer.start_active_span('/b-lend/apply/updateCustomerActivity') as scope:
                response = requests.post(f'{CUSTOMER_ACTIVITY_SERVICE_URL}/updateCustomerActivity', json=activity_data)
                
            if response.status_code != 200:
                return f'Failed to Update Activity  <br>Status Code: {response.status_code} <br>Error: {response.json()}'

            with tracer.start_active_span('mongo_insert') as mongo_span:
                trace_mongo_operation(mongo_span, 'insert', 'business_lending/apply_bloan', loan_data)
                business_lending.insert_one(loan_data)

            return jsonify({"status": "approved", "message": "Business Loan application accepted"}), 200

@app.route('/bloan/<bloan_id>', methods=['GET'])
@tracing.trace()
def get_bloan(bloan_id):
    with tracer.start_active_span('/b-lend/bloan/<id>') as scope:
        # Check cache first
        bloan = cache.get(bloan_id)
        if bloan:
            return bloan
        
        with tracer.start_active_span('mongo_insert') as mongo_span:
            trace_mongo_operation(mongo_span, 'find', 'business_lending/get_bloan', bloan)
            bloan = business_lending.find_one({"bloan_id": bloan_id}, {"_id": 0})

        if not bloan:
            return jsonify({"status": "error", "message": "Business Loan not found"}), 404

        # Cache the bloan details for future requests
        cache.set(bloan_id, bloan)
        return jsonify(bloan), 200

@app.route('/bloans/<username>', methods=['GET'])
@tracing.trace()
def get_all_bloans(username):
    with tracer.start_active_span('/b-lend/bloans/<uname>') as scope:
        with tracer.start_active_span('mongo_insert') as mongo_span:
            bloans = list(business_lending.find({"username": username}, {"_id": 0}))
            trace_mongo_operation(mongo_span, 'find', 'business_lending/pay_bloan', bloans)

        if not bloans:
            return jsonify({"status": "error", "message": "No bloans found for this business"}), 400

        return jsonify(bloans), 200

@app.route('/pay_bloan', methods=['POST'])
@tracing.trace()
def pay_bloan():
    with tracer.start_active_span('/b-lend/pay_bloan') as scope:
        jsonData = request.json
        bloan_id = jsonData.get('bloan_id')
        pay_amount = jsonData.get('amount')
        username = jsonData.get('username')
    
        # Check cache first
        bloan = business_lending.find_one({"bloan_id": bloan_id}, {"_id": 0})
        if not bloan:
            return jsonify({"status": "error", "message": "Business Loan not found"}), 404
        
        with tracer.start_active_span('/b-lend/pay_bloan/getCustomerInfo/<username>') as scope:
            resp = response = requests.get(f'{CUSTOMER_INFO_SERVICE_URL}/getCustomerInfo/{username}')
        if resp.status_code != 200:
            return  jsonify({"status": "error", "message": "Unexpected"}), 404
        customer_data = response.json()
        acc_balance = customer_data.get('acc_balance')
        account_number = customer_data.get('account_number')
        
        if int(pay_amount) > acc_balance:
            return jsonify({"status": "error", "message": "Insufficient funds"}), 400
        
        # Update business's account balance
        ###########
        # VERY BIGGGG LOOPHOLE... Amount should be updated after bloan has been repayed....
        ###########
        new_balance = acc_balance - int(pay_amount)

        with tracer.start_active_span('/b-lend/pay_bloan/updateCustomerInfo') as scope:
            response = requests.put(f'{CUSTOMER_INFO_SERVICE_URL}/updateCustomerInfo', json={"username": username, "acc_balance": new_balance})
        if response.status_code!= 200:
            return jsonify({"status": "error", "message": "Can't update the balance"}), 404
    
        # Send the Txn details to <Customer Activity>
        activity_data = {
            "username": username,
            "to": account_number,
            "from": bloan_id,
            "timestamp": datetime.now().isoformat(),
            "transaction_type": "B-Loan",
            "transaction_amount": pay_amount,
            "comments": "REPAYMENT"
        }

        with tracer.start_active_span('/b-lend/pay_bloan/updateCustomerActivity') as scope:
            response = requests.post(f'{CUSTOMER_ACTIVITY_SERVICE_URL}/updateCustomerActivity', json=activity_data)
        if response.status_code != 200:
            return f'Failed to Update Activity  <br>Status Code: {response.status_code} <br>Error: {response.json()}'
    
    
        # Update bloan status
        loan_amt = bloan.get("amount")
        if int(loan_amt) > int(pay_amount):
            with tracer.start_active_span('mongo_insert') as mongo_span:
                trace_mongo_operation(mongo_span, 'update', 'business_lending/pay_bloan', bloan)
                business_lending.update_one({"bloan_id": bloan_id}, {"$set": {"amount": int(loan_amt)-int(pay_amount)}})
            return jsonify({"status": "success", "message": "Partial Payment successful"}), 200
        
        else:
            with tracer.start_active_span('mongo_insert') as mongo_span:
                trace_mongo_operation(mongo_span, 'delete', 'business_lending/pay_bloan', bloan)
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
    with tracer.start_active_span('/b-lend/check_eligibility/getCustomerInfo/<username>') as scope:
        response = requests.get(f'{CUSTOMER_INFO_SERVICE_URL}/getCustomerInfo/{username}')

    if response.status_code != 200:
        return False, 0, customer_data.get("account_number")
    
    customer_data = response.json()
    total_balance = customer_data.get("acc_balance") + customer_data.get("dmat_balance")

    if total_balance >= 5000:
        return True, 2*(total_balance), customer_data.get("account_number")
    else:
        return False, 0, customer_data.get("account_number")

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
