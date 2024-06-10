import json
import os
import time
import redis
from pymongo import MongoClient
from flask import Flask, request, jsonify

SELF_PORT = os.environ.get('SELF_PORT')
MONGO_DB_HOST = os.environ.get('MONGO_DB_HOST')
MONGO_DB_PORT = os.environ.get('MONGO_DB_PORT')
MONGO_DB_USERNAME = os.environ.get('MONGO_DB_USERNAME')
MONGO_DB_PASSWORD = os.environ.get('MONGO_DB_PASSWORD')

REDIS_PASSWORD = os.environ.get('REDIS_PASSWORD')
REDIS_PORT = os.environ.get('REDIS_PORT')
REDIS_HOST = os.environ.get('REDIS_HOST')

app = Flask(__name__)

r_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD)
db_client = MongoClient(username=MONGO_DB_USERNAME, password=MONGO_DB_PASSWORD, host=MONGO_DB_HOST, port=int(MONGO_DB_PORT))
# Database init
data = db_client.search

# Collection init
index_collection = data.indexes

def redis_command(command, *args):
    max_retries = 3
    count = 0
    backoff_seconds = 5
    while True:
        try:
            return command(*args)
        except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError):
            count += 1
            if count > max_retries:
                raise
        print('Retrying in {} seconds'.format(backoff_seconds))
        time.sleep(backoff_seconds)

class IndexTemplate:
    def __init__(self, index_tag="", heading="", content=""):
        self.index_tag = index_tag
        self.heading = heading
        self.content = content
'''
For Redis:

key         |         value
============================
loan etc... | {   
            |   heading:   
            |   content:
            | }
'''
@app.route("/getIndex/<string:keyword>", methods=["GET"])
def getIndex(keyword):
    index_data = redis_command(r_client.get, keyword)
    if index_data is None:
        existing_index = index_collection.find_one({"index_tag": keyword})
        if existing_index is None:
            return jsonify({"error": "Not found"}), 404

        index_data = IndexTemplate(
            heading=existing_index["heading"],
            content=existing_index["content"]
        ).to_dict()

        redis_command(r_client.set, existing_index["index_tag"], json.dumps(index_data))
    
    index_data = json.loads(index_data)
    
    return jsonify(index_data), 200

@app.route("/updateIndex", methods=["GET"])
def updateIndex():
    jsonData = request.json
    index_tag = jsonData.get('index_tag')
    existing_data = index_collection.find_one({"index_tag": index_tag})

    if existing_data:
        index_collection.update_one({"index_tag": index_tag}, {"$set": jsonData})
    else:
        index_collection.insert_one(jsonData)
    return "Success", 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=SELF_PORT, debug=True)