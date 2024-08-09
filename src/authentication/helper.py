import time
import redis


def redis_command(command, *args, **kwargs):
    max_retries = 3
    count = 0
    backoff_seconds = 5
    while True:
        try:
            return command(*args, **kwargs)
        except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError):
            count += 1
            if count > max_retries:
                raise
        print('Retrying in {} seconds'.format(backoff_seconds))
        time.sleep(backoff_seconds)