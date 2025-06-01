# import json
# import requests
# import os
# import urllib3

# # Disable SSL warnings since we're using self-signed certificates
# urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# # Read URLs from environment variables (with fallbacks for local testing)
# url_offer_banner = os.getenv('OFFER_URL', 'http://localhost:5002/setOfferBanner')
# url_bank_contacts = os.getenv('CONTACTS_URL', 'https://localhost:5003/updateContacts')
# url_faq = os.getenv('FAQ_URL', 'https://localhost:5003/updateFaqs')
# url_index = os.getenv('INDEX_URL', 'http://localhost:5004/updateIndex')

# # files
# offer_banner = 'ads.json'
# bank_contacts = 'bank_contacts.json'
# faq = 'faq.json'
# index = 'index_search.json'

# pairs = {
#     url_offer_banner: offer_banner,
#     url_bank_contacts: bank_contacts,
#     url_faq: faq,
#     url_index: index
# }

# def read_json_file(file_path):
#     try:
#         with open(file_path, 'r') as file:
#             data = json.load(file)
#             return data
#     except FileNotFoundError:
#         print(f"Error: The file {file_path} does not exist.")
#     except PermissionError:
#         print(f"Error: You do not have permission to read the file {file_path}.")
#     except json.JSONDecodeError as e:
#         print(f"Error: Failed to decode JSON from the file {file_path}. Error: {e}")
#     except Exception as e:
#         print(f"An unexpected error occurred while reading the file {file_path}. Error: {e}")
#     return None

# for url, file in pairs.items():
#     data = read_json_file(file)
#     if data is not None:
#         for i in data:
#             try:
#                 # Disable SSL verification for HTTPS requests to contacts service
#                 verify_ssl = not url.startswith('https://')
#                 response = requests.post(url, json=i, verify=verify_ssl, timeout=30)
                
#                 if response.status_code == 200:
#                     print(f"Successfully updated data for {file} at {url}")
#                 else:
#                     try:
#                         error_message = response.json()
#                     except ValueError:
#                         error_message = response.text
#                     print(f"Failed to update data for {file} at {url}. Status code: {response.status_code}. Status Message: {error_message}")
#             except requests.exceptions.RequestException as e:
#                 print(f"Request failed for {file} at {url}: {e}")
#     else:
#         print(f"No data to update for {file} at {url}")

# print("Data upload process completed!")

import json
import requests
import httpx
import os
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Your existing URLs
url_offer_banner = os.getenv('OFFER_URL', 'http://ms-offer-banner:5002/updateAd')
url_bank_contacts = os.getenv('CONTACTS_URL', 'https://ms-contacts:5003/updateContacts')
url_faq = os.getenv('FAQ_URL', 'https://ms-contacts:5003/updateFaqs')
url_index = os.getenv('INDEX_URL', 'http://ms-search:5004/updateIndex')

# Files
offer_banner = 'ads.json'
bank_contacts = 'bank_contacts.json'
faq = 'faq.json'
index = 'index_search.json'

pairs = {
    url_offer_banner: offer_banner,
    url_bank_contacts: bank_contacts,
    url_faq: faq,
    url_index: index
}

def read_json_file(file_path):
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
            return data
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
    return None

# Create HTTP/2 client for contacts service
http2_client = httpx.Client(http2=True, verify=False)

for url, file in pairs.items():
    data = read_json_file(file)
    if data is not None:
        for i in data:
            try:
                # Use HTTP/2 client for contacts service, regular requests for others
                if 'ms-contacts' in url:
                    response = http2_client.post(url, json=i, timeout=30)
                    status_code = response.status_code
                    response_text = response.text
                else:
                    response = requests.post(url, json=i, verify=False, timeout=30)
                    status_code = response.status_code
                    response_text = response.text
                
                if status_code == 200:
                    print(f"Successfully updated data for {file} at {url}")
                else:
                    print(f"Failed to update data for {file} at {url}. Status code: {status_code}")
                    
            except Exception as e:
                print(f"Request failed for {file} at {url}: {e}")
    else:
        print(f"No data to update for {file} at {url}")

# Close the HTTP/2 client
http2_client.close()
print("Data upload process completed!")