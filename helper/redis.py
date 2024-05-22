import os
import time
import redis
from dotenv import load_dotenv
from redis.sentinel import Sentinel


# Env variables
load_dotenv()
redis_sentinels = os.getenv('REDIS_SENTINELS')
redis_master_name = os.getenv('REDIS_MASTER_NAME')
redis_password = os.getenv('REDIS_PASSWORD')

# setup Sentinels
sentinels = []
for s in redis_sentinels.split(','):
    sentinels.append((s.split(":")[0], s.split(":")[1]))
redis_sentinel = Sentinel(sentinels, socket_timeout=5)
redis_master = redis_sentinel.master_for(redis_master_name,password = redis_password, socket_timeout=5)

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