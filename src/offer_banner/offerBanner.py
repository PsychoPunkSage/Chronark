import os
import random
import redis
# import time

def get_offer_banner():
    ad_path = 'static/offer-banner'
    banners = os.listdir(ad_path)
    
    if not banners:
        return None

    # while True:
    #     random_banner = random.choice(banners)
    #     print(random_banner)
    #     time.sleep(5)
    random_banner = random.choice(banners)
    return random_banner

def redis_test():
    r = redis.Redis(host='localhost', port=6379, decode_responses=True)
    r.set('foo', 'bar')
    print(r.get('foo'))

redis_test()