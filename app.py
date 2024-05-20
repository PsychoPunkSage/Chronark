from flask import Flask, render_template, request, redirect, url_for
import os
import random

app = Flask(__name__)

# Directory for storing images
# BANNER_DIR = 'src/offer-banner/images'
BANNER_DIR = 'static/offer-banner'

@app.route('/')
def index():
    banners = os.listdir(BANNER_DIR)
    # banners = [os.path.join(BANNER_DIR, banner) for banner in banners]  # Include the directory in the image path
    return render_template('index.html', banners=banners)

@app.route('/open-account', methods=['POST'])
def open_account():
    # Process the form data
    name = request.form['name']
    dob = request.form['dob']
    mobile_no = request.form['mobile_no']
    pan_card = request.form['pan_card']
    email = request.form['email']
    address = request.form['address']
    
    # Here you would call the function to open an account, e.g., open_account(name, dob, mobile_no, pan_card, email, address)
    
    return redirect(url_for('index'))

@app.route('/generate-credit-card', methods=['POST'])
def generate_credit_card():
    # Process the form data
    account_number = request.form['account_number']
    secret_passcode = request.form['secret_passcode']
    dob = request.form['dob']
    
    # Here you would call the function to generate a credit card, e.g., check_account_legitimacy(account_number, secret_passcode, dob)
    
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
