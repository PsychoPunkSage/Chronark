import os
import hashlib
from pymongo import MongoClient
from flask import Flask, render_template, request, jsonify
import requests

from jaeger_client import Config
from flask_opentracing import FlaskTracing

SELF_PORT = os.environ.get('SELF_PORT')
MONGO_DB_HOST = os.environ.get('MONGO_DB_HOST')
MONGO_DB_PORT = os.environ.get('MONGO_DB_PORT')
MONGO_DB_USERNAME = os.environ.get('MONGO_DB_USERNAME')
MONGO_DB_PASSWORD = os.environ.get('MONGO_DB_PASSWORD')
# Wealth Management Service
WEALTH_MGMT_HOST = os.environ.get('WEALTH_MGMT_HOST')
WEALTH_MGMT_PORT = os.environ.get('WEALTH_MGMT_PORT')
WEALTH_MGMT_URL = f'http://{WEALTH_MGMT_HOST}:{WEALTH_MGMT_PORT}'
# Jaegar integration
JAEGER_AGENT_HOST = os.environ.get('JAEGER_AGENT_HOST')
JAEGER_AGENT_PORT = os.environ.get('JAEGER_AGENT_PORT')
JAEGER_SERVICE_URL = 'http://' + JAEGER_AGENT_HOST + ':' + JAEGER_AGENT_PORT

app = Flask(__name__)

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
        service_name='ms-cus-activity',
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
# Database init
data = db_client.info

# Collection init
customer_activity = data.activity

class CustomerActivityTemplate:
    def __init__(
            self, 
            transaction_id="",
            username="",
            form="", # acc_number
            to="", # acc_number
            timestamp="",
            transaction_type="", 
            transaction_amount="",
            comments="",
            ):
        self.transaction_id = transaction_id
        self.username = username
        self.form = form
        self.to = to
        self.timestamp = timestamp  # datetime.now()
        self.transaction_type = transaction_type
        self.transaction_amount = transaction_amount
        self.comments = comments

@app.route('/', methods=['GET'])
@tracing.trace()
def index():
    with tracer.start_active_span('/cus-act/') as scope:
        return render_template(
            'index.html',
            m_client=db_client , 
            MONGO_DB_HOST=MONGO_DB_HOST, 
            MONGO_DB_PORT=MONGO_DB_PORT, 
            MONGO_DB_USERNAME=MONGO_DB_USERNAME, 
            MONGO_DB_PASSWORD=MONGO_DB_PASSWORD
        )

# ===================================================================================================================================================================================== #

@app.route("/getCustomerActivity/<string:account_number>", methods=["GET"])
@tracing.trace()
def getCustomerActivity(account_number):
    with tracer.start_active_span(f'/cus-act/getCustomerActivity/{account_number}') as scope:
        customer_activity_data = list(customer_activity.find(
            {"$or": [{"from": account_number}, {"to": account_number}]}, 
            {"_id": 0}
        ))
        print("CAD::>", customer_activity_data)
        return jsonify(customer_activity_data)

@app.route("/getAllCustomerActivities", methods=["GET"])
@tracing.trace()
def getAllCustomerActivities():
    with tracer.start_active_span('/cus-act/getAllCustomerActivities') as scope:
        with tracer.start_active_span('mongo_insert') as mongo_span:
            trace_mongo_operation(mongo_span, 'find', '/cus-act/getAllCustomerActivities', {})
            customer_datas = customer_activity.find()
        datas = []
        for contact in customer_datas:
            contact_dict = {key: value for key, value in contact.items() if key != '_id'}
            datas.append(contact_dict)
        return jsonify(datas)

@app.route("/updateCustomerActivity", methods=["POST", "PUT"])
@tracing.trace()
def updateCustomerActivity():
    with tracer.start_active_span('/cus-act/updateCustomerActivity') as scope:
        jsondata = request.json
        username = jsondata.get('username')
        froms = jsondata.get('from')
        to = jsondata.get('to')
        timestamp = jsondata.get('timestamp')
        transaction_type = jsondata.get('transaction_type')
        transaction_amount = jsondata.get('transaction_amount')
        comments = jsondata.get('comments')
        
        transaction_id = get_txn_id(username, froms, to, timestamp, transaction_type, transaction_amount, comments)
        jsondata['transaction_id'] = transaction_id
    
        if request.method == "POST":
            
            with tracer.start_active_span('mongo_insert') as mongo_span:
                trace_mongo_operation(mongo_span, 'insert', '/cus-act/updateCustomerActivities', jsondata)
                customer_activity.insert_one(jsondata)
        
            wealth_mgmt_data = {
                "amount": transaction_amount,
                "txn_id": transaction_id,
                "txn_type": transaction_type,
                "username": username,
            }

            with tracer.start_active_span('/cus-act/updateCustomerActivities/configureTaxSlab') as cusActScope:
                response = requests.post(f'{WEALTH_MGMT_URL}/configureTaxSlab', json=wealth_mgmt_data)
            if response.status_code != 200:
                return f'Failed to Update TAX Data  <br>Status Code: {response.status_code} <br>Error: {response.json()}'
            
            return "Success", 200
        
        if request.method == "PUT":
            existing_tx = customer_activity.find_one({"transaction_id": transaction_id})
            if existing_tx:
                with tracer.start_active_span('mongo_insert') as mongo_span:
                    trace_mongo_operation(mongo_span, 'update', '/cus-act/updateCustomerActivities', jsondata)
                    customer_activity.update_one({"transaction_id": transaction_id}, {"$set": jsondata})
            else:
                with tracer.start_active_span('mongo_insert') as mongo_span:
                    trace_mongo_operation(mongo_span, 'insert', '/cus-act/updateCustomerActivities', jsondata)
                    customer_activity.insert_one(jsondata)
            return "Success", 200
    
# =====================================================================================================================================================================================

@app.route('/clearData', methods=['POST'])
@tracing.trace()
def clearContacts():
    with tracer.start_active_span('/cus-act/clearData') as scope:
        with tracer.start_active_span('mongo_insert') as mongo_span:
            trace_mongo_operation(mongo_span, 'delete', '/cus-act/clearContacts', {})
            customer_activity.delete_many({})
        return "All data cleared from contacts collection", 200

# =====================================================================================================================================================================================

def get_txn_id(username, froms, to, timestamp, transaction_type, transaction_amount, comments):
    unique_string = f"{username}_{froms}_{to}_{timestamp}_{transaction_type}_{transaction_amount}_{comments}"
    hash_object = hashlib.sha256(unique_string.encode())
    hex_dig = hash_object.hexdigest()
    digits = ''.join(filter(str.isdigit, hex_dig))
    tx_id = '0x' + digits[:20]
    tx_id = tx_id.ljust(22, '0')

    return tx_id

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=SELF_PORT, debug=True)