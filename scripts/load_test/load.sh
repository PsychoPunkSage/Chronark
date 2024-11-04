#!/bin/bash

# URLs for the API endpoints
login_data="http://localhost:5005/clearData"
customerInfo_data="http://localhost:5006/clearData"
register_url="http://localhost:5005/register"
# register_url="http://localhost:80/signup"
login_link="http://localhost:80/login" # Login endpoint via load balancer
logout_link="http://localhost:80/logout" # Login endpoint via load balancer

# Default number of users to add
default_users=10

# cookie folder for each user login
mkdir -p cookie

# Function to clear data for each username
cleanup() {
  start_index=$1
  end_index=$2
  for ((i = start_index; i < end_index; i++)); do
    username="user$i"

    (
      # Logout user
      logout_user "$username" # for testing USERNAME == PASSWORD

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
    )&
  done

  wait
  echo "Cleanup completed for users from $start_index to $((end_index - 1))."
}

login_user() {
  username=$1
  password=$2
  cookie_file="cookie/cookies_$username.txt"

  echo "username: $username || password: $password"

  login_response=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$login_link" \
    -d "username=$username&password=$password" --cookie-jar "$cookie_file")
  if [ "$login_response" -eq 200 ] || [ "$login_response" -eq 302 ]; then
    echo "User $username logged IN successfully. Cookies saved in $cookie_file."
  else
    echo "Failed to log-in user $username. Status code: $login_response"
  fi
}

logout_user() {
  username=$1
  cookie_file="cookie/cookies_$username.txt"
  logout_response=$(curl -s -o /dev/null -w "%{http_code}" -L "$logout_link" \
    --cookie "$cookie_file" --cookie-jar "$cookie_file")
  if [ "$logout_response" -eq 200 ]; then
    echo "User $username logged OUT successfully. Cookies saved in $cookie_file."
  else
    echo "Failed to log-out user $username. Status code: $logout_response"
  fi
}

# SYNC WAY
# add_users() {
#   default_users=${1:-10}
#   for ((i = 11; i < 11 + default_users; i++)); do
#     username="user$i"
#     password="user$i"
#     user_data=$(jq -n --arg username "$username" --arg password "$password" \
#       --arg name "User $i" --arg email "$username@example.com" \
#       --arg contact "+91 98765432$(printf '%02d' $i)" \
#       --arg address "${i}00 Main St, Anytown, AnyState" \
#       '{username: $username, password: $password, name: $name, email: $email, contact: $contact, address: $address}')
    
#     # Register user
#     register_response=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$register_url" -H "Content-Type: application/json" -d "$user_data")
#     if [ "$register_response" -eq 200 ]; then
#       echo "User $username registered successfully."
      
#       # Login user (after registration)
#       login_user "$username" "$password"
#     else
#       echo "Failed to register user $username. Status code: $register_response"
#     fi
#   done
# }

# ASYNC WAY
add_users() {
  default_users=${1:-10}
  
  for ((i = 11; i < 11 + default_users; i++)); do
    username="user$i"
    password="user$i"
    user_data=$(jq -n --arg username "$username" --arg password "$password" \
      --arg name "User $i" --arg email "$username@example.com" \
      --arg contact "+91 98765432$(printf '%02d' $i)" \
      --arg address "${i}00 Main St, Anytown, AnyState" \
      '{username: $username, password: $password, name: $name, email: $email, contact: $contact, address: $address}')

    # Register user in the background
    (
      register_response=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$register_url" -H "Content-Type: application/json" -d "$user_data")
      if [ "$register_response" -eq 200 ]; then
        echo "User $username registered successfully."
        
        # Login user (after registration) in the background
        login_user "$username" "$password"
      else
        echo "Failed to register user $username. Status code: $register_response"
      fi
    ) &
  done

  # Wait for all background processes to complete
  wait
  echo "All users registered and logged in concurrently."
}

# Main script to handle flags
while [[ "$#" -gt 0 ]]; do
  case $1 in
    --refresh)
      shift
      cleanup "$@"
      rm -rf ./cookie
      exit 0
      ;;
    --login)
      shift
      login_user "$@"
      exit 0
      ;;
    --logout)
      shift
      logout_user "$@"
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
