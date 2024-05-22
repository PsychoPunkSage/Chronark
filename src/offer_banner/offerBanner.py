import os
import random
import redis

def get_offer_banner():
    ad_path = 'static/offer-banner'
    banners = os.listdir(ad_path)
    
    if not banners:
        return None
    
    random_banner = random.choice(banners)
    return random_banner