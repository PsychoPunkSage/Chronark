import os
from pymongo import MongoClient
from flask import Flask, render_template, request, jsonify

from jaeger_client import Config
from flask_opentracing import FlaskTracing

SELF_PORT = os.environ.get('SELF_PORT')
MONGO_DB_HOST = os.environ.get('MONGO_DB_HOST')
MONGO_DB_PORT = os.environ.get('MONGO_DB_PORT')
MONGO_DB_USERNAME = os.environ.get('MONGO_DB_USERNAME')
MONGO_DB_PASSWORD = os.environ.get('MONGO_DB_PASSWORD')
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
        service_name='ms-cus-info',
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
customer_collection = data.customerInfos

class CustomerInfoTemplate:
    def __init__(
            self, 
            username="", 
            password="", 
            name="", 
            acc_balance="", 
            dmat_balance="", 
            account_number="", 
            email="", 
            contact_no="", 
            address="", 
            customer_pic_url=""
    ):
        self.username = username
        self.password = password
        self.name = name
        self.acc_balance = acc_balance # default = 50000
        self.dmat_balance = dmat_balance # default = 0
        self.account_number = account_number # generated
        self.email = email
        self.contact_no = contact_no
        self.address = address
        self.customer_pic_url = customer_pic_url # No need to add

@app.route('/', methods=['GET'])
@tracing.trace()
def index():
    with tracer.start_active_span('/cus-info/') as scope:
        return render_template(
            'index.html',
            m_client=db_client , 
            MONGO_DB_HOST=MONGO_DB_HOST, 
            MONGO_DB_PORT=MONGO_DB_PORT, 
            MONGO_DB_USERNAME=MONGO_DB_USERNAME, 
            MONGO_DB_PASSWORD=MONGO_DB_PASSWORD
        )

# ===================================================================================================================================================================================== #

@app.route("/getCustomerInfo/<string:username>", methods=["GET"])
@tracing.trace()
def getCustomerInfo(username):
    with tracer.start_active_span(f'/cus-info/getCustomerInfo/{username}') as scope:
        with tracer.start_active_span('mongo_insert') as mongo_span:
            trace_mongo_operation(mongo_span, 'find', '/cus-info/getCustomerInfo', username)
            customer_data = customer_collection.find_one({"username": username}, {"_id": 0})

        if customer_data is None:
            return jsonify({"message": "No customer found"}), 404
        else:
            return jsonify(customer_data)

@app.route("/getCustomerInfos", methods=["GET"])
@tracing.trace()
def getCustomerInfos():
    with tracer.start_active_span('/cus-info/getCustomerInfos') as scope:
        with tracer.start_active_span('mongo_insert') as mongo_span:
            trace_mongo_operation(mongo_span, 'find', '/cus-info/getCustomerInfos', {})
            customer_datas = customer_collection.find()

        datas = []
        for contact in customer_datas:
            contact_dict = {key: value for key, value in contact.items() if key != '_id'}
            datas.append(contact_dict)
        return jsonify(datas)

@app.route("/updateCustomerInfo", methods=["POST", "PUT"])
@tracing.trace()
def updateCustomerInfo():
    with tracer.start_active_span('/cus-info/updateCustomerInfo') as scope:
        jsondata = request.json
        username = jsondata.get('username')

        with tracer.start_active_span('mongo_insert') as mongo_span:
            trace_mongo_operation(mongo_span, 'find', '/cus-info/updateCustomerInfo', username)
            existing_user = customer_collection.find_one({"username": username})

        if request.method == "POST":
            if existing_user:
                # Preserve the existing values for account_balance, dmat_balance, and account_number
                jsondata['account_number'] = existing_user.get('account_number')

                with tracer.start_active_span('mongo_insert') as mongo_span:
                    trace_mongo_operation(mongo_span, 'update', '/cus-info/updateCustomerInfo', jsondata)
                    customer_collection.update_one({"username": username}, {"$set": jsondata})
            else:
                with tracer.start_active_span('mongo_insert') as mongo_span:
                    trace_mongo_operation(mongo_span, 'insert', '/cus-info/updateCustomerInfo', jsondata)
                    customer_collection.insert_one(jsondata)
            return "Success", 200

        if request.method == "PUT":
            if existing_user:
                with tracer.start_active_span('mongo_insert') as mongo_span:
                    trace_mongo_operation(mongo_span, 'update', '/cus-info/updateCustomerInfo', username)
                    customer_collection.update_one({"username": username}, {"$set": jsondata})
            else:
                return jsonify({"message": "No customer found"}), 404
            return "Success", 200

# ===================================================================================================================================================================================== #

@app.route('/clearData', methods=['POST'])
@tracing.trace()
def clearContacts():
    with tracer.start_active_span('/cus-info/clearData') as scope:
        with tracer.start_active_span('mongo_insert') as mongo_span:
            trace_mongo_operation(mongo_span, 'delete', '/cus-info/clearContacts', {})
            customer_collection.delete_many({})
        return "All data cleared from contacts collection", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=SELF_PORT, debug=True)