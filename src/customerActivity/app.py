import os
import hashlib
from pymongo import MongoClient
from flask import Flask, render_template, request, jsonify
import requests

SELF_PORT = os.environ.get('SELF_PORT')
MONGO_DB_HOST = os.environ.get('MONGO_DB_HOST')
MONGO_DB_PORT = os.environ.get('MONGO_DB_PORT')
MONGO_DB_USERNAME = os.environ.get('MONGO_DB_USERNAME')
MONGO_DB_PASSWORD = os.environ.get('MONGO_DB_PASSWORD')
# Wealth Management Service
WEALTH_MGMT_HOST = os.environ.get('WEALTH_MGMT_HOST')
WEALTH_MGMT_PORT = os.environ.get('WEALTH_MGMT_PORT')
WEALTH_MGMT_URL = f'http://{WEALTH_MGMT_HOST}:{WEALTH_MGMT_PORT}'

app = Flask(__name__)

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
def index():
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
def getCustomerActivity(account_number):
    customer_activity_data = list(customer_activity.find(
        {"$or": [{"from": account_number}, {"to": account_number}]}, 
        {"_id": 0}
    ))
    print("CAD::>", customer_activity_data)
    return jsonify(customer_activity_data)

@app.route("/getAllCustomerActivities", methods=["GET"])
def getAllCustomerActivities():
    customer_datas = customer_activity.find()
    datas = []
    for contact in customer_datas:
        contact_dict = {key: value for key, value in contact.items() if key != '_id'}
        datas.append(contact_dict)
    print("CAD(all)::>", data)
    return jsonify(datas)

@app.route("/updateCustomerActivity", methods=["POST", "PUT"])
def updateCustomerActivity():
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
        customer_activity.insert_one(jsondata)
    
        wealth_mgmt_data = {
            "amount": transaction_amount,
            "txn_id": transaction_id,
            "txn_type": transaction_type,
            "username": username,
        }

        response = requests.post(f'{WEALTH_MGMT_URL}/configureTaxSlab', json=wealth_mgmt_data)
        if response.status_code != 200:
            return f'Failed to Update TAX Data  <br>Status Code: {response.status_code} <br>Error: {response.json()}'
        
        return "Success", 200
    
    if request.method == "PUT":
        existing_tx = customer_activity.find_one({"transaction_id": transaction_id})
        if existing_tx:
            customer_activity.update_one({"transaction_id": transaction_id}, {"$set": jsondata})
        else:
            customer_activity.insert_one(jsondata)
        return "Success", 200
    
# =====================================================================================================================================================================================

@app.route('/clearData', methods=['POST'])
def clearContacts():
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