import os.path
import csv
import json
from flask import Flask
from helper import redis
from flask import request

dataPath = "src/offer_banner/ads.json"

class Ad:
    def __init__(self, adID="", alt="", image_path="", category="", date="", time="") -> None:
        self.adID = adID
        self.alt = alt
        self.image_path = image_path
        self.category = category
        self.date = date
        self.time = time
    def created_at(self):
        return self.date + " || " + self.time

def getAds():
    # if os.path.isfile(dataPath):
    #     with open(dataPath, newline='') as adFile:
    #         data = adFile.read()
    #         ads = json.loads(data)
    #         return ads
    # else:
    #     print("Error loading")
    #     return {}
    ads = {}
    adIDs = redis.redis_command(redis.redis_command.scan_iter, "*")
    for adID in adIDs:
        ad = getAd(adID)
        ads[ad["adID"]] = ad
    return ads

def getAd(adID):
    # ads = getAds()
    # if adID in ads:
    #     return ads[adID]
    # else:
    #     return {}
    ad = redis.redis_command(redis.redis_master.get, adID)
    if ad is None:
        return {}
    else:
        return json.loads(str(ad, 'utf8'))

def updateAd(ad):
    redis.redis_command(redis.redis_master.set, ad.adID, json.dumps(ad.__dict__))

def updateAds(ads):
    # with open(dataPath, 'w', newline='') as adFile:
    #     adJson = json.dumps(adDict)
    #     adFile.write(adJson)
    for ad in ads:
        updateAd(ad)