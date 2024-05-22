import json
from flask import Flask, render_template, request, redirect, url_for

from src.offer_banner.ads import getAds, getAd, updateAds, Ad
from src.offer_banner.offerBanner import get_offer_banner

app = Flask(__name__)

BANNER_DIR = 'static/offer-banner'

@app.route('/', methods=['GET'])
def get_ads():
    ads = getAds()
    return json.dumps(ads)
# def index():
#     banner = get_offer_banner()
#     return render_template('index.html', banner=banner)

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

    if "adID" not in jsonData:
        return "adID required", 400
    if "alt" not in jsonData:
        return "alt required", 400
    if "image_path" not in jsonData:
        return "image_path required", 400
    if "category" not in jsonData:
        return "category required", 400
    if "date" not in jsonData:
        return "date required", 400
    if "time" not in jsonData:
        return "time required", 400
    
    ads = get_ads()

    ads[jsonData["adID"]] = Ad(jsonData["adID"], jsonData["alt"], jsonData["image_path"], jsonData["category"], jsonData["date"], jsonData["time"]).__dict__
    updateAds(ads)
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
