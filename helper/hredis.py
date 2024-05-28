import os
import time
import redis
from dotenv import load_dotenv

# Env variables
load_dotenv()
redis_password = os.getenv('REDIS_PASSWORD')
print(redis_password)
r_client = redis.Redis(host="localhost", port=6379, password=redis_password)
print(r_client)
def redis_command(command, *args):
    max_retries = 3
    count = 0
    backoffSeconds = 5
    while True:
        try:
            return command(*args)
        except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError):
            count += 1
            if count > max_retries:
                raise
        print('Retrying in {} seconds'.format(backoffSeconds))
        time.sleep(backoffSeconds)