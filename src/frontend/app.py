import os
import sys
import json
# import redis
from flask import Flask, render_template, request, redirect, url_for

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from src.offer_banner.ads import getAds, getAd, updateAd, get_offer_banner, Ad

app = Flask(__name__)

# TEST
# print("Running Redis Setup test")
# print(redis.redis_command(redis.r_client.set, 'foo', 'bar'))
# print(redis.redis_command(redis.r_client.get, 'foo'))

@app.route('/', methods=['GET'])
def get_ads():
    ads = getAds()
    banner_id = get_offer_banner(list(ads.keys()))
    if banner_id is not None:
        banner = ads[banner_id]
    else:
        banner = None
    return render_template('index.html', banner=banner)

@app.route('/get/<string:adID>', methods=['GET'])
def get_ad(adID):
    ad = getAd(adID)
    if ad == {}:
        return {}, 404
    else:
        return json.dumps(ad), 200

@app.route('/set', methods=['POST'])
def add_ad():
    jsonData = request.json

    required_fields = ["adID", "alt", "url", "category", "date", "time"]
    for field in required_fields:
        if field not in jsonData:
            return f"{field} required", 400

    ad = Ad(
        adID=jsonData["adID"],
        alt=jsonData["alt"],
        url=jsonData["url"],
        category=jsonData["category"],
        date=jsonData["date"],
        time=jsonData["time"]
    )
    updateAd(ad)
    return "success", 200

@app.route('/open-account', methods=['POST'])
def open_account():
    # Process the form data
    name = request.form['name']
    dob = request.form['dob']
    mobile_no = request.form['mobile_no']
    pan_card = request.form['pan_card']
    email = request.form['email']
    address = request.form['address']
    return redirect(url_for('index'))

@app.route('/generate-credit-card', methods=['POST'])
def generate_credit_card():
    # Process the form data
    account_number = request.form['account_number']
    secret_passcode = request.form['secret_passcode']
    dob = request.form['dob']
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
