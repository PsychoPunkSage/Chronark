import os
import time
import redis
from dotenv import load_dotenv

# Env variables
load_dotenv()
redis_password = os.getenv('REDIS_PASSWORD')
print(redis_password)
r_client = redis.Redis(host="localhost", port=6380, password=redis_password)
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

try:
    redis_command(r_client.set, 'test_key', 'test_value')
    redis_command(r_client.set, 'test_key1', 'test_value1')
    redis_command(r_client.set, 'test_key2', 'test_value2')
    redis_command(r_client.set, 'test_key3', 'test_value3')
    redis_command(r_client.set, 'test_key4', 'test_value4')
    print('Set key success')

    all_keys = redis_command(r_client.keys, '*')
    all_keys = [key.decode('utf-8') for key in all_keys]
    print(all_keys)

    value = redis_command(r_client.get, 'test_key')
    print('Get key success, value:', value)
    
    # redis_command(r_client.delete, 'test_key')
    # print('Delete key success')

except redis.exceptions.RedisError as e:
    print('Redis error:', str(e))