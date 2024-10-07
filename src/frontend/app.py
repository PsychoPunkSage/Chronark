import os
import random
import requests
from datetime import datetime
from tracing import setup_tracer, instrument_app
from flask import Flask, render_template, request, redirect, url_for, flash, session

from jaeger_client import Config
from flask_opentracing import FlaskTracing

app = Flask(__name__)

SELF_PORT = os.environ.get('SELF_PORT')
app.secret_key = os.environ.get('SECRET_KEY', 'your_super_complex_secret_key_here')

# Offer-banner url
OFFER_BANNER_SERVICE_HOST = os.environ.get('OFFER_BANNER_SERVICE_HOST')
OFFER_BANNER_SERVICE_PORT = os.environ.get('OFFER_BANNER_SERVICE_PORT')
ADS_SERVICE_URL = 'http://' + OFFER_BANNER_SERVICE_HOST + ':' + OFFER_BANNER_SERVICE_PORT

# Contact url
CONTACT_SERVICE_HOST = os.environ.get('CONTACT_SERVICE_HOST')
CONTACT_SERVICE_PORT = os.environ.get('CONTACT_SERVICE_PORT')
CONTACT_SERVICE_URL = 'http://' + CONTACT_SERVICE_HOST + ':' + CONTACT_SERVICE_PORT

# Credit Card Service
CREDIT_CARD_SERVICE_HOST = os.environ.get('CREDIT_CARD_SERVICE_HOST')
CREDIT_CARD_SERVICE_PORT = os.environ.get('CREDIT_CARD_SERVICE_PORT')
CREDIT_CARD_SERVICE_URL = 'http://' + CREDIT_CARD_SERVICE_HOST + ':' + CREDIT_CARD_SERVICE_PORT

# Search url
SEARCH_SERVICE_HOST = os.environ.get('SEARCH_SERVICE_HOST')
SEARCH_SERVICE_PORT = os.environ.get('SEARCH_SERVICE_PORT')
SEARCH_SERVICE_URL = 'http://' + SEARCH_SERVICE_HOST + ':' + SEARCH_SERVICE_PORT

# Auth service
AUTH_SERVICE_HOST = os.environ.get('AUTH_SERVICE_HOST')
AUTH_SERVICE_PORT = os.environ.get('AUTH_SERVICE_PORT')
AUTH_SERVICE_URL = f'http://{AUTH_SERVICE_HOST}:{AUTH_SERVICE_PORT}'

# Customer Info Service
CUSTOMER_INFO_SERVICE_HOST = os.environ.get('CUSTOMER_INFO_SERVICE_HOST')
CUSTOMER_INFO_SERVICE_PORT = os.environ.get('CUSTOMER_INFO_SERVICE_PORT')
CUSTOMER_INFO_SERVICE_URL = f'http://{CUSTOMER_INFO_SERVICE_HOST}:{CUSTOMER_INFO_SERVICE_PORT}'

# Personal Lending Service
PERSONAL_LENDING_SERVICE_HOST = os.environ.get('PERSONAL_LENDING_SERVICE_HOST')
PERSONAL_LENDING_SERVICE_PORT = os.environ.get('PERSONAL_LENDING_SERVICE_PORT')
PERSONAL_LENDING_SERVICE_URL = f'http://{PERSONAL_LENDING_SERVICE_HOST}:{PERSONAL_LENDING_SERVICE_PORT}'

# Business Lending Service
BUSINESS_LENDING_SERVICE_HOST = os.environ.get('BUSINESS_LENDING_SERVICE_HOST')
BUSINESS_LENDING_SERVICE_PORT = os.environ.get('BUSINESS_LENDING_SERVICE_PORT')
BUSINESS_LENDING_SERVICE_URL = f'http://{BUSINESS_LENDING_SERVICE_HOST}:{BUSINESS_LENDING_SERVICE_PORT}'

# Mortgage Service
MORTGAGE_SERVICE_HOST = os.environ.get('MORTGAGE_SERVICE_HOST')
MORTGAGE_SERVICE_PORT = os.environ.get('MORTGAGE_SERVICE_PORT')
MORTGAGE_SERVICE_URL = f'http://{MORTGAGE_SERVICE_HOST}:{MORTGAGE_SERVICE_PORT}'

# Investment Service
INVESTMENT_SERVICE_HOST = os.environ.get('INVESTMENT_SERVICE_HOST')
INVESTMENT_SERVICE_PORT = os.environ.get('INVESTMENT_SERVICE_PORT')
INVESTMENT_SERVICE_URL = f'http://{INVESTMENT_SERVICE_HOST}:{INVESTMENT_SERVICE_PORT}'

# Deposit n Withdrawl Service
DEPOSIT_WITHDRAWL_SERVICE_HOST = os.environ.get('DEPOSIT_WITHDRAWL_SERVICE_HOST')
DEPOSIT_WITHDRAWL_SERVICE_PORT = os.environ.get('DEPOSIT_WITHDRAWL_SERVICE_PORT')
DEPOSIT_WITHDRAWL_SERVICE_URL = f'http://{DEPOSIT_WITHDRAWL_SERVICE_HOST}:{DEPOSIT_WITHDRAWL_SERVICE_PORT}'

# Customer Activity Service
CUSTOMER_ACTIVITY_SERVICE_HOST = os.environ.get('CUSTOMER_ACTIVITY_SERVICE_HOST')
CUSTOMER_ACTIVITY_SERVICE_PORT = os.environ.get('CUSTOMER_ACTIVITY_SERVICE_PORT')
CUSTOMER_ACTIVITY_SERVICE_URL = f'http://{CUSTOMER_ACTIVITY_SERVICE_HOST}:{CUSTOMER_ACTIVITY_SERVICE_PORT}'

# Payments Service
PAYMENTS_SERVICE_HOST = os.environ.get('PAYMENTS_SERVICE_HOST')
PAYMENTS_SERVICE_PORT = os.environ.get('PAYMENTS_SERVICE_PORT')
PAYMENTS_SERVICE_URL = f'http://{PAYMENTS_SERVICE_HOST}:{PAYMENTS_SERVICE_PORT}'

# ACL Service
ACL_SERVICE_HOST = os.environ.get('ACL_SERVICE_HOST')
ACL_SERVICE_PORT = os.environ.get('ACL_SERVICE_PORT')
ACL_SERVICE_URL = f'http://{ACL_SERVICE_HOST}:{ACL_SERVICE_PORT}/v1/data/authz/allow'

# Wealth Management Service
WEALTH_MGMT_HOST = os.environ.get('WEALTH_MGMT_HOST')
WEALTH_MGMT_PORT = os.environ.get('WEALTH_MGMT_PORT')
WEALTH_MGMT_URL = f'http://{WEALTH_MGMT_HOST}:{WEALTH_MGMT_PORT}'

# Jaegar integration
JAEGER_AGENT_HOST = os.environ.get('JAEGER_AGENT_HOST')
JAEGER_AGENT_PORT = os.environ.get('JAEGER_AGENT_PORT')
JAEGER_SERVICE_URL = 'http://' + JAEGER_AGENT_HOST + ':' + JAEGER_AGENT_PORT

# print("SEARCH_SERVICE_URL: ", JAEGER_SERVICE_URL)

# Jaeger configuration - start
# def initialize_tracer():
#     config = Config(
#         config={
#             'sampler': {'type': 'const', 'param': 1},
#             'local_agent': {
#                 'reporting_host': JAEGER_AGENT_HOST,
#                 'reporting_port': JAEGER_AGENT_PORT,
#             },
#             'logging': True,
#         },
#         # ToCheck: offer-banner...
#         service_name="frontend",
#     )
#     return config.initialize_tracer()

# tracer = initialize_tracer()
# tracing = FlaskTracing(tracer, True, app)
# Jaeger configuration - end

# Setup tracer
tracer = setup_tracer(service_name="frontend", jaeger_host=JAEGER_AGENT_HOST, jaeger_port=int(JAEGER_AGENT_PORT))

# Instrument the app
instrument_app(app)


def check_permissions(path, method):
    username = session.get('username')
    
    if 'admin' in username:
        roles = ["admin", "user"]
    else:
        roles = ["user"]
    
    input_data = {
        "input": {
            "path": path,
            "method": method,
            "roles": roles
        }
    }

    response = requests.post(ACL_SERVICE_URL, json=input_data)
    return response.json().get('result', False)


################################### LANDING PAGE ###################################

@app.route('/', methods=['GET'])
# @tracing.trace()
def home():
    is_logged_in = 'token' in session
    username = session.get('username') if 'token' in session else None
    if not is_logged_in:
        return redirect(url_for('login'))

    banner = fetch_banners(2)

    user_info = fetch_customer_info(username) or {}

    return render_template('index.html', banner_r=banner[0], banner_l=banner[1], is_logged_in=is_logged_in, **user_info, port=SELF_PORT)

################################### WEALTH MGMT ###################################

@app.route('/wealth_mgmt', methods=['GET'])
def wealth_mgmt():
    is_logged_in = 'token' in session
    username = session.get('username') if 'token' in session else None
    if not is_logged_in:
        return redirect(url_for('login'))
    user_info = fetch_customer_info(username) or {}
    username = user_info.get('username')
    tax_info= requests.get(f"{WEALTH_MGMT_URL}/getTaxes/{username}")
    return render_template('wealth_mgmt.html', is_logged_in=is_logged_in, **user_info, tax_info=tax_info.json())
@app.route('/record_tax_payments', methods=['GET', 'POST'])
def record_tax_payments():
    username = session.get('username') if 'token' in session else None
    tax_id = request.form['tax_id']
    if not username or not tax_id:
        return 'Form data missing!', 400
    
    data = {
        'tax_id': tax_id,
        'username': username
    }
    resp = requests.post(f"{WEALTH_MGMT_URL}/payTaxes", json=data)
    if resp.status_code == 200:
        return 'Payment successful!', 200
    else:
        return f'Failed to submit form.  <br>Status Code: {resp.status_code} <br>Error: {resp.json()} Username: {username}'

################################### PAYMENTS ###################################

@app.route('/payments', methods=['GET'])
def payments():
    is_logged_in = 'token' in session
    username = session.get('username') if 'token' in session else None
    if not is_logged_in:
        return redirect(url_for('login'))
    user_info = fetch_customer_info(username) or {}
    banner = fetch_banners(3)
    return render_template('payments.html', banner1=banner[0], banner2=banner[1], banner3=banner[2], is_logged_in=is_logged_in, **user_info)

@app.route('/relay_payments', methods=['POST'])
def relay_payments():
    receiver_username = request.form['receiver_username']
    username = session.get('username') if 'token' in session else None
    account_number = request.form['account_number']
    comments = request.form['comments']
    receiver = request.form['receiver']
    amount = request.form['amount']

    if not receiver_username or not account_number or not amount or not comments or not username or not receiver:
        return 'Form data missing!', 400
    
    data = {
        'receiver_username': receiver_username,
        'username': username,
        'account_number': account_number,
        'comments':comments,
        'to': receiver,
        'amount': amount
    }

    print(f"DATA::> {data}")

    response = requests.post(f'{PAYMENTS_SERVICE_URL}/pay', json=data)

    if response.status_code == 200:
            return 'Form submitted successfully!'
    else:
        return f'Failed to submit form.  <br>Status Code: {response.status_code} <br>Error: {response.json()}'

################################### CREDIT CARD ###################################

@app.route('/creditCard', methods=['GET'])
def creditCard():
    is_logged_in = 'token' in session
    username = session.get('username') if 'token' in session else None
    if not is_logged_in:
        return redirect(url_for('login'))
    user_info = fetch_customer_info(username) or {}
    card_info = requests.get(f'{CREDIT_CARD_SERVICE_URL}/get_credit_card_info/{username}')
    banner = fetch_banners(1)
    return render_template('creditcard.html', banner=banner, is_logged_in=is_logged_in, **user_info, card_info=card_info.json())

@app.route('/generate_credit_card', methods=['POST'])
def generate_credit_card():
    balance = request.form['initial_balance']
    secret_passcode = request.form['secret_passphrase']
    username = session.get('username') if 'token' in session else None

    user_info = fetch_customer_info(username) or {}
    account_number = user_info.get('account_number')

    if not secret_passcode or not username or not account_number or not balance:
        return 'Form data missing!', 400
    
    data = {
        'username': username,
        'account_number': account_number,
        'secret_passcode': secret_passcode,
        'balance': balance,
    }

    response = requests.post(f'{CREDIT_CARD_SERVICE_URL}/generate_credit_card', json=data)

    if response.status_code == 200:
            return 'Form submitted successfully!'
    else:
        return f'Failed to submit form.  <br>Status Code: {response.status_code} <br>Error: {response.json()}'

@app.route('/deposit_funds', methods=['POST'])
def deposit_funds():
    deposit_amount = request.form['deposit_amount']
    username = session.get('username') if 'token' in session else None

    if not deposit_amount or not username:
        return 'Form data missing!', 400
    
    data = {
        'username': username,
        'deposit_amount': deposit_amount,
    }

    print(f"DATA::> {data}")

    response = requests.post(f'{CREDIT_CARD_SERVICE_URL}/deposit_funds', json=data)

    if response.status_code == 200:
            return 'Form submitted successfully!'
    else:
        return f'Failed to submit form.  <br>Status Code: {response.status_code} <br>Error: {response.json()}'

@app.route('/withdraw_funds', methods=['POST'])
def withdraw_funds():
    withdraw_amount = request.form['withdraw_amount']
    username = session.get('username') if 'token' in session else None

    if not withdraw_amount or not username:
        return 'Form data missing!', 400
    
    data = {
        'username': username,
        'withdraw_amount': withdraw_amount,
    }

    response = requests.post(f'{CREDIT_CARD_SERVICE_URL}/withdraw_funds', json=data)

    if response.status_code == 200:
            return 'Form submitted successfully!'
    else:
        return f'Failed to submit form.  <br>Status Code: {response.status_code} <br>Error: {response.json()}'

################################### ACTIVITY LOG PAGE ###################################

@app.route('/activity', methods=['GET'])
def activity():
    is_logged_in = 'token' in session
    username = session.get('username') if 'token' in session else None
    if not is_logged_in:
        return redirect(url_for('login'))
    user_info = fetch_customer_info(username) or {}
    account_number = user_info.get('account_number')
    activity_info = requests.get(f"{CUSTOMER_ACTIVITY_SERVICE_URL}/getCustomerActivity/{account_number}")
    banner = fetch_banners(1)
    return render_template('activity.html', banner=banner, is_logged_in=is_logged_in, **user_info, activity_info=activity_info.json())

@app.route('/all-activity', methods=['GET'])
def allActivity():
    is_logged_in = 'token' in session
    if not is_logged_in:
        return redirect(url_for('login'))
    if not check_permissions('all-activity', 'GET'):
        return "Unauthorized", 403
    username = session.get('username') if 'token' in session else None

    user_info = fetch_customer_info(username) or {}
    activity_info = requests.get(f"{CUSTOMER_ACTIVITY_SERVICE_URL}/getAllCustomerActivities")
    banner = fetch_banners(1)
    return render_template('allactivity.html', banner=banner, is_logged_in=is_logged_in, **user_info, activity_info=activity_info.json())

################################### DEPOSIT/WITHDRAWL PAGE ###################################

@app.route('/deposit', methods=['GET'])
def depositNWithdrawl():
    is_logged_in = 'token' in session
    username = session.get('username') if 'token' in session else None
    if not is_logged_in:
        return redirect(url_for('login'))
    user_info = fetch_customer_info(username) or {}
    banner = fetch_banners(1)
    return render_template('depositWithdraw.html', banner=banner, is_logged_in=is_logged_in, **user_info)

@app.route('/record_deposit', methods=['POST'])
def record_deposit():
    amount = request.form['deposit_amount']
    username = session.get('username') if 'token' in session else None

    if not amount or not username:
        return 'Form data missing!', 400
    
    data = {
        'username': username,
        'amount': amount,
    }

    response = requests.post(f'{DEPOSIT_WITHDRAWL_SERVICE_URL}/deposit', json=data)

    if response.status_code == 200:
            return 'Form submitted successfully!'
    else:
        return f'Failed to submit form.  <br>Status Code: {response.status_code} <br>Error: {response.json()}'

@app.route('/record_withdraw', methods=['POST'])
def record_withdraw():
    amount = request.form['withdraw_amount']
    username = session.get('username') if 'token' in session else None

    if not amount or not username:
        return 'Form data missing!', 400
    
    data = {
        'username': username,
        'amount': amount,
    }

    response = requests.post(f'{DEPOSIT_WITHDRAWL_SERVICE_URL}/withdraw', json=data)

    if response.status_code == 200:
            return 'Form submitted successfully!'
    else:
        return f'Failed to submit form.  <br>Status Code: {response.status_code} <br>Error: {response.json()}'

################################### INVESTMENT PAGE ###################################

@app.route('/investment', methods=['GET'])
# @tracing.trace()
def investment():
    is_logged_in = 'token' in session
    username = session.get('username') if 'token' in session else None
    if not is_logged_in:
        return redirect(url_for('login'))
    
    investments = requests.get(f"{INVESTMENT_SERVICE_URL}/investments/{username}")
    print(f"investments::> {investments}")
    
    return render_template('investment.html', investments=investments.json(), is_logged_in=is_logged_in)

@app.route('/record_investment', methods=['POST', "GET"])
def invest_amount():
    if request.method == 'POST':
        amount = request.form['amount']
        duration = request.form['duration']
        invested_in = request.form['invested_in']
        investment_type = request.form['investment_type']
        username = session.get('username') if 'token' in session else None

        if not duration or not amount or not invested_in or not username or not investment_type:
            return 'Form data missing!', 400

        data = {
            'username': username,
            'amount': amount,
            'duration': duration,
            'invested_in': invested_in,
            'investment_type': investment_type,
        }

        response = requests.post(f'{INVESTMENT_SERVICE_URL}/investment', json=data)

        if response.status_code == 200:
            return 'Form submitted successfully!'
        else:
            return f'Failed to submit form.  <br>Status Code: {response.status_code} <br>Error: {response.json()}'
        
    else:
        pass

@app.route('/redeem_investment', methods=['POST', "GET"])
def redeem_investment():
    if request.method == 'POST':
        amount_redeem = request.form['amount_redeem']
        investment_id = request.form['investment_id']
        username = session.get('username') if 'token' in session else None

        if not investment_id or not amount_redeem or not username:
            return 'Form data missing!', 400

        data = {
            'username': username,
            'amount_redeem': amount_redeem,
            'investment_id': investment_id,
        }

        response = requests.post(f'{INVESTMENT_SERVICE_URL}/redeem_investment', json=data)

        if response.status_code == 200:
            return 'Investment application accepted'
        else:
            return f'Failed to initiate Investment Redemption. <br>Status Code: {response.status_code} <br>Error: {response.json()}'
    else:
        pass

################################### BUSINESS LENDING PAGE ###################################

@app.route('/business_loan', methods=['GET'])
# @tracing.trace()
def business_loan():
    is_logged_in = 'token' in session
    username = session.get('username') if 'token' in session else None
    if not is_logged_in:
        return redirect(url_for('login'))
    
    bloans = requests.get(f"{BUSINESS_LENDING_SERVICE_URL}/bloans/{username}")
    print(f"bloans::> {bloans}")
    
    return render_template('bloan.html', bloans=bloans.json(), is_logged_in=is_logged_in)

@app.route('/record_business_loan', methods=['POST', "GET"])
def apply_for_business_loans():
    if request.method == 'POST':
        term = request.form['term']
        amount = request.form['amount']
        purpose = request.form['purpose']
        username = session.get('username') if 'token' in session else None

        if not term or not amount or not purpose or not username:
            return 'Form data missing!', 400

        data = {
            'username': username,
            'amount': amount,
            'term': term,
            'purpose': purpose,
        }

        response = requests.post(f'{BUSINESS_LENDING_SERVICE_URL}/apply', json=data)

        if response.status_code == 200:
            return 'Form submitted successfully!'
        else:
            return f'Failed to submit form.  <br>Status Code: {response.status_code} <br>Error: {response.json()}'
        
    else:
        pass

@app.route('/payout_business_loan', methods=['POST', "GET"])
def payout_business_loan():
    if request.method == 'POST':
        amount = request.form['amount']
        bloan_id = request.form['bloan_id']
        username = session.get('username') if 'token' in session else None

        if not bloan_id or not amount or not username:
            return 'Form data missing!', 400

        data = {
            'username': username,
            'amount': amount,
            'bloan_id': bloan_id,
        }

        response = requests.post(f'{BUSINESS_LENDING_SERVICE_URL}/pay_bloan', json=data)

        if response.status_code == 200:
            return 'Loan repayment application accepted'
        else:
            return f'Failed to initiate loan repayment.  <br>Status Code: {response.status_code} <br>Error: {response.json()}'
        
    else:
        pass

################################### PERSONAL LENDING PAGE ###################################

@app.route('/loan', methods=['GET'])
# @tracing.trace()
def loan():
    is_logged_in = 'token' in session
    username = session.get('username') if 'token' in session else None
    if not is_logged_in:
        return redirect(url_for('login'))
    
    loans = requests.get(f"{PERSONAL_LENDING_SERVICE_URL}/loans/{username}")
    print(f"loans::> {loans}")
    
    return render_template('loan.html', loans=loans.json(), is_logged_in=is_logged_in)

@app.route('/record_loan', methods=['POST', "GET"])
def apply_for_loans():
    if request.method == 'POST':
        term = request.form['term']
        amount = request.form['amount']
        purpose = request.form['purpose']
        username = session.get('username') if 'token' in session else None

        if not term or not amount or not purpose or not username:
            return 'Form data missing!', 400

        data = {
            'username': username,
            'amount': amount,
            'term': term,
            'purpose': purpose,
        }

        response = requests.post(f'{PERSONAL_LENDING_SERVICE_URL}/apply', json=data)

        if response.status_code == 200:
            return 'Form submitted successfully!'
        else:
            return f'Failed to submit form.  <br>Status Code: {response.status_code} <br>Error: {response.json()}'
        
    else:
        pass

@app.route('/payout_loan', methods=['POST', "GET"])
def payout_loan():
    if request.method == 'POST':
        amount = request.form['amount']
        loanId = request.form['loanId']
        username = session.get('username') if 'token' in session else None

        if not loanId or not amount or not username:
            return 'Form data missing!', 400

        data = {
            'username': username,
            'amount': amount,
            'loanId': loanId,
        }

        response = requests.post(f'{PERSONAL_LENDING_SERVICE_URL}/pay_loan', json=data)

        if response.status_code == 200:
            return 'Loan repayment application accepted'
        else:
            return f'Failed to initiate loan repayment.  <br>Status Code: {response.status_code} <br>Error: {response.json()}'
        
    else:
        pass

################################### MORTGAGES PAGE ###################################

@app.route('/mortgage', methods=['GET'])
# @tracing.trace()
def mortgage():
    is_logged_in = 'token' in session
    username = session.get('username') if 'token' in session else None
    if not is_logged_in:
        return redirect(url_for('login'))
    
    mortgages = requests.get(f"{MORTGAGE_SERVICE_URL}/mortgages/{username}")
    print(f"mortgage::> {mortgages}")
    
    return render_template('mortgage.html', mortgages=mortgages.json(), is_logged_in=is_logged_in)

@app.route('/record_mortgage', methods=['POST', "GET"])
def apply_for_mortgage():
    if request.method == 'POST':
        term = request.form['term']
        amount = request.form['amount']
        purpose = request.form['purpose']
        down_payment = request.form['down_payment']
        property_value = request.form['property_value']
        username = session.get('username') if 'token' in session else None

        if not term or not amount or not purpose or not username:
            return 'Form data missing!', 400

        data = {
            'term': term,
            'amount': amount,
            'purpose': purpose,
            'username': username,
            'down_payment': down_payment,
            'property_value': property_value,
        }

        response = requests.post(f'{MORTGAGE_SERVICE_URL}/apply_mortgage', json=data)

        if response.status_code == 200:
            return 'MORTGAGE Form submitted successfully!'
        else:
            return f'Failed to submit form.  <br>Status Code: {response.status_code} <br>Error: {response.json()}'
        
    else:
        pass

@app.route('/payout_mortgage', methods=['POST', "GET"])
def payout_mortgage():
    if request.method == 'POST':
        pay_amount = request.form['pay_amount']
        mortgage_id = request.form['mortgage_id']
        username = session.get('username') if 'token' in session else None

        if not pay_amount or not mortgage_id or not username:
            return 'Form data missing!', 400

        data = {
            'username': username,
            'amount': pay_amount,
            'mortgage_id': mortgage_id,
        }

        response = requests.post(f'{MORTGAGE_SERVICE_URL}/pay_mortgage', json=data)

        if response.status_code == 200:
            return 'Morgage repayment application accepted'
        else:
            return f'Failed to initiate loan repayment. \nStatus Code: {response.status_code} \nError: {response.json()}'
        
    else:
        pass

################################ ACCESS MANAGEMENT ################################

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        response = requests.post(f'{AUTH_SERVICE_URL}/login', json={'username': username, 'password': password})
        if response.status_code == 200:
            session['token'] = response.json()['token']
            session['username'] = response.json()['username']
            print("RESPONSE::>", response.json())
            return redirect(url_for('home'))
            # redirect(url_for('home'))
            # return response.content
        else:
            flash('Login failed. Check your username and password.')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        name = request.form['name']
        email = request.form['email']
        contact = request.form['contact']
        address = request.form['address']

        response = requests.post(
            f'{AUTH_SERVICE_URL}/register', 
            json={ 
                'username': username, 
                'password': password,
                'name': name, 
                'email': email, 
                'contact': contact, 
                'address': address 
            })
        
        if response.status_code == 200:
            flash('Registered successfully. Please log in.')
            return redirect(url_for('login'))
        else:
            flash('Username already exists.')
    return render_template('signup.html')

@app.route('/logout')
def logout():
    token = session.pop('token', None)
    if token:
        requests.post(f'{AUTH_SERVICE_URL}/logout', headers={'Authorization': token})
        session.clear() 
    return redirect(url_for('login'))

# ======================================================================================================================================================================================== #

##################################### CONTACT  ####################################

@app.route('/contact', methods=['GET'])
def contact():
    is_logged_in = 'token' in session
    banner = fetch_banners(2)

    try:
        response = requests.get(f'{CONTACT_SERVICE_URL}/getContacts')
        response.raise_for_status()  # Raises an HTTPError for bad responses
        contacts = response.json()
    except requests.RequestException as e:
        print(f"Error fetching contacts: {e}")
        contacts = []

    tollfree_contact = next((contact for contact in contacts if contact['region_id'] == 'tollfree'), None)
    overseas_contact = next((contact for contact in contacts if contact['region_id'] == 'overseas'), None)
    regional_contact = [contact for contact in contacts if contact['region_id'] not in ['tollfree', 'overseas']]

    try:
        response = requests.get(f'{CONTACT_SERVICE_URL}/getFaqs')
        response.raise_for_status()
        faqs = response.json()
    except requests.RequestException as e:
        print(f"Error fetching FAQs: {e}")
        faqs = []

    categories = {}
    for item in faqs:
        category = item['category']
        if category not in categories:
            categories[category] = []
        categories[category].append(item)

    return render_template('contact.html', 
                           banner_r=banner[0], 
                           banner_l=banner[1], 
                           tollfree=tollfree_contact, 
                           overseas=overseas_contact, 
                           contacts=regional_contact, 
                           categories=categories, 
                           is_logged_in=is_logged_in
                           )

# ======================================================================================================================================================================================== #

##################################### INPUT/OUTPUT ####################################
@app.route('/record_conv', methods=['POST', "GET"])
# @tracing.trace()
def record_conv():
    if request.method == 'POST':
        # Capturing form data
        name = request.form['name']
        email = request.form['email']
        message = request.form['message']

        print("Received form data:")
        print(f"Name: {name}, Email: {email}, Message: {message}")

        if not name or not email or not message:
            return 'Form data missing!', 400

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
        if response.status_code == 201:
            return 'Form submitted successfully!'
        else:
            return 'Failed to submit form.', response.status_code
    else:
        pass

@app.route('/search_results', methods=['POST'])
# @tracing.trace()
def search_results():
    # if request.method == 'POST':
    # Capturing Form data
    print("++++Entered search_results++++")
    print("Form Request", request.form)
    prompt = request.form['prompt']
    print("++++Noted Prompt++++")
    if not prompt:
        return 'Form data missing! - Prompt'#, 400
    data = {
        'prompt': prompt,
    }
    response = requests.post(f'{SEARCH_SERVICE_URL}/getIndex', json=data)
    offer_banner = fetch_banners(2)
    source = response.json().get('source')
    index_data = response.json().get('data')
    return render_template('index_page.html', data=index_data, prompt=prompt, source=source, banner_l=offer_banner[0], banner_r=offer_banner[1])

# ======================================================================================================================================================================================== #

##################################### ADS ####################################
@app.route('/setOfferBanner', methods=['POST'])
# @tracing.trace()
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
# @tracing.trace()
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

# ======================================================================================================================================================================================== #

##################################### HELPER FN ####################################
def fetch_banners(num_outputs):
    response = requests.get(f'{ADS_SERVICE_URL}/getAds')
    
    if response.status_code != 200:
        return [None] * num_outputs  # Return a list of None if the request fails
    
    ads = response.json()
    banners = [get_offer_banner(list(ads.keys())) for _ in range(num_outputs)]
    
    return [ads[banner] if banner else None for banner in banners]

def fetch_customer_info(username):
    response = requests.get(f'{CUSTOMER_INFO_SERVICE_URL}/getCustomerInfo/{username}')

    if response.status_code != 200:
        return None

    customer_data = response.json()

    user_info = {
        "username": customer_data.get("username", ""),
        "name": customer_data.get("name", ""),
        "acc_balance": customer_data.get("acc_balance", "0"),
        "dmat_balance": customer_data.get("dmat_balance", "0"),
        "account_number": customer_data.get("account_number", ""),
        "credit_card": customer_data.get("credit_card", ""),
        "email": customer_data.get("email", ""),
        "contact_no": customer_data.get("contact_no", ""),
        "address": customer_data.get("address", ""),
        "customer_pic_url": customer_data.get("customer_pic_url", "https://imgs.search.brave.com/QZ3mtUm8nZzRX-Ru5cyHaCL5eBj9vXxTOz81T5eq1Ao/rs:fit:860:0:0:0/g:ce/aHR0cHM6Ly93d3cu/cG5naXRlbS5jb20v/cGltZ3MvbS81MDQt/NTA0MDUyOF9lbXB0/eS1wcm9maWxlLXBp/Y3R1cmUtcG5nLXRy/YW5zcGFyZW50LXBu/Zy5wbmc"),
    }

    return user_info

def fetch_credit_card_info(username):
    response = requests.get(f'{CREDIT_CARD_SERVICE_URL}/get_credit_card_info/{username}')

    if response.status_code != 200:
        return None

    card_data = response.json()

    card_info = {
        "username": card_data.get("username", ""),
        "account_number": card_data.get("account_number", ""),
        "credit_card": card_data.get("credit_card", ""),
        "balance": card_data.get("balance", ""),
    }

    return card_info

def get_offer_banner(banner_list):
    if not banner_list:
        return None
    random_banner = random.choice(banner_list)
    return random_banner

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=SELF_PORT, debug=True)
