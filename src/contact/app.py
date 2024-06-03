import os
from pymongo import MongoClient
from flask import Flask, render_template, request, jsonify

'''
id:
name:
employee: (yes/no)
customer: (yes/no)
email:
mobile number:
address:
'''
# SELF_PORT = 5003
# MONGO_DB_HOST = "localhost"
# MONGO_DB_PORT = "27017"
# MONGO_DB_USERNAME = "mongocontact"
# MONGO_DB_PASSWORD = "contact"
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

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html', m_client=db_client, MONGO_HOST=MONGO_DB_HOST, MONGO_PORT=MONGO_DB_PORT, MONGO_PASSWORD=MONGO_DB_PASSWORD, MONGO_USERNAME=MONGO_DB_USERNAME)


# connecting to db
@app.route('/client', methods=['POST'])
def add_client():
    client_data = request.json
    status = storage.insert_one(client_data)
    return jsonify({"status": str(status.inserted_id)}), 201

@app.route('/client/<client_id>', methods=['GET'])
def get_client(client_id):
    client = storage.find_one({"id": client_id})
    if client:
        return jsonify(client), 200
    else:
        return jsonify({"error": "Client not found"}), 404

@app.route('/clients', methods=['GET'])
def get_all_clients():
    client_data = storage.find()
    clients = []
    for client in client_data:
        client['_id'] = str(client['_id'])  # Convert ObjectId to string
        clients.append(client)
    return jsonify(clients), 200

@app.route('/client/<client_id>', methods=['PUT'])
def update_client(client_id):
    updated_data = request.json
    result = storage.update_one({"id": client_id}, {"set": updated_data})
    if result.matched_count:
        return jsonify({"status": "Client updated"}), 200
    else:
        return jsonify({"error": "Client not found"}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=SELF_PORT, debug=True)