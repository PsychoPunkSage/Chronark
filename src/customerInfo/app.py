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
        self.acc_balance = acc_balance
        self.dmat_balance = dmat_balance
        self.account_number = account_number
        self.acc_balance = acc_balance
        self.email = email
        self.contact_no = contact_no
        self.address = address
        self.customer_pic_url = customer_pic_url

# ===================================================================================================================================================================================== #

@app.route("/getCustomerInfo", methods=["GET"])
def getCustomerInfo():
    customer_data = customer_collection.find()
    infos = []
    for info in customer_data:
        info_dict = {key: value for key, value in info.items() if key != '_id'}
        infos.append(info_dict)
    return jsonify(infos)

@app.route("/updateCustomerInfo", methods=["POST"])
def updateCustomerInfo():
    jsondata = request.json
    username = jsondata.get('username')
    existing_user = customer_collection.find_one({"username": username})

    if existing_user:
        customer_collection.update_one({"username": username}, {"$set": jsondata})
    else:
        customer_collection.insert_one(jsondata)
    return "Success", 200

# ===================================================================================================================================================================================== #