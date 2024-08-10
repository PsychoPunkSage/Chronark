# 1. Clear all the data in DB
#   - UserLogin Data (authentication MS)
#   - Customer Info Data (customerInfo MS)
# 2. Make POST request to signup all the users (default = 10)
import requests

default_users = 10
api_link = 'http://localhost:5005/register' # Add users

# Clear Data
login_data = 'http://localhost:5005/clearData'
customerInfo_data = 'http://localhost:5006/clearData'

def cleanup():
    urls = [login_data, customerInfo_data]
    for url in urls:
        try:
            response = requests.post(url)
            if response.status_code == 200:
                print(f"{url} collection cleared successfully.")
            else:
                print(f"Failed to clear {url} collection. Status code:", response.status_code)
        except requests.exceptions.RequestException as e:
            print(f"Error({url}): {e}")

def add_users():
    sample_users = [
        {
            "username": f"user{i}",
            "password": f"user{i}",
            "name": f"User {i}",
            "email": f"user{i}@example.com",
            "contact": f"+91 98765432{i:02d}",
            "address": f"{i}00 Main St, Anytown, AnyState"
        } for i in range(1, default_users + 1)
    ]

    for user in sample_users:
        try:
            response = requests.post(api_link, json=user)
            if response.status_code == 200:
                print(f"User {user['username']} registered successfully.")
            else:
                print(f"Failed to register user {user['username']}. Status code: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Error registering user {user['username']}: {e}")

cleanup()
add_users()