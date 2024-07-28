import os
import requests

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your_super_complex_secret_key_here')

SELF_PORT = os.environ.get('SELF_PORT')

AUTH_SERVICE_HOST = os.environ.get('AUTH_SERVICE_HOST')
AUTH_SERVICE_PORT = os.environ.get('AUTH_SERVICE_PORT')
AUTH_SERVICE_URL = 'http://' + AUTH_SERVICE_HOST + ':' + AUTH_SERVICE_PORT

@app.route('/')
def index():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    response = requests.post(f'{AUTH_SERVICE_URL}/login', json={'username': username, 'password': password})
    
    if response.status_code == 200:
        token = response.json().get('token')
        flash('Logged in successfully!', 'success')
        # You can set the token in cookies or session here
        # For example: session['token'] = token
        return redirect(url_for('protected'))
    else:
        flash(response.json().get('message', 'Login failed!'), 'danger')
        return redirect(url_for('index'))

@app.route('/protected')
def protected():
    # You can use the token stored in cookies or session to access protected routes
    # For simplicity, we just show a message here
    return 'This is a protected page.'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5006, debug=True)
