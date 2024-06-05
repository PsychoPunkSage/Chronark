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
print("db_client::> ", db_client)
data = db_client.contact
storage = data.storage

class Client:
    def __init__(self, id="", name="", employee="", customer="", email="", mobile="", address="") -> None:
        self.id = id
        self.name = name
        self.employee = employee
        self.customer = customer
        self.email = email
        self.mobile = mobile
        self.address = address

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html', m_client=db_client, MONGO_HOST=MONGO_DB_HOST, MONGO_PORT=MONGO_DB_PORT, MONGO_PASSWORD=MONGO_DB_PASSWORD, MONGO_USERNAME=MONGO_DB_USERNAME)

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
    client = Client(**jsonData)
    storage.update_one({"id": client.id}, {"$set": client.__dict__}, upsert=True)
    return "Success", 200

@app.route('/updateClients', methods=['POST'])
def updateClients():
    jsonData = request.json
    for client_data in jsonData:
        client = Client(**client_data)
        storage.update_one({"id": client.id}, {"$set": client.__dict__}, upsert=True)
    return "Success", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=SELF_PORT, debug=True)