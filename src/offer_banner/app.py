import os
import json
import time
import redis
# from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

# Load environment variables
# load_dotenv()
SELF_PORT = os.environ.get('SELF_PORT')

REDIS_PASSWORD = os.environ.get('REDIS_PASSWORD')
REDIS_PORT = os.environ.get('REDIS_PORT')
REDIS_HOST = os.environ.get('REDIS_HOST')
r_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD)

def redis_command(command, *args):
    max_retries = 3
    count = 0
    backoff_seconds = 5
    while True:
        try:
            return command(*args)
        except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError):
            count += 1
            if count > max_retries:
                raise
        print('Retrying in {} seconds'.format(backoff_seconds))
        time.sleep(backoff_seconds)


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

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html', r_client=r_client, REDIS_HOST=REDIS_HOST, REDIS_PORT=REDIS_PORT, REDIS_PASSWORD=REDIS_PASSWORD)


@app.route('/getAds', methods=['GET'])
def getAds():
    ads = {}
    adIDs = redis_command(r_client.scan_iter, "*")
    for adID in adIDs:
        ad = getAd(adID)
        if "adID" in ad:
            ads[ad["adID"]] = ad
        else:
            print(f"Invalid ad data for adID {adID}: {ad}")
    return jsonify(ads)


@app.route('/getAd/<string:adID>', methods=['GET'])
def getAd(adID):
    ad = redis_command(r_client.get, adID)
    if ad is None:
        return {}, 404
    else:
        try:
            return json.loads(ad.decode('utf-8'))
        except json.JSONDecodeError as e:
            print(f"JSONDecodeError: {e}")
            print(f"Raw ad data: {ad}")
            return {}

@app.route('/updateAd', methods=['POST'])
def updateAd():
    jsonData = request.json
    ad = Ad(**jsonData)
    redis_command(r_client.set, ad.adID, json.dumps(ad.__dict__))
    return "Success", 200

@app.route('/updateAds', methods=['POST'])
def updateAds():
    jsonData = request.json
    for ad_data in jsonData:
        ad = Ad(**ad_data)
        updateAd(ad)
    return "Success", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=SELF_PORT, debug=True)
    # app.run(host='0.0.0.0', debug=True)
