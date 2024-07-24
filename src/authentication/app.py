import os
import jwt
import redis
import datetime

from flask import Flask, request, jsonify
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
redis_client = redis.StrictRedis(host='redis', port=6379, db=0)
mongo_client = MongoClient('mongodb://mongo:27017/')
db = mongo_client['auth_db']
users_collection = db['users']

def token_required(f):
    def decorator(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token is missing'}), 403

        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            if redis_client.get(token):
                return jsonify({'message': 'Token is blacklisted'}), 403
        except:
            return jsonify({'message': 'Token is invalid'}), 403

        return f(*args, **kwargs)
    return decorator

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    hashed_password = generate_password_hash(data['password'], method='sha256')
    users_collection.insert_one({'username': data['username'], 'password': hashed_password})
    return jsonify({'message': 'Registered successfully'}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user = users_collection.find_one({'username': data['username']})
    if user and check_password_hash(user['password'], data['password']):
        token = jwt.encode({'user': data['username'], 'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=30)}, app.config['SECRET_KEY'])
        return jsonify({'token': token})

    return jsonify({'message': 'Could not verify'}), 401

@app.route('/logout', methods=['POST'])
@token_required
def logout():
    token = request.headers['Authorization']
    redis_client.set(token, 'blacklisted', ex=30*60)  # Blacklist for 30 minutes
    return jsonify({'message': 'Logged out successfully'})

@app.route('/protected', methods=['GET'])
@token_required
def protected():
    return jsonify({'message': 'This is protected'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=SELF_PORT, debug=True)

