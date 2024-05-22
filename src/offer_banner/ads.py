import os.path
import csv
import json
from flask import Flask
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
    if os.path.isfile(dataPath):
        with open(dataPath, newline='') as adFile:
            data = adFile.read()
            ads = json.loads(data)
            return ads
    else:
        print("Error loading")
        return {}

def getAd(adID):
    ads = getAds()

    if adID in ads:
        return ads[adID]
    else:
        return {}

def updateAds(adDict):
    with open(dataPath, 'w', newline='') as adFile:
        adJson = json.dumps(adDict)
        adFile.write(adJson)