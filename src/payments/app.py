import os
import requests
from datetime import datetime
from flask import Flask, render_template, request, jsonify

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

@app.route('/', methods=['GET'])
def index():
    return render_template(
        'index.html', 
        self_port=SELF_PORT
    )

# ===================================================================================================================================================================================== #

@app.route('/pay', methods=['POST'])
def pay():
    data = request.json
    receiver_username = data.get("receiver_username")
    username_sender = data.get("username")
    account_number = data.get("account_number")
    comments = data.get("comments")
    receiver = data.get("to")
    amount = data.get("amount")

    resp_receiver = requests.get(f"{CUSTOMER_INFO_SERVICE_URL}/getCustomerInfo/{receiver_username}")
    if resp_receiver.status_code != 200:
        return  jsonify({"status": "error", "message": "No such user exists"}), 404
    
    receiver_data = resp_receiver.json()
    true_name = receiver_data.get("name").lower().strip()
    true_account_number = receiver_data.get("account_number").lower().strip()
    acc_balance_receiver = int(receiver_data.get("acc_balance"))
    if true_name.lower() != receiver.lower().strip() or true_account_number != account_number.lower().strip():
        return jsonify({"status": "error", "message": f"Invalid credentials <br>{receiver.lower().strip()} != {true_name} || {true_account_number} != {account_number.lower().strip()}"}), 400
    
    # Get sender info
    resp_sender = requests.get(f"{CUSTOMER_INFO_SERVICE_URL}/getCustomerInfo/{username_sender}")
    if resp_sender.status_code!= 200:
        return jsonify({"status": "error", "message": "Unexpected error"}), 404
    
    sender_data = resp_sender.json()
    acc_balance_sender = int(sender_data.get("acc_balance"))
    sender_account_number = sender_data.get("account_number")

    # Money transfer - checks
    if int(amount) > acc_balance_sender:
        return jsonify({"status": "error", "message": "Insufficient funds"}), 400

    # Update sender's and receiver's account balances
    updated_acc_balance_sender = acc_balance_sender - int(amount)
    updated_acc_balance_receiver = acc_balance_receiver + int(amount)

    resp_sender_update = requests.put(f"{CUSTOMER_INFO_SERVICE_URL}/updateCustomerInfo", json={"username": username_sender, "acc_balance": updated_acc_balance_sender})
    if resp_sender_update.status_code!= 200:
        return jsonify({"status": "error", "message": "Unexpected error"}), 404
    
    resp_receiver_update = requests.put(f"{CUSTOMER_INFO_SERVICE_URL}/updateCustomerInfo", json={"username": receiver_username, "acc_balance": updated_acc_balance_receiver})
    if resp_sender_update.status_code!= 200:
        return jsonify({"status": "error", "message": "Unexpected error"}), 404
    
    # Send the Txn details to <Customer Activity>
    activity_data = {
        "username": username_sender,
        "to": account_number,
        "from": sender_account_number,
        "timestamp": datetime.now().isoformat(),
        "transaction_type": f"Money Transfer - {receiver}",
        "transaction_amount": amount,
        "comments": f"{comments}"
    }

    response = requests.post(f'{CUSTOMER_ACTIVITY_SERVICE_URL}/updateCustomerActivity', json=activity_data)
    if response.status_code != 200:
        return f'Failed to Update Activity  <br>Status Code: {response.status_code} <br>Error: {response.json()}'

    return jsonify({"status": "success", "message": "Payment successful"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=SELF_PORT, debug=True)