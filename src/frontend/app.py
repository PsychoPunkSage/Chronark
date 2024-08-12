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
PERSONAL_LENDING_SERVICE_HOST = os.environ.get('CUSTOMER_INFO_SERVICE_HOST')
PERSONAL_LENDING_SERVICE_PORT = os.environ.get('CUSTOMER_INFO_SERVICE_PORT')
PERSONAL_LENDING_SERVICE_URL = f'http://{PERSONAL_LENDING_SERVICE_HOST}:{PERSONAL_LENDING_SERVICE_PORT}'

# Jaegar integration
JAEGER_AGENT_HOST = os.environ.get('JAEGER_AGENT_HOST')
JAEGER_AGENT_PORT = os.environ.get('JAEGER_AGENT_PORT')

JAEGER_SERVICE_URL = 'http://' + JAEGER_AGENT_HOST + ':' + JAEGER_AGENT_PORT
print("SEARCH_SERVICE_URL: ", JAEGER_SERVICE_URL)

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

################################### LANDING PAGE ###################################

@app.route('/', methods=['GET'])
# @tracing.trace()
def home():
    is_logged_in = 'token' in session
    username = session.get('username') if 'token' in session else None
    if not is_logged_in:
        return redirect(url_for('login'))

    response = requests.get(f'{ADS_SERVICE_URL}/getAds')
    ads = response.json()
    banner_id = get_offer_banner(list(ads.keys()))
    if banner_id is not None:
        banner = ads[banner_id]
    else:
        banner = None

    user_info = fetch_customer_info(username) or {}

    return render_template('index.html', banner=banner, is_logged_in=is_logged_in, **user_info)

################################### LANDING PAGE ###################################

@app.route('/loan', methods=['GET'])
# @tracing.trace()
def loan():
    is_logged_in = 'token' in session
    username = session.get('username') if 'token' in session else None
    if not is_logged_in:
        return redirect(url_for('login'))
    
    loans = requests.get(f"{PERSONAL_LENDING_SERVICE_URL}/loans/{username}")

    # if loans.status_code != 200:
    #     return render_template('loan.html', loans=loans)
    
    return render_template('loan.html', loans=loans)

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
    return redirect(url_for('login'))

# ======================================================================================================================================================================================== #

##################################### CONTACT  ####################################

@app.route('/contact', methods=['GET'])
# @tracing.trace()
def contact():
    # response = requests.get(f'{ADS_SERVICE_URL}/getAds')
    # ads = response.json()
    # banners = [get_offer_banner(list(ads.keys())) for _ in range(2)]
    # if all(banners):
    #     banner_r, banner_l = (ads[banners[0]], ads[banners[1]])
    # else:
    #     banner_r = banner_l = None
    banner = fetch_banners(2)

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

    return render_template('contact.html', banner_r=banner[0], banner_l=banner[1], tollfree=tollfree_contact, overseas=overseas_contact, contacts=regional_contact, categories=categories )

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
        if response.status_code == 200:
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
        "email": customer_data.get("email", ""),
        "contact_no": customer_data.get("contact_no", ""),
        "address": customer_data.get("address", ""),
        "customer_pic_url": customer_data.get("customer_pic_url", "https://imgs.search.brave.com/QZ3mtUm8nZzRX-Ru5cyHaCL5eBj9vXxTOz81T5eq1Ao/rs:fit:860:0:0:0/g:ce/aHR0cHM6Ly93d3cu/cG5naXRlbS5jb20v/cGltZ3MvbS81MDQt/NTA0MDUyOF9lbXB0/eS1wcm9maWxlLXBp/Y3R1cmUtcG5nLXRy/YW5zcGFyZW50LXBu/Zy5wbmc"),
    }

    return user_info
    




































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
