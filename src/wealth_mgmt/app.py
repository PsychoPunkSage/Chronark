import os
import hashlib
import requests
from pymongo import MongoClient
from flask import Flask, request, jsonify

from jaeger_client import Config
from flask_opentracing import FlaskTracing

SELF_PORT = os.environ.get('SELF_PORT')
MONGO_DB_HOST = os.environ.get('MONGO_DB_HOST')
MONGO_DB_PORT = os.environ.get('MONGO_DB_PORT')
MONGO_DB_USERNAME = os.environ.get('MONGO_DB_USERNAME')
MONGO_DB_PASSWORD = os.environ.get('MONGO_DB_PASSWORD')
# Customer Info Service
CUSTOMER_INFO_SERVICE_HOST = os.environ.get('CUSTOMER_INFO_SERVICE_HOST')
CUSTOMER_INFO_SERVICE_PORT = os.environ.get('CUSTOMER_INFO_SERVICE_PORT')
CUSTOMER_INFO_SERVICE_URL = f'http://{CUSTOMER_INFO_SERVICE_HOST}:{CUSTOMER_INFO_SERVICE_PORT}'
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
        service_name='ms-frontend',
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
data = db_client.wealth_mgmt
wealth_mgmt_activity = data.activity

class WealthManagementTemplate:
    def __init__(
            self, 
            transaction_id="",
            username="",
            from_acc="", # acc_number
            to_acc="", # acc_number
            timestamp="",
            transaction_type="", 
            transaction_amount="",
            tax_amount="",
            total_amount="",
            comments="",
            ):
        self.transaction_id = transaction_id
        self.username = username
        self.from_acc = from_acc
        self.to_acc = to_acc
        self.timestamp = timestamp
        self.transaction_type = transaction_type
        self.transaction_amount = transaction_amount
        self.tax_amount = tax_amount
        self.total_amount = total_amount
        self.comments = comments

# ========================================================================================================================= #

def calculate_tax(amount):
    """
    Tax slabs:
    - < 1000: No tax
    - 1000 - 5000: 5%
    - 5001 - 10000: 10%
    - 10000 - 20000: 15%
    - 20000 - 50000: 30%
    - > 50000: 50%
    """
    if amount < 1000:
        return 0, 0
    elif amount <= 5000:
        return amount * 0.05, 5
    elif amount <= 10000:
        return amount * 0.10, 10
    elif amount <= 20000:
        return amount * 0.15, 15
    elif amount <= 50000:
        return amount * 0.30, 30
    else:
        return amount * 0.50, 50

# ========================================================================================================================= #

@app.route("/configureTaxSlab", methods=["POST"])
@tracing.trace()
def configureTaxSlab():
    with tracer.start_active_span('/wealth-mgmt/configureTaxSlab') as scope:
        # Get the Amount being Transacted
        data = request.json
        amount = int(data.get('amount'))
        txn_id = data.get('txn_id')
        txn_type = data.get('txn_type')
        username = data.get('username')

        # Configure the Tax Slab and Tax
        if amount <= 0:
            return jsonify({"message": "Invalid amount"}), 400
        tax, taxSlab = calculate_tax(amount)

        data["tax"] = tax
        data["taxSlab"] = taxSlab

        tax_id = get_tax_id(amount, txn_id, txn_type, username, tax, taxSlab)
        data["tax_id"] = tax_id

        # Push/Update the Data in DB.... (Mongo)
        with tracer.start_active_span('mongo_update') as mongo_span:
            trace_mongo_operation(mongo_span, 'update', 'wealth-mgmt/configureTaxSlab', data)
            wealth_mgmt_activity.insert_one(data)

        return jsonify({"message": "Tax Slab Configured Successfully"}), 200
    
# ========================================================================================================================= #

@app.route("/getTaxes/<username>", methods=["GET"])
@tracing.trace()
def getTaxes(username):
    with tracer.start_active_span('/wealth-mgmt/getTaxes/<uname>') as scope:
        """
        Fetch all transactions for a specific username.
        """

        with tracer.start_active_span('mongo_find') as mongo_span:
            trace_mongo_operation(mongo_span, 'find', 'wealth-mgmt/gettaxes', username)
            transactions = wealth_mgmt_activity.find({"username": username})

        transactions_list = []
        total_tax = 0

        for txn in transactions:
            if int(txn.get('tax', 0)) > 0:  # Only include transactions with non-zero tax
                txn_dict = {key: value for key, value in txn.items() if key != '_id'}
                transactions_list.append(txn_dict)
                total_tax += int(txn_dict.get('tax', 0))

        # If no valid transactions found, return a message
        if not transactions_list:
            return jsonify({"message": "No transactions with non-zero tax found for this username"}), 404

        # Return the filtered list of transactions and total tax amount
        return jsonify({"transactions": transactions_list, "total_tax": total_tax}), 200

# ========================================================================================================================= #

@app.route("/payTaxes", methods=["POST"])
@tracing.trace()
def pay_taxes():
    with tracer.start_active_span('/wealth-mgmt/payTaxes') as scope:
        """
        Pay the taxes for a specific transaction and remove it from the database.
        """
        data = request.json
        tax_id = data.get('tax_id')
        username = data.get('username')

        with tracer.start_active_span(f'/wealth-mgmt/payTaxes/getCustomerInfo/{username}') as wmScope:
            resp = response = requests.get(f'{CUSTOMER_INFO_SERVICE_URL}/getCustomerInfo/{username}')

        if resp.status_code != 200:
            print("Username: {username}".format(username=username))
            return  jsonify({"status": "error", "message": f"Unexpected- {username}"}), 404
        customer_data = response.json()
        acc_balance = int(customer_data.get('acc_balance'))

        # Fetch the transaction by txn_id
        with tracer.start_active_span('mongo_find') as mongo_span:
            trace_mongo_operation(mongo_span, 'find', 'wealth-mgmt/gettaxes', tax_id)
            transaction = wealth_mgmt_activity.find_one({"tax_id": tax_id})

        if not transaction:
            return jsonify({"message": "Transaction not found"}), 404

        # Check if the tax amount exists and is valid
        tax_amount = int(transaction.get('tax'))

        if not tax_amount or tax_amount == 0:
            return jsonify({"message": "No tax to be paid for this transaction"}), 400

        # Check if the customer has sufficient balance to cover the tax
        if acc_balance < tax_amount:
            return jsonify({"message": "Insufficient balance to cover the tax"}), 400

        # Update the customer's account balance
        new_acc_balance = acc_balance - tax_amount

        with tracer.start_active_span(f'/wealth-mgmt/payTaxes/updateCustomerInfo') as wmScope:
            response = requests.put(f'{CUSTOMER_INFO_SERVICE_URL}/updateCustomerInfo', json={"username": username, "acc_balance": new_acc_balance})

        if response.status_code!= 200:
            return jsonify({"status": "error", "message": "Unexpected"}), 555

        # Delete the transaction from the database
        with tracer.start_active_span('mongo_delete') as mongo_span:
            trace_mongo_operation(mongo_span, 'delete', 'wealth-mgmt/payTaxes', tax_id)
            wealth_mgmt_activity.delete_one({"tax_id": tax_id})

        return jsonify({"message": f"Tax of {tax_amount} paid successfully."}), 200

# ========================================================================================================================= #

def get_tax_id(amount, txn_id, txn_type, username, tax, taxSlab):
    unique_string = f"{username}_{amount}_{txn_id}_{txn_type}_{tax}_{taxSlab}"
    hash_object = hashlib.sha256(unique_string.encode())
    hex_dig = hash_object.hexdigest()
    digits = ''.join(filter(str.isdigit, hex_dig))
    tax_id = '0xTAX' + digits[:17]
    tax_id = tax_id.ljust(22, '0')
    return tax_id

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=SELF_PORT, debug=True)
