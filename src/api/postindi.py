import json
import requests

url = 'http://localhost:5003/clearContacts'

def read_json_file(file_path):
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
            return data
    except FileNotFoundError:
        print(f"Error: The file {file_path} does not exist.")
    except PermissionError:
        print(f"Error: You do not have permission to read the file {file_path}.")
    except json.JSONDecodeError as e:
        print(f"Error: Failed to decode JSON from the file {file_path}. Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred while reading the file {file_path}. Error: {e}")
    return None

# data = read_json_file(file)
# if data is not None:
#     for i in data:
#         response = requests.post(url, json=i)
#         if response.status_code == 200:
#             print(f"Successfully updated data for {file} at {url}")
#         else:
#             print(f"Failed to update data for {file} at {url}. Status code: {response.status_code}")
# else:
#     print(f"No data to update for {file} at {url}")

try:
    response = requests.post(url)
    if response.status_code == 200:
        print("Contacts collection cleared successfully.")
    else:
        print("Failed to clear contacts collection. Status code:", response.status_code)
except requests.exceptions.RequestException as e:
    print("Error:", e)