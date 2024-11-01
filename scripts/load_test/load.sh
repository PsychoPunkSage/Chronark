#!/bin/bash

# URLs for the API endpoints
login_data="http://localhost:5005/clearData"
customerInfo_data="http://localhost:5006/clearData"
register_url="http://localhost:5005/register"

# Default number of users to add
default_users=10

# Function to clear data for each username
cleanup() {
  usernames=("$@")
  for username in "${usernames[@]}"; do
    for url in "$login_data" "$customerInfo_data"; do
      response=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$url" -H "Content-Type: application/json" -d "{\"username\": \"$username\"}")
      if [ "$response" -eq 200 ]; then
        echo "Data for username '$username' cleared successfully at $url."
      elif [ "$response" -eq 404 ]; then
        echo "No data found for username '$username' at $url."
      else
        echo "Failed to clear data for username '$username' at $url. Status code: $response"
      fi
    done
  done
}

# Function to add users
add_users() {
  num_users=${1:-$default_users}
  for ((i = 11; i < 11 + num_users; i++)); do
    user_data=$(jq -n \
      --arg username "user$i" \
      --arg password "user$i" \
      --arg name "User $i" \
      --arg email "user$i@example.com" \
      --arg contact "+91 98765432$(printf "%02d" $i)" \
      --arg address "$i-00 Main St, Anytown, AnyState" \
      '{username: $username, password: $password, name: $name, email: $email, contact: $contact, address: $address}')
    
    response=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$register_url" -H "Content-Type: application/json" -d "$user_data")
    if [ "$response" -eq 200 ]; then
      echo "User user$i registered successfully."
    else
      echo "Failed to register user user$i. Status code: $response"
    fi
  done
}

# Main script to handle flags
while [[ "$#" -gt 0 ]]; do
  case $1 in
    --refresh)
      shift
      cleanup "$@"
      exit 0
      ;;
    --load)
      shift
      num_users=${1:-$default_users}
      add_users "$num_users"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 [--refresh <usernames...>] [--load <number_of_users>]"
      exit 1
      ;;
  esac
done
