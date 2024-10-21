import os
import jwt
import redis
import hashlib
import datetime
import requests

from flask import Flask, render_template, request, jsonify
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from helper import redis_command

from jaeger_client import Config
from flask_opentracing import FlaskTracing

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your_super_complex_secret_key_here')

SELF_PORT = os.environ.get('SELF_PORT')
AUTH_REDIS_HOST = os.environ.get('REDIS_HOST')
AUTH_REDIS_PORT = os.environ.get('REDIS_PORT')
AUTH_REDIS_PASSWORD = os.environ.get('REDIS_PASSWORD')
AUTH_MONGO_DB_HOST = os.environ.get('MONGO_DB_HOST')
AUTH_MONGO_DB_PORT = os.environ.get('MONGO_DB_PORT')
AUTH_MONGO_DB_USERNAME = os.environ.get('MONGO_DB_USERNAME')
AUTH_MONGO_DB_PASSWORD = os.environ.get('MONGO_DB_PASSWORD')
# Customer Info Service
CUSTOMER_INFO_SERVICE_HOST = os.environ.get('CUSTOMER_INFO_SERVICE_HOST')
CUSTOMER_INFO_SERVICE_PORT = os.environ.get('CUSTOMER_INFO_SERVICE_PORT')
CUSTOMER_INFO_SERVICE_URL = f'http://{CUSTOMER_INFO_SERVICE_HOST}:{CUSTOMER_INFO_SERVICE_PORT}'
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
        service_name='ms-authentication',
    )
    return config.initialize_tracer()

tracer = init_tracer()
tracing = FlaskTracing(tracer, True, app)

# ================================================================================================ #

redis_client = redis.Redis(host=AUTH_REDIS_HOST, port=AUTH_REDIS_PORT, password=AUTH_REDIS_PASSWORD)

mongo_client = MongoClient(
    username=AUTH_MONGO_DB_USERNAME, 
    password=AUTH_MONGO_DB_PASSWORD, 
    host=AUTH_MONGO_DB_HOST, 
    port=int(AUTH_MONGO_DB_PORT)
)

db = mongo_client.auth_db
users_collection = db.users

class Users:
    def __init__(self, username="", password="") -> None:
        self.username = username
        self.password = password

test_user = {"username": "test_user", "password": "test_password"}
insert_result = users_collection.insert_one(test_user)
print(f"Inserted document ID: {insert_result.inserted_id}")
fetched_user = users_collection.find_one({"username": "test_user"})
print(f"Fetched document: {fetched_user}")
delete_result = users_collection.delete_one({"username": "test_user"})
print(f"Deleted document count: {delete_result.deleted_count}")

def token_required(f):
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token is missing'}), 403

        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            if redis_command(redis_client.get, token):
                return jsonify({'message': 'Token is blacklisted'}), 403
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired'}), 403
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Token is invalid'}), 403

        return f(*args, **kwargs)
    return decorated_function

@app.route('/', methods=['GET'])
@tracing.trace()
def index():
    with tracer.start_active_span('/auth/') as scope:
        return render_template(
            'index.html',
            r_client=redis_client,
            AUTH_REDIS_HOST=AUTH_REDIS_HOST,
            AUTH_REDIS_PORT=AUTH_REDIS_PORT,
            AUTH_REDIS_PASSWORD=AUTH_REDIS_PASSWORD,
            m_client=mongo_client,
            MONGO_DB_HOST=AUTH_MONGO_DB_HOST,
            MONGO_DB_PORT=AUTH_MONGO_DB_PORT,
            MONGO_DB_USERNAME=AUTH_MONGO_DB_USERNAME,
            MONGO_DB_PASSWORD=AUTH_MONGO_DB_PASSWORD
        )

@app.route('/register', methods=['POST'])
@tracing.trace()
def register():
    with tracer.start_active_span('/auth/register') as scope:
        jsonData = request.json
        username = jsonData.get('username')
        password = jsonData.get('password')
        existing_user = users_collection.find_one({'username': username})

        loginData = {'username': username, 'password': password}

        if existing_user:
            users_collection.update_one({'username': username}, {"$set": loginData})
        else:
            # New User
            users_collection.insert_one(loginData)
            customerData = makeCustomerInfo(jsonData=jsonData)
            response = requests.post(f'{CUSTOMER_INFO_SERVICE_URL}/updateCustomerInfo', json = customerData)
            if response.status_code != 200:
                return jsonify({'message': 'Failed to Add customer'}), 500
        return "Successful Regiatration", 200


@app.route('/login', methods=['POST'])
@tracing.trace()
def login():
    with tracer.start_active_span('/auth/login') as scope:
        data = request.json
        username = data.get('username')
        password = data.get('password')
        user = users_collection.find_one({'username': username})
        if not user:
            return jsonify({'message': 'Username does not exist'}), 404
        else:
            print("user password", user["password"])
            if user["password"]!=password:
                return "UnAuthenticated Access", 303
            else:
                payload = {
                    'user': username,
                    'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=30)
                }
                token = jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')
                return jsonify({'Status': "Success", "Status Code": 200, "token": token, "username": username})


@app.route('/logout', methods=['POST'])
@tracing.trace()
@token_required
def logout():
    with tracer.start_active_span('/auth/logout') as scope:
        token = request.headers['Authorization']
        redis_command(redis_client.set, token, 'blacklisted', ex=30*60)  # Blacklist for 30 minutes
        return jsonify({'message': 'Logged out successfully'})

@app.route('/clearData', methods=['POST'])
@tracing.trace()
def clearContacts():
    users_collection.delete_many({})
    return "All data cleared from contacts collection", 200

@app.route("/getUserInfos", methods=["GET"])
@tracing.trace()
def getUserInfos():
    with tracer.start_active_span('/auth/getUserInfos') as scope:
        customer_datas = users_collection.find()
        datas = []
        for contact in customer_datas:
            contact_dict = {key: value for key, value in contact.items() if key != '_id'}
            datas.append(contact_dict)
        return jsonify(datas)

def makeCustomerInfo(jsonData):
    username = jsonData.get('username')
    password = jsonData.get('password')
    name = jsonData.get('name')
    email = jsonData.get('email')
    contact = jsonData.get('contact')
    address = jsonData.get('address')
    # Account no.
    account_number = generate_acc_no(username, password, name, email, contact, address)
    # Dmat/Acc Balance
    dmat_balance = 0
    acc_balance = 50000
    # Default pic
    customer_pic_url = "https://imgs.search.brave.com/QZ3mtUm8nZzRX-Ru5cyHaCL5eBj9vXxTOz81T5eq1Ao/rs:fit:860:0:0:0/g:ce/aHR0cHM6Ly93d3cu/cG5naXRlbS5jb20v/cGltZ3MvbS81MDQt/NTA0MDUyOF9lbXB0/eS1wcm9maWxlLXBp/Y3R1cmUtcG5nLXRy/YW5zcGFyZW50LXBu/Zy5wbmc"

    customer_info = {
        "username": username,
        "password": password,
        "name": name,
        "email": email,
        "contact": contact,
        "address": address,
        "account_number": account_number,
        "acc_balance": acc_balance,
        "dmat_balance": dmat_balance,
        "customer_pic_url": customer_pic_url,
    }

    return customer_info

def generate_acc_no(username, password, name, email, contact, address):
    unique_string = f"{username}_{password}_{name}_{email}_{contact}_{address}"
    hash_object = hashlib.sha256(unique_string.encode())
    hex_dig = hash_object.hexdigest()
    digits = ''.join(filter(str.isdigit, hex_dig))
    account_number = '5' + digits[:11]
    account_number = account_number.ljust(12, '0')

    return account_number

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=SELF_PORT, debug=True)