import os
import json
import random
import requests
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

SELF_PORT = os.environ.get('SELF_PORT')

# Offer-banner urls
OFFER_BANNER_SERVICE_HOST = os.environ.get('OFFER_BANNER_SERVICE_HOST')
OFFER_BANNER_SERVICE_PORT = os.environ.get('OFFER_BANNER_SERVICE_PORT')
ADS_SERVICE_URL = 'http://' + OFFER_BANNER_SERVICE_HOST + ':' + OFFER_BANNER_SERVICE_PORT

# Contact
CONTACT_SERVICE_HOST = os.environ.get('CONTACT_SERVICE_HOST')
CONTACT_SERVICE_PORT = os.environ.get('CONTACT_SERVICE_PORT')
CONTACT_SERVICE_URL = 'http://' + CONTACT_SERVICE_HOST + ':' + CONTACT_SERVICE_PORT


@app.route('/', methods=['GET'])
def get_ads():
    response = requests.get(f'{ADS_SERVICE_URL}/getAds')
    ads = response.json()
    banner_id = get_offer_banner(list(ads.keys()))
    if banner_id is not None:
        banner = ads[banner_id]
    else:
        banner = None

    response = requests.get(f'{CONTACT_SERVICE_URL}/clients')
    contacts = response.json()

    return render_template('index.html', banner=banner, contacts=contacts)
    # return render_template('index.html', banner=banner)

@app.route('/contact', methods=['GET'])
def get_contacts():
    response = requests.get(f'{CONTACT_SERVICE_URL}/clients')
    contacts = response.json()
    return render_template('index.html', contacts=contacts)

@app.route('/get/<string:adID>', methods=['GET'])
def get_ad(adID):
    response = requests.get(f'{ADS_SERVICE_URL}/getAd/{adID}')
    if response.status_code == 404:
        return {}, 404
    else:
        ad = response.json()
        return json.dumps(ad), 200

@app.route('/set', methods=['POST'])
def add_ad():
    jsonData = request.json
    required_fields = ["adID", "alt", "url", "category", "date", "time"]
    for field in required_fields:
        if field not in jsonData:
            return f"{field} required", 400

    ad = {
        "adID": jsonData["adID"],
        "alt": jsonData["alt"],
        "url": jsonData["url"],
        "category": jsonData["category"],
        "date": jsonData["date"],
        "time": jsonData["time"]
    }

    response = requests.post(f'{ADS_SERVICE_URL}/updateAd', json=ad)
    return "success", response.status_code

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

def get_offer_banner(banner_list):
    if not banner_list:
        return None
    random_banner = random.choice(banner_list)
    return random_banner

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=SELF_PORT, debug=True)
    # app.run(host='0.0.0.0', debug=True)
