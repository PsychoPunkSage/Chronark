import os
import random
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
