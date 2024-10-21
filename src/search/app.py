import difflib
import json
import os
import time
import redis
from pymongo import MongoClient
from flask import Flask, render_template, request, jsonify

from jaeger_client import Config
from flask_opentracing import FlaskTracing

SELF_PORT = os.environ.get('SELF_PORT')
MONGO_DB_HOST = os.environ.get('MONGO_DB_HOST')
MONGO_DB_PORT = os.environ.get('MONGO_DB_PORT')
MONGO_DB_USERNAME = os.environ.get('MONGO_DB_USERNAME')
MONGO_DB_PASSWORD = os.environ.get('MONGO_DB_PASSWORD')

SEARCH_REDIS_PASSWORD = os.environ.get('SEARCH_REDIS_PASSWORD')
SEARCH_REDIS_PORT = os.environ.get('SEARCH_REDIS_PORT')
SEARCH_REDIS_HOST = os.environ.get('SEARCH_REDIS_HOST')

JAEGER_AGENT_HOST = os.environ.get('JAEGER_AGENT_HOST')
JAEGER_AGENT_PORT = os.environ.get('JAEGER_AGENT_PORT')

app = Flask(__name__)

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
        service_name='ms-search',
    )
    return config.initialize_tracer()

tracer = init_tracer()
tracing = FlaskTracing(tracer, True, app)

def trace_mongo_operation(scope, operation: str, collection_name: str, query: dict):
    span = scope.span
    
    span.set_tag('db.type', 'mongodb')
    span.set_tag('db.collection', collection_name)
    span.set_tag('db.operation', operation)
    span.log_kv({'query': query})

def trace_redis_operation(scope, operation: str, key: str, value: str = None):
    span = scope.span
    
    span.set_tag('cache.type', 'redis')
    span.set_tag('cache.operation', operation)
    span.set_tag('cache.key', key)
    
    if value:
        span.set_tag('cache.value', value)  # Optionally log value for 'set' operations
    
    span.log_kv({'key': key, 'value': value if value else 'N/A'})


# ================================================================================================ #

r_client = redis.Redis(host=SEARCH_REDIS_HOST, port=SEARCH_REDIS_PORT, password=SEARCH_REDIS_PASSWORD)
db_client = MongoClient(
    username=MONGO_DB_USERNAME, 
    password=MONGO_DB_PASSWORD, 
    host=MONGO_DB_HOST, 
    port=int(MONGO_DB_PORT)
)
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
    def __init__(self, index_id="", index_tag="", heading="", content=""):
        self.index_id = index_id
        self.index_tag = index_tag
        self.heading = heading
        self.content = content
    
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
@tracing.trace()
def index():
    with tracer.start_active_span('/search/') as scope:
        return render_template(
            'index.html',
            r_client=r_client, 
            SEARCH_REDIS_HOST=SEARCH_REDIS_HOST, 
            SEARCH_REDIS_PORT=SEARCH_REDIS_PORT, 
            SEARCH_REDIS_PASSWORD=SEARCH_REDIS_PASSWORD, 
            m_client=db_client , 
            MONGO_DB_HOST=MONGO_DB_HOST, 
            MONGO_DB_PORT=MONGO_DB_PORT, 
            MONGO_DB_USERNAME=MONGO_DB_USERNAME, 
            MONGO_DB_PASSWORD=MONGO_DB_PASSWORD
        )

@app.route('/clearContacts', methods=['POST'])
@tracing.trace()
def clearContacts():
    with tracer.start_active_span('mongo_insert') as mongo_span:
        trace_mongo_operation(mongo_span, 'delete', 'search/clear_contacts', {})
        index_collection.delete_many({})
    return "All data cleared from contacts collection", 200

@app.route("/getIndexKeys", methods=["GET"])
@tracing.trace()
def getIndexKeys():
    with tracer.start_active_span('/search/getIndexKeys') as scope:

        with tracer.start_active_span('redis_keys') as redis_span:
            trace_redis_operation(redis_span, 'keys', '*')
            all_keys = redis_command(r_client.keys, '*')

        all_keys = [key.decode('utf-8') for key in all_keys]  # Get list of strings
        return all_keys, 200

@app.route("/getIndex", methods=["POST"])
@tracing.trace()
def getIndex():
    with tracer.start_active_span('/search/getIndex') as scope:
        keyword = request.json.get('prompt')

        if not keyword:
            return jsonify({"error": "Keyword is required"}), 400

        similar_key = get_similar_index_id_from_redis(keyword)
        if similar_key:

            with tracer.start_active_span('redis_get') as redis_span:
                trace_redis_operation(redis_span, 'get', similar_key)
                index_data = redis_command(r_client.get, similar_key)
                
            if index_data:
                index_data = json.loads(index_data)
                return jsonify({"source": "Redis", "data": index_data}), 200

        # If no similar key found in Redis, fall back to MongoDB
        similar_index_id = get_similar_index_id_from_mongo(keyword)
        if similar_index_id:
            with tracer.start_active_span('mongo_insert') as mongo_span:
                trace_mongo_operation(mongo_span, 'find', 'search/getIndex', {'index_id':similar_index_id})
                existing_index = index_collection.find_one({"index_id": similar_index_id})
            if existing_index:
                index_data = {
                    "index_id": existing_index["index_id"],
                    "index_tag": existing_index["index_tag"],
                    "heading": existing_index["heading"],
                    "content": existing_index["content"]
                }

                with tracer.start_active_span('redis_set') as redis_span:
                    trace_redis_operation(redis_span, 'set', existing_index["index_id"], json.dumps(index_data))
                    redis_command(r_client.set, existing_index["index_id"], json.dumps(index_data))

                return jsonify({"source": "MongoDB", "data": index_data}), 200

        return jsonify({"error": "No matching index found"}), 404


@app.route("/updateIndex", methods=["POST"])
@tracing.trace()
def updateIndex():
    with tracer.start_active_span('/search/updateIndex') as scope:
        # Update only in `Mongodb`
        jsonData = request.json
        index_id = jsonData.get('index_id')
        with tracer.start_active_span('mongo_insert') as mongo_span:
            trace_mongo_operation(mongo_span, 'find', 'search/updateIndex:find', {'index_id':index_id})
            existing_data = index_collection.find_one({"index_id": index_id})

        if existing_data:
            with tracer.start_active_span('mongo_insert') as mongo_span:
                trace_mongo_operation(mongo_span, 'update', 'search/updateIndex:update', {'index_id':index_id})
                index_collection.update_one({"index_id": index_id}, {"$set": jsonData})
        else:
            with tracer.start_active_span('mongo_insert') as mongo_span:
                trace_mongo_operation(mongo_span, 'insert', 'search/updateIndex:insert', jsonData)
                index_collection.insert_one(jsonData)
        return "Success", 200

# ============================================================================================================ #

def get_all_keys(r_client):

    with tracer.start_active_span('redis_keys') as redis_span:
        trace_redis_operation(redis_span, 'keys', '*')
        return redis_command(r_client.keys, '*')

def get_similar_index_id_from_redis(keyword):
    # Retrieve all keys from Redis
    with tracer.start_active_span('redis_keys') as redis_span:
        trace_redis_operation(redis_span, 'keys', '*')
        all_keys = redis_command(r_client.keys, '*')
        
    all_keys = [key.decode('utf-8') for key in all_keys]

    best_match_id = None
    highest_similarity = 0

    # Iterate through all keys to find the best match
    for key in all_keys:
        with tracer.start_active_span('redis_get') as redis_span:
            trace_redis_operation(redis_span, 'get', key)
            value = redis_command(r_client.get, key)

        if value:
            try:
                value = value.decode('utf-8')
                value_data = json.loads(value)
                index_tags = value_data.get('index_tag', '').split(', ')

                # Check each tag for similarity
                for tag in index_tags:
                    similarity = difflib.SequenceMatcher(None, keyword, tag).ratio()
                    if similarity > highest_similarity:
                        highest_similarity = similarity
                        best_match_id = key
            except json.JSONDecodeError as e:
                print(f"JSON decode error for key {key}: {e}")
                continue

    return best_match_id if highest_similarity > 0.8 else None  # Set a threshold for similarity

def get_similar_index_id_from_mongo(keyword):
    with tracer.start_active_span('mongo_insert') as mongo_span:
        trace_mongo_operation(mongo_span, 'find', 'search/get_similar', {})
        all_entries = index_collection.find({}, {"index_tag": 1, "index_id": 1})

    best_match_id = None
    highest_similarity = 0

    for entry in all_entries:
        index_id = entry['index_id']
        index_tags = entry['index_tag'].split(', ')
        
        for tag in index_tags:
            similarity = difflib.SequenceMatcher(None, keyword, tag).ratio()
            if similarity > highest_similarity:
                highest_similarity = similarity
                best_match_id = index_id

    return best_match_id if highest_similarity > 0.8 else None  # Set a threshold for similarity

# ============================================================================================================ #

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=SELF_PORT, debug=True)