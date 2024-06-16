import difflib
import json
import os
import time
import redis
from pymongo import MongoClient
from flask import Flask, render_template, request, jsonify

SELF_PORT = os.environ.get('SELF_PORT')
MONGO_DB_HOST = os.environ.get('MONGO_DB_HOST')
MONGO_DB_PORT = os.environ.get('MONGO_DB_PORT')
MONGO_DB_USERNAME = os.environ.get('MONGO_DB_USERNAME')
MONGO_DB_PASSWORD = os.environ.get('MONGO_DB_PASSWORD')

SEARCH_REDIS_PASSWORD = os.environ.get('SEARCH_REDIS_PASSWORD')
SEARCH_REDIS_PORT = os.environ.get('SEARCH_REDIS_PORT')
SEARCH_REDIS_HOST = os.environ.get('SEARCH_REDIS_HOST')

app = Flask(__name__)

r_client = redis.Redis(host=SEARCH_REDIS_HOST, port=SEARCH_REDIS_PORT, password=SEARCH_REDIS_PASSWORD)
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
    
    def to_dict(self):
        return {
            "index_tag": self.index_tag,
            "heading": self.heading,
            "content": self.content
        }
    
'''
For Redis:

key         |         value
============================
index_tag   | {   
            |   heading:   
            |   content:
            | }
'''
# test
in1 = redis_command(r_client.set, 'test_key', 'test_value')
print(in1)
value = redis_command(r_client.get, 'test_key')
print(value)

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html', r_client=r_client, SEARCH_REDIS_HOST=SEARCH_REDIS_HOST, SEARCH_REDIS_PORT=SEARCH_REDIS_PORT, SEARCH_REDIS_PASSWORD=SEARCH_REDIS_PASSWORD, m_client=db_client , MONGO_DB_HOST=MONGO_DB_HOST, MONGO_DB_PORT=MONGO_DB_PORT, MONGO_DB_USERNAME=MONGO_DB_USERNAME, MONGO_DB_PASSWORD=MONGO_DB_PASSWORD)

@app.route('/clearContacts', methods=['POST'])
def clearContacts():
    index_collection.delete_many({})
    return "All data cleared from contacts collection", 200

@app.route("/getIndexKeys", methods=["GET"])
def getIndexKeys():
    all_keys = redis_command(r_client.keys, '*')
    all_keys = [key.decode('utf-8') for key in all_keys]  # Get list of strings
    return all_keys, 200

@app.route("/getIndex", methods=["POST"])
def getIndex():
    keyword = request.json['prompt']
    print("**Keyword** ", keyword)
    all_keys = redis_command(r_client.keys, '*')
    all_keys = [key.decode('utf-8') for key in all_keys]  # Get list of strings
    similar_key = get_similar_index_from_mongo(keyword)
    return similar_key

    # if all_keys:
    #     similar_key = get_similar_key(keyword, all_keys)
    #     if similar_key:
    #         index_data = redis_command(r_client.get, similar_key)
    #         if index_data:
    #             return jsonify(index_data), "Redis", 200

    # existing_index = index_collection.find_one({"index_tag": keyword})
    # if existing_index is None:
    #     similar_index_tag = get_similar_index_from_mongo(keyword)
    #     if similar_index_tag:
    #         existing_index = index_collection.find_one({"index_tag": similar_index_tag})
    #         if existing_index:
    #             index_data = IndexTemplate(
    #                 index_tag=existing_index["index_tag"],
    #                 heading=existing_index["heading"],
    #                 content=existing_index["content"]
    #             ).to_dict()

    #             redis_command(r_client.set, existing_index["index_tag"], json.dumps(index_data))
    #             return jsonify(index_data),  "MongoDB", 200
    #     return jsonify({}), None, 404

    # index_data = IndexTemplate(
    #     index_tag=existing_index["index_tag"],
    #     heading=existing_index["heading"],
    #     content=existing_index["content"]
    # ).to_dict()

    # redis_command(r_client.set, existing_index["index_tag"], json.dumps(index_data))
    # return jsonify(index_data), "MongoDB", 200


@app.route("/updateIndex", methods=["POST"])
def updateIndex():
    # Update only in `Mongodb`
    jsonData = request.json
    index_tag = jsonData.get('index_tag')
    existing_data = index_collection.find_one({"index_tag": index_tag})

    if existing_data:
        index_collection.update_one({"index_tag": index_tag}, {"$set": jsonData})
    else:
        index_collection.insert_one(jsonData)
    return "Success", 200

# ============================================================================================================ #

def get_all_keys(r_client):
    return redis_command(r_client.keys, '*')

def get_similar_key(keyword, all_keys):
    similar_keys = difflib.get_close_matches(keyword, all_keys, n=1, cutoff=0.8)
    return similar_keys[0] if similar_keys else None

def get_similar_index_from_mongo(keyword):
    all_entries = index_collection.find({}, {"index_tag": 1, "index_id": 1})

    best_match = None
    best_match_id = None
    highest_similarity = 0

    for entry in all_entries:
        index_id = entry['index_id']
        index_tags = entry['index_tag'].split(', ')
        
        for tag in index_tags:
            similarity = difflib.SequenceMatcher(None, keyword, tag).ratio()
            if similarity > highest_similarity:
                highest_similarity = similarity
                best_match = tag
                best_match_id = index_id

    return best_match_id if best_match else None

# ============================================================================================================ #

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=SELF_PORT, debug=True)