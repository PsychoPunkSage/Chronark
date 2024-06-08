import os
import random
import requests
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

SELF_PORT = os.environ.get('SELF_PORT')

# Offer-banner url
OFFER_BANNER_SERVICE_HOST = os.environ.get('OFFER_BANNER_SERVICE_HOST')
OFFER_BANNER_SERVICE_PORT = os.environ.get('OFFER_BANNER_SERVICE_PORT')
ADS_SERVICE_URL = 'http://' + OFFER_BANNER_SERVICE_HOST + ':' + OFFER_BANNER_SERVICE_PORT

# Contact url
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
    return render_template('index.html', banner=banner)

@app.route('/contact', methods=['GET'])
def contact():
    response = requests.get(f'{ADS_SERVICE_URL}/getAds')
    ads = response.json()
    banners = [get_offer_banner(list(ads.keys())) for _ in range(2)]
    if all(banners):
        banner_r, banner_l = (ads[banners[0]], ads[banners[1]])
    else:
        banner_r = banner_l = None

    response = requests.get(f'{CONTACT_SERVICE_URL}/getContacts')
    contacts = response.json()
    regional_contact = []
    for contact in contacts:
        if contact['region_id'] == 'tollfree':
            tollfree_contact = contact
        elif contact['region_id'] == 'overseas':
            overseas_contact = contact
        else:
            regional_contact.append(contact)

    response = requests.get(f'{CONTACT_SERVICE_URL}/getFaqs')
    faqs = response.json()
    categories = {}
    for item in faqs:
        category = item['category']
        if category not in categories:
            categories[category] = []
        categories[category].append(item)

    return render_template('contact.html', banner_r=banner_r, banner_l=banner_l, tollfree=tollfree_contact, overseas=overseas_contact, contacts=regional_contact, categories=categories )

@app.route('/record_conv', methods=['POST'])
def record_conv():
    # Capturing form data
    name = request.form['name']
    email = request.form['email']
    message = request.form['message']
    now = datetime.now()
    data = {
        'conversation_id': random.randint(1000000, 9999999),
        'name': name,
        'email': email,
        'message': message,
        'date': now.date().isoformat(),
        'time':now.time().isoformat(),
    }
    print("++++ DATA ++++", data)
    response = requests.post(f'{CONTACT_SERVICE_URL}/updateConvs', json=data)
    if response.status_code == 200:
        return 'Form submitted successfully!'
    else:
        return 'Failed to submit form.', response.status_code

@app.route('/setOfferBanner', methods=['POST'])
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

@app.route('/setContacts', methods=['POST'])
def add_contact():
    jsonData = request.json
    required_fields = ["id", "name", "employee", "customer", "email", "mobile", "address"]
    for field in required_fields:
        if field not in jsonData:
            return f"{field} required", 400

    contact = {
        "id": jsonData["id"],
        "name": jsonData["name"],
        "employee": jsonData["employee"],
        "customer": jsonData["customer"],
        "email": jsonData["email"],
        "mobile": jsonData["mobile"],
        "address": jsonData["address"]
    }

    response = requests.post(f'{CONTACT_SERVICE_URL}/updateClient', json=contact)
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
