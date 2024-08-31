from datetime import datetime
import hashlib
import os
from pymongo import MongoClient
from pymemcache.client import base
from flask import Flask, render_template, request, jsonify
import requests

app = Flask(__name__)

SELF_PORT = os.environ.get('SELF_PORT')
# MONGO_DB_HOST = os.environ.get('MONGO_DB_HOST')
# MONGO_DB_PORT = os.environ.get('MONGO_DB_PORT')
# MONGO_DB_USERNAME = os.environ.get('MONGO_DB_USERNAME')
# MONGO_DB_PASSWORD = os.environ.get('MONGO_DB_PASSWORD')
# MEMCACHED_HOST = os.environ.get('MEMCACHED_HOST')
# MEMCACHED_PORT = os.environ.get('MEMCACHED_PORT')
# Customer Info
CUSTOMER_INFO_SERVICE_HOST = os.environ.get('CUSTOMER_INFO_SERVICE_HOST')
CUSTOMER_INFO_SERVICE_PORT = os.environ.get('CUSTOMER_INFO_SERVICE_PORT')
CUSTOMER_INFO_SERVICE_URL = f'http://{CUSTOMER_INFO_SERVICE_HOST}:{CUSTOMER_INFO_SERVICE_PORT}'
# Customer Activity
CUSTOMER_ACTIVITY_SERVICE_HOST = os.environ.get('CUSTOMER_ACTIVITY_SERVICE_HOST')
CUSTOMER_ACTIVITY_SERVICE_PORT = os.environ.get('CUSTOMER_ACTIVITY_SERVICE_PORT')
CUSTOMER_ACTIVITY_SERVICE_URL = f'http://{CUSTOMER_ACTIVITY_SERVICE_HOST}:{CUSTOMER_ACTIVITY_SERVICE_PORT}'

@app.route('/', methods=['GET'])
def index():
    return render_template(
        'index.html', 
        self_port=SELF_PORT
    )

# ===================================================================================================================================================================================== #




if __name__ == '__main__':
    app.run(host='0.0.0.0', port=SELF_PORT, debug=True)