from datetime import datetime
import os
import requests
from flask import Flask, request, jsonify

from jaeger_client import Config
from flask_opentracing import FlaskTracing

app = Flask(__name__)

SELF_PORT = os.environ.get('SELF_PORT')
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
        service_name='ms-deposit-acc',
    )
    return config.initialize_tracer()

tracer = init_tracer()
tracing = FlaskTracing(tracer, True, app)

# ===================================================================================================================================================================================== #

@app.route('/getBalance/<username>', methods=['GET'])
@tracing.trace()
def get_balance(username):
    with tracer.start_active_span('/deposit-acc/getBalance/<uname>') as scope:
        resp = response = requests.get(f'{CUSTOMER_INFO_SERVICE_URL}/getCustomerInfo/{username}')
        if resp.status_code != 200:
            return  jsonify({"status": "error", "message": "User DNE"}), 404

        customer_data = response.json()
        acc_balance = customer_data.get('acc_balance')

        return jsonify({"status": "success", "balance": acc_balance}), 200

@app.route('/deposit', methods=['POST'])
@tracing.trace()
def deposit():
    with tracer.start_active_span('/deposit-acc/deposit') as scope:
        data = request.json
        amount = data.get('amount')
        username = data.get('username')

        resp = response = requests.get(f'{CUSTOMER_INFO_SERVICE_URL}/getCustomerInfo/{username}')
        if resp.status_code != 200:
            return  jsonify({"status": "error", "message": "Account Not found"}), 404

        customer_data = response.json()
        acc_balance = customer_data.get('acc_balance')
        account_number = customer_data.get('account_number')

        new_balance = int(acc_balance) + int(amount)
        response = requests.put(f'{CUSTOMER_INFO_SERVICE_URL}/updateCustomerInfo', json={"username": username, "acc_balance": new_balance})
        if response.status_code!= 200:
            return jsonify({"status": "error", "message": "Can't update the balance"}), 404

        # Send the Txn details to <Customer Activity>
        activity_data = {
            "username": username,
            "to": account_number,
            "from": "External",
            "timestamp": datetime.now().isoformat(),
            "transaction_type": "Deposit",
            "transaction_amount": amount,
            "comments": "Money Deposited: Self"
        }

        response = requests.post(f'{CUSTOMER_ACTIVITY_SERVICE_URL}/updateCustomerActivity', json=activity_data)
        if response.status_code != 200:
            return f'Failed to Update Activity  <br>Status Code: {response.status_code} <br>Error: {response.json()}'

        return jsonify({"status": "success", "message": "Deposit successful", "new_balance": new_balance}), 200

@app.route('/withdraw', methods=['POST'])
@tracing.trace()
def withdraw():
    with tracer.start_active_span('/deposit-acc/withdraw') as scope:
        data = request.json
        amount = data.get('amount')
        username = data.get('username')

        resp = response = requests.get(f'{CUSTOMER_INFO_SERVICE_URL}/getCustomerInfo/{username}')
        if resp.status_code != 200:
            return  jsonify({"status": "error", "message": "Account Not found"}), 404

        customer_data = response.json()
        acc_balance = customer_data.get('acc_balance')
        account_number = customer_data.get('account_number')

        if int(acc_balance) < int(amount):
            return jsonify({"status": "error", "message": "Insufficient funds"}), 400

        new_balance = int(acc_balance) - int(amount)
        response = requests.put(f'{CUSTOMER_INFO_SERVICE_URL}/updateCustomerInfo', json={"username": username, "acc_balance": new_balance})
        if response.status_code!= 200:
            return jsonify({"status": "error", "message": "Can't update the balance"}), 404

        # Send the Txn details to <Customer Activity>
        activity_data = {
            "username": username,
            "from": account_number,
            "to": "External",
            "timestamp": datetime.now().isoformat(),
            "transaction_type": "Withdrawl",
            "transaction_amount": amount,
            "comments": "Money Withdrawl: Self"
        }

        response = requests.post(f'{CUSTOMER_ACTIVITY_SERVICE_URL}/updateCustomerActivity', json=activity_data)
        if response.status_code != 200:
            return f'Failed to Update Activity  <br>Status Code: {response.status_code} <br>Error: {response.json()}'


        return jsonify({"status": "success", "message": "Withdrawal successful", "new_balance": new_balance}), 200

# ===================================================================================================================================================================================== #

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=SELF_PORT, debug=True)
