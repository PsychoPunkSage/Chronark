import json
import random
from helper import hredis

def get_offer_banner(banner_list):
    if not banner_list:
        return None
    random_banner = random.choice(banner_list)
    return random_banner

class Ad:
    def __init__(self, adID="", alt="", url="", category="", date="", time="") -> None:
        self.adID = adID
        self.alt = alt
        self.url = url
        self.category = category
        self.date = date
        self.time = time
    def created_at(self):
        return self.date + " || " + self.time

def getAds():
    ads = {}
    adIDs = hredis.redis_command(hredis.r_client.scan_iter, "*")
    for adID in adIDs:
        ad = getAd(adID)
        if "adID" in ad:
            ads[ad["adID"]] = ad
        else:
            print(f"Invalid ad data for adID {adID}: {ad}")
    return ads

def getAd(adID):
    ad = hredis.redis_command(hredis.r_client.get, adID)
    if ad is None:
        return {}
    else:
        try:
            return json.loads(ad.decode('utf-8'))
        except json.JSONDecodeError as e:
            print(f"JSONDecodeError: {e}")
            print(f"Raw ad data: {ad}")
            return {}

def updateAd(ad):
    if isinstance(ad, Ad):
        hredis.redis_command(hredis.r_client.set, ad.adID, json.dumps(ad.__dict__))
    else:
        raise TypeError("Expected an instance of Ad class")

def updateAds(ads):
    for ad in ads:
        updateAd(ad)