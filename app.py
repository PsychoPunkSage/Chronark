from flask import Flask, render_template, request, redirect, url_for
from src.offer_banner.offerBanner import get_offer_banner
import os

app = Flask(__name__)

BANNER_DIR = 'static/offer-banner'

@app.route('/')
def index():
    banner = get_offer_banner()
    return render_template('index.html', banner=banner)

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
