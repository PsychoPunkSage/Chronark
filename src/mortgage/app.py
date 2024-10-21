import os
import hashlib
import requests
from datetime import datetime
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
        service_name='ms-mortgage',
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
mortgage_collection = data.mortgage

# MEMCACHED Setup
cache = base.Client(
    (MEMCACHED_HOST, int(MEMCACHED_PORT))
)

# ===================================================================================================================================================================================== #

@app.route('/', methods=['GET'])
@tracing.trace()
def index():
    with tracer.start_active_span('/mortgage/') as scope:
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

@app.route('/apply_mortgage', methods=['POST'])
@tracing.trace()
def apply_mortgage():
    with tracer.start_active_span('/mortgage/apply_mortgage') as scope:
        data = request.json
        term = data.get('term')
        amount = data.get('amount')
        username = data.get('username')
        down_payment = data.get('down_payment')
        property_value = data.get('property_value')

        interest_rate = 7 # %
        # Check eligibility (simplified example)
        eligibility, max_mortgage_amount, account_number = check_eligibility(username, property_value, down_payment)
        if not eligibility:
            return jsonify({"status": "denied", "message": "Not eligible for mortgage"}), 400
        if int(amount) > max_mortgage_amount:
            return jsonify({"status": "denied", "message": "Requested amount exceeds max mortgage limit"}), 400

        mortgage_id = get_mortgage_id(username, amount, term, interest_rate, property_value, down_payment)
        # Create mortgage application
        mortgage_data = {
            "mortgage_id": mortgage_id,
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

        # Send the Txn details to <Customer Activity>
        activity_data = {
            "username": username,
            "to": account_number,
            "from": mortgage_id,
            "timestamp": datetime.now().isoformat(),
            "transaction_type": f"Mortgage: {amount}",
            "transaction_amount": down_payment,
            "comments": f"for Property: ₹{property_value}"
        }

        with tracer.start_active_span('/mortgage/apply_mortgage/updateCustomerActivity') as invScope:
            response = requests.post(f'{CUSTOMER_ACTIVITY_SERVICE_URL}/updateCustomerActivity', json=activity_data)
        if response.status_code != 200:
            return f'Failed to Update Activity  <br>Status Code: {response.status_code} <br>Error: {response.json()}'
        
        with tracer.start_active_span('mongo_insert') as mongo_span:
            trace_mongo_operation(mongo_span, 'insert', 'mortgage/apply_mortgage', mortgage_data)
            mortgage_collection.insert_one(mortgage_data)

        return jsonify({"status": "pending", "approved": "Mortgage application accepted"}), 200

@app.route('/mortgage/<mortgage_id>', methods=['GET'])
@tracing.trace()
def get_mortgage(mortgage_id):
    with tracer.start_active_span('/mortgage/mortgage/<mortgage_id>') as scope:
        # Check cache first

        with tracer.start_active_span('memcached_get') as cache_span:
            trace_memcached_operation(cache_span, 'get', mortgage_id)
            mortgage = cache.get(mortgage_id)

        if mortgage:
            return mortgage
        with tracer.start_active_span('mongo_find') as mongo_span:
            trace_mongo_operation(mongo_span, 'find', 'mortgage/get_mortgage', mortgage_id)
            mortgage = mortgage_collection.find_one({"mortgage_id": mortgage_id}, {"_id": 0})

        if not mortgage:
            return jsonify({"status": "error", "message": "Mortgage not found"}), 404

        # Cache the mortgage details for future requests
        with tracer.start_active_span('memcached_set') as cache_span:
            trace_memcached_operation(cache_span, 'set', mortgage_id, str(mortgage))
            cache.set(mortgage_id, mortgage)

        return jsonify(mortgage), 200

@app.route('/mortgages/<username>', methods=['GET'])
@tracing.trace()
def get_all_mortgages(username):
    with tracer.start_active_span('/mortgage/mortgages/<uname>') as scope:

        with tracer.start_active_span('mongo_find') as mongo_span:
            trace_mongo_operation(mongo_span, 'find', 'mortgage/get_all__mortgage', username)
            mortgages = list(mortgage_collection.find({"username": username}, {"_id": 0}))

        if not mortgages:
            return jsonify({"status": "error", "message": "No mortgages found for this user"}), 400

        return jsonify(mortgages), 200

@app.route('/pay_mortgage', methods=['POST'])
@tracing.trace()
def pay_mortgage():
    with tracer.start_active_span('/mortgage/pay_mortgage') as scope:
        jsonData = request.json
        mortgage_id = jsonData.get('mortgage_id')
        pay_amount = jsonData.get('amount')
        username = jsonData.get('username')

        with tracer.start_active_span('mongo_find') as mongo_span:
            trace_mongo_operation(mongo_span, 'find', 'mortgage/pay_mortgage', username)
            mortgage = mortgage_collection.find_one({"mortgage_id": mortgage_id}, {"_id": 0})

        if not mortgage:
            return jsonify({"status": "error", "message": "Mortgage not found"}), 404
        outstanding_balance = mortgage.get("outstanding_balance")
        property_value = mortgage.get("property_value")

        with tracer.start_active_span(f'/mortgage/pay_mortgage/getCustomerInfo/{username}') as mortScope:
            response = requests.get(f'{CUSTOMER_INFO_SERVICE_URL}/getCustomerInfo/{username}')

        if response.status_code != 200:
            return jsonify({"status": "error", "message": "Unexpected"}), 404
        customer_data = response.json()
        acc_balance = customer_data.get('acc_balance')
        account_number = customer_data.get('account_number')

        if int(pay_amount) > int(acc_balance):
            return jsonify({"status": "error", "message": "Insufficient funds"}), 400

        # Update customer's account balance
        new_balance = int(acc_balance) - int(pay_amount)

        with tracer.start_active_span(f'/mortgage/pay_mortgage/updateCustomerInfo') as mortScope:
            response = requests.put(f'{CUSTOMER_INFO_SERVICE_URL}/updateCustomerInfo', json={"username": username, "acc_balance": new_balance})

        if response.status_code != 200:
            return jsonify({"status": "error", "message": "Can't update the balance"}), 404

         # Send the Txn details to <Customer Activity>
        activity_data = {
            "username": username,
            "from": account_number,
            "to": mortgage_id,
            "timestamp": datetime.now().isoformat(),
            "transaction_type": f"Mortgage Payment: {outstanding_balance}",
            "transaction_amount": pay_amount,
            "comments": f"for Property: ₹{property_value}"
        }

        with tracer.start_active_span('/mortgage/pay_mortgage/updateCustomerActivity') as invScope:
            response = requests.post(f'{CUSTOMER_ACTIVITY_SERVICE_URL}/updateCustomerActivity', json=activity_data)
        if response.status_code != 200:
            return f'Failed to Update Activity  <br>Status Code: {response.status_code} <br>Error: {response.json()}'

        # Update mortgage status

        if int(outstanding_balance) > int(pay_amount):
            with tracer.start_active_span('mongo_update') as mongo_span:
                trace_mongo_operation(mongo_span, 'update', 'mortgage/pay_mortgage', {"mortgage_id": mortgage_id, "outstanding_balance": int(outstanding_balance) - int(pay_amount)})
                mortgage_collection.update_one({"mortgage_id": mortgage_id}, {"$set": {"outstanding_balance": int(outstanding_balance) - int(pay_amount)}})

            return jsonify({"status": "success", "message": "Partial Payment successful"}), 200
        else:
            with tracer.start_active_span('mongo_delete') as mongo_span:
                trace_mongo_operation(mongo_span, 'delete', 'mortgage/pay_mortgage', mortgage_id)
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
    with tracer.start_active_span(f'/mortgage/check_eligibility/getCustomerInfo/{username}') as mortScope:
        response = requests.get(f'{CUSTOMER_INFO_SERVICE_URL}/getCustomerInfo/{username}')

    if response.status_code != 200:
        return False, 0, customer_data.get("account_number").get("account_number")
    
    customer_data = response.json()
    down_payment_ratio = int(down_payment) / int(property_value)

    if down_payment_ratio >= 0.2:
        return True, 0.8 * int(property_value), customer_data.get("account_number")
    else:
        return False, 0, customer_data.get("account_number")

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