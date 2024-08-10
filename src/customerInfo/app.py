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
        self.acc_balance = acc_balance # default = 5000
        self.dmat_balance = dmat_balance # default = 0
        self.account_number = account_number # generated
        self.email = email
        self.contact_no = contact_no
        self.address = address
        self.customer_pic_url = customer_pic_url # No need to add

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

@app.route("/getCustomerInfo/<string:username>", methods=["GET"])
def getCustomerInfo(username):
    customer_data = customer_collection.find_one({"username": username}, {"_id": 0})
    if customer_data is None:
        return jsonify({"message": "No customer found"}), 404
    else:
        return jsonify(customer_data)

@app.route("/getCustomerInfos", methods=["GET"])
def getCustomerInfos():
    customer_datas = customer_collection.find()
    datas = []
    for contact in customer_datas:
        contact_dict = {key: value for key, value in contact.items() if key != '_id'}
        datas.append(contact_dict)
    return jsonify(datas)

@app.route("/updateCustomerInfo", methods=["POST"])
def updateCustomerInfo():
    jsondata = request.json
    username = jsondata.get('username')
    existing_user = customer_collection.find_one({"username": username})

    if existing_user:
        # Preserve the existing values for account_balance, dmat_balance, and account_number
        jsondata['acc_balance'] = existing_user.get('acc_balance')
        jsondata['dmat_balance'] = existing_user.get('dmat_balance')
        jsondata['account_number'] = existing_user.get('account_number')

        customer_collection.update_one({"username": username}, {"$set": jsondata})
    else:
        customer_collection.insert_one(jsondata)
    return "Success", 200

# ===================================================================================================================================================================================== #

@app.route('/clearData', methods=['POST'])
def clearContacts():
    customer_collection.delete_many({})
    return "All data cleared from contacts collection", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=SELF_PORT, debug=True)