import os
import random
import redis

def get_offer_banner(banner_list):
    if not banner_list:
        return None
    random_banner = random.choice(banner_list)
    return random_banner