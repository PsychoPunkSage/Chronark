import json
import os
from pymongo import MongoClient
from flask import Flask, render_template, request, jsonify

'''
id:
name:
employee: (yes/no)
customer: (yes/no)
email:
mobile:
address:
'''
SELF_PORT = os.environ.get('SELF_PORT')
MONGO_DB_HOST = os.environ.get('MONGO_DB_HOST')
MONGO_DB_PORT = os.environ.get('MONGO_DB_PORT')
MONGO_DB_USERNAME = os.environ.get('MONGO_DB_USERNAME')
MONGO_DB_PASSWORD = os.environ.get('MONGO_DB_PASSWORD')


app = Flask(__name__)

# Database connection
db_client = MongoClient(username=MONGO_DB_USERNAME, password=MONGO_DB_PASSWORD, host=MONGO_DB_HOST, port=int(MONGO_DB_PORT))
# User data
data = db_client.contact
storage = data.storage

# Contact No.
contacts_collection = data.contacts

# FAQ
faqs_collection = data.faq

# Conversation
conv_collection = data.conversation


class Client:
    def __init__(self, id="", name="", employee="", customer="", email="", mobile="", address="") -> None:
        self.id = id
        self.name = name
        self.employee = employee
        self.customer = customer
        self.email = email
        self.mobile = mobile
        self.address = address

class ContactNumber:
    def __init__(self, region_id="", number="", region="", email=""):
        self.region_id = region_id
        self.number = number
        self.region = region
        self.email = email

class Faq:
    def __init__(self, question_id="", category="", question="", answer=""):
        self.question_id = question_id
        self.category = category
        self.question = question
        self.answer = answer

class Conversation:
    def __init__(self, conversation_id="", name="", email="", message="", date="", time=""):
        self.conversation_id = conversation_id
        self.name = name
        self.email = email
        self.question = message
        self.date = date
        self.time = time

# ===================================================================================================================================================================================== #

@app.route('/', methods=['GET'])
def index():
    conv_data = getConvs().response
    return render_template('index.html', conv_data=conv_data, m_client=db_client, MONGO_HOST=MONGO_DB_HOST, MONGO_PORT=MONGO_DB_PORT, MONGO_PASSWORD=MONGO_DB_PASSWORD, MONGO_USERNAME=MONGO_DB_USERNAME)

# ===================================================================================================================================================================================== #

@app.route('/getContacts', methods=['GET'])
def getContacts():
    contact_data = contacts_collection.find()
    contacts = []
    for contact in contact_data:
        contact_dict = {key: value for key, value in contact.items() if key != '_id'}
        contacts.append(contact_dict)
    return jsonify(contacts)

@app.route('/updateContacts', methods=['POST'])
def updateContacts():
    jsonData = request.json
    region_id = jsonData.get('region_id')
    existing_contact = contacts_collection.find_one({"region_id": region_id})

    if existing_contact:
        contacts_collection.update_one({"region_id": region_id}, {"$set": jsonData})
    else:
        contacts_collection.insert_one(jsonData)
    return "Success", 200

# ===================================================================================================================================================================================== #

@app.route('/getFaqs', methods=['GET'])
def getFaqs():
    faq_data = faqs_collection.find()
    faqs = []
    for faq in faq_data:
        faq_dict = {key: value for key, value in faq.items() if key != '_id'}
        faqs.append(faq_dict)
    return jsonify(faqs)

@app.route('/updateFaqs', methods=['POST'])
def updateFaqs():
    jsonData = request.json
    question_id = jsonData.get('question_id')
    existing_faq = faqs_collection.find_one({"question_id": question_id})

    if existing_faq:
        faqs_collection.update_one({"question_id": question_id}, {"$set": jsonData})
    else:
        faqs_collection.insert_one(jsonData)
    return "Success", 200

# ===================================================================================================================================================================================== #

@app.route('/getConvs', methods=['GET'])
def getConvs():
    conv_data = conv_collection.find()
    convs = []
    for conv in conv_data:
        conv_dict = {key: value for key, value in conv.items() if key != '_id'}
        convs.append(conv_dict)
    return jsonify(convs)

@app.route('/updateConvs', methods=['POST'])
def updateConvs():
    jsonData = request.json
    conv_collection.insert_one(jsonData)
    return "Success", 200

# ===================================================================================================================================================================================== #

@app.route('/clearContacts', methods=['POST'])
def clearContacts():
    contacts_collection.delete_many({})
    return "All data cleared from contacts collection", 200

# ===================================================================================================================================================================================== #

@app.route('/getClients', methods=['GET'])
def getClients():
    client_data = storage.find()
    clients = []
    for client in client_data:
        client_dict = {key: value for key, value in client.items() if key != '_id'}
        clients.append(client_dict)
    return jsonify(clients)


@app.route('/getClient/<string:id>', methods=['GET'])
def getClient(id):
    client = storage.find_one({"id": id})
    if client is None:
        return {}, 404
    else:
        return client

@app.route('/updateClient', methods=['POST'])
def updateClient():
    jsonData = request.json
    client_id = jsonData.get('region_id')
    existing_contact = contacts_collection.find_one({"id": client_id})

    if existing_contact:
        storage.update_one({"id": client_id}, {"$set": jsonData})
    else:
        storage.insert_one(jsonData)
    return "Success", 200

# ===================================================================================================================================================================================== #

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=SELF_PORT, debug=True)