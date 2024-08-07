import os
import jwt
import redis
import datetime

from flask import Flask, render_template, request, jsonify
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from helper import redis_command

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

# @app.route('/test_db', methods=['GET'])
# def test_db_connection():
#     try:
#         # Insert a test document
#         test_user = {"username": "test_user", "password": "test_password"}
#         insert_result = users_collection.insert_one(test_user)
#         print(f"Inserted document ID: {insert_result.inserted_id}")

#         # Fetch the test document
#         fetched_user = users_collection.find_one({"username": "test_user"})
#         print(f"Fetched document: {fetched_user}")

#         # Delete the test document
#         delete_result = users_collection.delete_one({"username": "test_user"})
#         print(f"Deleted document count: {delete_result.deleted_count}")

#         return jsonify({
#             "inserted_id": str(insert_result.inserted_id),
#             "fetched_user": fetched_user,
#             "deleted_count": delete_result.deleted_count
#         })
#     except Exception as e:
#         print(f"An error occurred: {e}")
#         return jsonify({"error": str(e)}), 500

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
def index():
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
def register():
    jsonData = request.json
    username = jsonData.get('username')
    existing_user = users_collection.find_one({'username': username})
    
    if existing_user:
        users_collection.update_one({'username': username}, {"$set": jsonData})
    else:
        users_collection.insert_one(jsonData)
    return "Successful Regiatration", 200

@app.route('/login', methods=['POST'])
def login():
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
            # token = jwt.encode({
            #     'user': username,
            #     'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=30)
            # }, app.config['SECRET_KEY'], algorithm='HS256')
            # return jsonify({'token': token})
            return "Success", 200

@app.route('/logout', methods=['POST'])
@token_required
def logout():
    token = request.headers['Authorization']
    redis_command(redis_client.set, token, 'blacklisted', ex=30*60)  # Blacklist for 30 minutes
    return jsonify({'message': 'Logged out successfully'})

# @app.route('/protected', methods=['GET'])
# @token_required
# def protected():
#     return jsonify({'message': 'This is protected'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=SELF_PORT, debug=True)

# Locust...APT