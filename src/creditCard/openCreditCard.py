"""
Check if account is legit:
* Requirement:
    - Account no.
    - Secret Passcode
    - DOB

If Account exist then check for validity of security code. If everything passes then generate a 16 digit long credit card no. derived from Debit card number via hashing stc.
"""

import sqlite3
import hashlib

def generate_credit_card_number(debit_card_number):
    hashed_twice = hashlib.sha256(str(debit_card_number).encode()).hexdigest()
    credit_card_number = int(hashed_twice, 16) % (10 ** 16)
    return credit_card_number

def update_credit_card_number(account_number, new_credit_card_number):
    # Connect to the SQLite database
    conn = sqlite3.connect('accounts.db')
    c = conn.cursor()

    # Update credit card number in the database
    c.execute("UPDATE accounts SET Credit_Card_Number=? WHERE Account_Number=?", (new_credit_card_number, account_number))
    conn.commit()
    conn.close()

def check_account_legitimacy(account_number, secret_passcode, dob):
    conn = sqlite3.connect('accounts.db')
    c = conn.cursor()

    c.execute("SELECT * FROM accounts WHERE Account_Number=?", (account_number,))
    account_data = c.fetchone()

    if not account_data:
        print("Account not found.")
        return None
    if account_data[2] != 0:
        print("Credit Card already exist")
        return None
    # Validate secret passcode and DOB
    if account_data[9][::-1] != secret_passcode:
        print("Invalid secret passcode.")
        return None
    if account_data[5] != dob:
        print("Invalid date of birth.")
        return None

    # Generate credit card number
    debit_card_number = account_data[1]
    credit_card_number = generate_credit_card_number(debit_card_number)
    update_credit_card_number(account_number, credit_card_number)

    return credit_card_number

account_number = input("Enter account number: ")
secret_passcode = input("Enter secret passcode: ")
dob = input("Enter date of birth (YYYY-MM-DD): ")

credit_card_number = check_account_legitimacy(account_number, secret_passcode, dob)
if credit_card_number:
    print("Your credit card number is:", credit_card_number)

# # Example usage:
# account_number = 57723026892501
# secret_passcode = "jGXPmWtH"
# dob = "1990-01-01"