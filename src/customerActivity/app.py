import os
from pymongo import MongoClient
from flask import Flask, render_template, request, jsonify

SELF_PORT = os.environ.get('SELF_PORT')
MONGO_DB_HOST = os.environ.get('MONGO_DB_HOST')
MONGO_DB_PORT = os.environ.get('MONGO_DB_PORT')
MONGO_DB_USERNAME = os.environ.get('MONGO_DB_USERNAME')
MONGO_DB_PASSWORD = os.environ.get('MONGO_DB_PASSWORD')

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
            transaction_type="", 
            transaction_amount="",
            comments="",
            ):
        self.transaction_id = transaction_id
        self.username = username
        self.form = form
        self.to = to
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

@app.route("/getCustomerInfo/<string:account_number>", methods=["GET"])
def getCustomerInfo(account_number):
    customer_activity_data = list(customer_activity.find(
        {"$or": [{"From": account_number}, {"To": account_number}]}, 
        {"_id": 0}
    ))
    
    return jsonify(customer_activity_data)

@app.route("/getAllCustomerActivities", methods=["GET"])
def getCustomerInfos():
    customer_datas = customer_activity.find()
    datas = []
    for contact in customer_datas:
        contact_dict = {key: value for key, value in contact.items() if key != '_id'}
        datas.append(contact_dict)
    return jsonify(datas)

@app.route("/updateCustomerActivity", methods=["POST", "PUT"])
def updateCustomerActivity():
    jsondata = request.json
    transaction_id = jsondata.get('transaction_id')
    existing_tx = customer_activity.find_one({"transaction_id": transaction_id})

    if request.method == "POST":
        if existing_tx:
            return "Unexpected behaviour: Txn already exist", 404
        else:
            customer_activity.insert_one(jsondata)
        return "Success", 200
    
    if request.method == "PUT":
        if existing_tx:
            customer_activity.update_one({"transaction_id": transaction_id}, {"$set": jsondata})
        else:
            return jsonify({"message": "No such txn found"}), 404
        return "Success", 200
    
# =====================================================================================================================================================================================

@app.route('/clearData', methods=['POST'])
def clearContacts():
    customer_activity.delete_many({})
    return "All data cleared from contacts collection", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=SELF_PORT, debug=True)