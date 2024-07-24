import os
import jwt
import redis
import datetime

from flask import Flask, request, jsonify
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from helper import redis_command

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your_super_complex_secret_key_here')

SELF_PORT = os.environ.get('SELF_PORT')
REDIS_PORT = os.environ.get('REDIS_PORT')
REDIS_HOST = os.environ.get('REDIS_HOST')
REDIS_PASSWORD = os.environ.get('REDIS_PASSWORD')
MONGO_DB_HOST = os.environ.get('MONGO_DB_HOST')
MONGO_DB_PORT = os.environ.get('MONGO_DB_PORT')
MONGO_DB_USERNAME = os.environ.get('MONGO_DB_USERNAME')
MONGO_DB_PASSWORD = os.environ.get('MONGO_DB_PASSWORD')

redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD)

mongo_client = MongoClient(username=MONGO_DB_USERNAME, password=MONGO_DB_PASSWORD, host=MONGO_DB_HOST, port=int(MONGO_DB_PORT))
data = mongo_client.auth_db
users_collection = data.users

def token_required(f):
    def decorator(*args, **kwargs):
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
    return decorator

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if users_collection.find_one({'username': data['username']}):
        return jsonify({'message': 'Username already exists'}), 409

    hashed_password = generate_password_hash(data['password'], method='sha256')
    users_collection.insert_one({'username': data['username'], 'password': hashed_password})
    return jsonify({'message': 'Registered successfully'}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user = users_collection.find_one({'username': data['username']})
    if not user:
        return jsonify({'message': 'Username does not exist'}), 404

    if check_password_hash(user['password'], data['password']):
        token = jwt.encode({'user': data['username'], 'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=30)}, app.config['SECRET_KEY'])
        return jsonify({'token': token})

    return jsonify({'message': 'Could not verify password'}), 401

@app.route('/logout', methods=['POST'])
@token_required
def logout():
    token = request.headers['Authorization']
    redis_command(redis_client.set, token, 'blacklisted', ex=30*60)  # Blacklist for 30 minutes
    return jsonify({'message': 'Logged out successfully'})

@app.route('/protected', methods=['GET'])
@token_required
def protected():
    return jsonify({'message': 'This is protected'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=SELF_PORT, debug=True)

