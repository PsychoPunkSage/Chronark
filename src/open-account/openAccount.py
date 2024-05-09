"""
Requirements:
- Name
- DOB
- Mobile No.
- email-Id
- Address
- PanCard number
- Initial Bank Balance

Output:
- account number
"""

import re
import random
import hashlib
import sqlite3
import string

def double_sha256(input_string):
    hash_object = hashlib.sha256(input_string.encode())
    hashed_once = hash_object.digest()
    hash_object = hashlib.sha256(hashed_once)
    hashed_twice = hash_object.hexdigest()
    return hashed_twice

def _validate_dob(dob):
    # DOB format : YYYY-MM-DD
    dob_pattern = re.compile(r'\d{4}-\d{2}-\d{2}')
    return dob_pattern.match(dob)

def _validate_mobile_no(mobile_no):
    # mobile number: 10 digits
    mobile_pattern = re.compile(r'^\d{10}$')
    return mobile_pattern.match(mobile_no)

def _validate_pan_card(pan_card):
    # PAN card number: alphanumeric: 10 characters <5 letters - 4 digits - 1 letter>
    pan_pattern = re.compile(r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$')
    return pan_pattern.match(pan_card)

def _validate_email(email):
    email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    return email_pattern.match(email)

def create_table():
    conn = sqlite3.connect('accounts.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS accounts
                 (Account_Number INTEGER, Debit_Card_Number INTEGER, Credit_Card_Number INTEGER, Pan_Card TEXT, Name TEXT, DOB TEXT, Mobile Number TEXT, Email TEXT, Address TEXT, Security_Code TEXT)''')
    conn.commit()
    conn.close()

def open_account(name, dob, mobile_no, pan_card, email, address):
    # verification Steps....

    # create Account number
    input_string = f"{name}{dob}{mobile_no}{pan_card}{email}"
    hashed_twice = double_sha256(input_string)
    # 16 digits
    account_number = int(hashed_twice, 16) % (10 ** 14)
    debit_card_num = random.randint(10**15, (10**16)-1)
    secretcode = ''.join(random.choices(string.ascii_letters + string.digits, k=8))

    conn = sqlite3.connect('accounts.db')
    c = conn.cursor()
    c.execute("INSERT INTO accounts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
              (account_number, debit_card_num, 0, pan_card, name, dob, mobile_no, email, address, secretcode[::-1]))
    conn.commit()
    conn.close()
    
    print("Account opened successfully!")
    print("Your account number is:", account_number)
    print("Your Debit Card number is:", debit_card_num)
    print("Your Security Code number is:", secretcode)
    return True

def get_valid_input(prompt, validator):
    while True:
        value = input(prompt)
        if validator(value):
            return value
        print("Invalid input. Please try again.")

create_table()

# name = get_valid_input("Enter your name: ", lambda x: len(x) > 0)
# dob = get_valid_input("Enter your date of birth (YYYY-MM-DD): ", _validate_dob)
# mobile_no = get_valid_input("Enter your mobile number: ", _validate_mobile_no)
# email = get_valid_input("Enter your Email: ", _validate_email)
# address = get_valid_input("Enter your address: ", lambda x: len(x) > 0)
# pan_card = get_valid_input("Enter your PAN card number: ", _validate_pan_card)
name="John Doe"
dob="1990-01-01"
mobile_no="1234567890"
pan_card="ABCDE1234F"
email="john.doe@example.com"
address="123 Main St, City, Country"

open_account(name, dob, mobile_no, pan_card, email, address)