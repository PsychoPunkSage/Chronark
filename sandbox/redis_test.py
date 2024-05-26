import os
import json
import redis
from dotenv import load_dotenv

load_dotenv()
redis_password = os.getenv('REDIS_PASSWORD')

r = redis.Redis(host="localhost", port=6379, password=redis_password)

r.set("test", json.dumps({"name": "Alice", "age": 30, "city": "Wonderland"}))
r.set("examiner", "examinee")

# print("test: ", r.get("test"), " result: ", r.get("examiner"))
# print(type(r.get("test")))
result = r.get("test")

string_data = result.decode('utf-8')
# print(string_data)
json_data = json.loads(string_data)
print(json_data, type(json_data))