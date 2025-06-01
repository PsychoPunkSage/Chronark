#!/bin/bash

# # URLs for the API endpoints
# login_data="http://localhost:5005/clearData"
# customerInfo_data="http://localhost:5006/clearData"
# register_url="http://localhost:5005/register"
# # register_url="http://localhost:80/signup"
# login_link="http://localhost:80/login" # Login endpoint via load balancer
# logout_link="http://localhost:80/logout" # Login endpoint via load balancer

# # Default number of users to add
# default_users=10

# # cookie folder for each user login
# mkdir -p cookie

# # Function to clear data for each username
# cleanup() {
#   start_index=$1
#   end_index=$2
#   for ((i = start_index; i < end_index; i++)); do
#     username="user$i"

#     (
#       # Logout user
#       logout_user "$username" # for testing USERNAME == PASSWORD

#       for url in "$login_data" "$customerInfo_data"; do
#         response=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$url" -H "Content-Type: application/json" -d "{\"username\": \"$username\"}")
#         if [ "$response" -eq 200 ]; then
#           echo "[CLEANUP][+]  Data for username '$username' cleared successfully at $url."
#         elif [ "$response" -eq 404 ]; then
#           echo "[CLEANUP][?]  No data found for username '$username' at $url."
#         else
#           echo "[CLEANUP][-]  Failed to clear data for username '$username' at $url. Status code: $response"
#         fi
#       done
#     )&
#   done

#   wait
#   echo "================================================================"
#   echo "Cleanup completed for users from $start_index to $((end_index - 1))."
#   echo "================================================================"
# }

# login_user() {
#   username=$1
#   password=$2
#   cookie_file="cookie/cookies_$username.txt"

#   login_response=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$login_link" \
#     -d "username=$username&password=$password" --cookie-jar "$cookie_file")
#   if [ "$login_response" -eq 200 ] || [ "$login_response" -eq 302 ]; then
#     echo "[LOGIN][+]     User $username logged IN successfully. Cookies saved in $cookie_file."
#   else
#     echo "[LOGIN][-]     Failed to log-in user $username. Status code: $login_response"
#   fi
# }

# logout_user() {
#   username=$1
#   cookie_file="cookie/cookies_$username.txt"
#   logout_response=$(curl -s -o /dev/null -w "%{http_code}" -L "$logout_link" \
#     --cookie "$cookie_file" --cookie-jar "$cookie_file")
#   if [ "$logout_response" -eq 200 ]; then
#     echo "[LOGOUT][+]   User $username logged OUT successfully. Cookies saved in $cookie_file."
#   else
#     echo "[LOGOUT][-]   Failed to log-out user $username. Status code: $logout_response"
#   fi
# }

# # SYNC WAY
# # add_users() {
# #   default_users=${1:-10}
# #   for ((i = 11; i < 11 + default_users; i++)); do
# #     username="user$i"
# #     password="user$i"
# #     user_data=$(jq -n --arg username "$username" --arg password "$password" \
# #       --arg name "User $i" --arg email "$username@example.com" \
# #       --arg contact "+91 98765432$(printf '%02d' $i)" \
# #       --arg address "${i}00 Main St, Anytown, AnyState" \
# #       '{username: $username, password: $password, name: $name, email: $email, contact: $contact, address: $address}')
    
# #     # Register user
# #     register_response=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$register_url" -H "Content-Type: application/json" -d "$user_data")
# #     if [ "$register_response" -eq 200 ]; then
# #       echo "User $username registered successfully."
      
# #       # Login user (after registration)
# #       login_user "$username" "$password"
# #     else
# #       echo "Failed to register user $username. Status code: $register_response"
# #     fi
# #   done
# # }

# # ASYNC WAY
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

#     # Register user in the background
#     (
#       register_response=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$register_url" -H "Content-Type: application/json" -d "$user_data")
#       if [ "$register_response" -eq 200 ]; then
#         echo "[REGISTER][+]  User $username registered successfully."
        
#         # Login user (after registration) in the background
#         login_user "$username" "$password"
#       else
#         echo "[REGISTER][-]  Failed to register user $username. Status code: $register_response"
#       fi
#     ) &
#   done

#   # Wait for all background processes to complete
#   wait
#   echo "================================================"
#   echo "All users registered and logged in concurrently."
#   echo "================================================"
# }

# # Main script to handle flags
# while [[ "$#" -gt 0 ]]; do
#   case $1 in
#     --refresh)
#       shift
#       cleanup "$@"
#       rm -rf ./cookie
#       exit 0
#       ;;
#     --login)
#       shift
#       login_user "$@"
#       exit 0
#       ;;
#     --logout)
#       shift
#       logout_user "$@"
#       exit 0
#       ;;
#     --load)
#       shift
#       num_users=${1:-$default_users}
#       add_users "$num_users"
#       exit 0
#       ;;
#     *)
#       echo "Unknown option: $1"
#       echo "Usage: $0 [--refresh <usernames...>] [--load <number_of_users>]"
#       exit 1
#       ;;
#   esac
# done

# Default configuration
DEFAULT_MANAGER_IP="localhost"
MANAGER_IP=""
USE_LOAD_BALANCER=true  # Set to false to test services directly

# # Parse IP argument if provided
# for arg in "$@"; do
#     case $arg in
#         --ip=*)
#             MANAGER_IP="${arg#*=}"
#             ;;
#         --ip)
#             # Next argument should be the IP
#             shift
#             MANAGER_IP="$1"
#             ;;
#     esac
# done

# Parse IP argument if provided
TEMP_ARGS=()
while [ $# -gt 0 ]; do
    case $1 in
        --ip=*)
            MANAGER_IP="${1#*=}"
            shift
            ;;
        --ip)
            MANAGER_IP="$2"
            shift 2
            ;;
        *)
            TEMP_ARGS+=("$1")
            shift
            ;;
    esac
done

# Restore arguments without --ip
set -- "${TEMP_ARGS[@]}"

# Use default IP if none provided
if [ -z "$MANAGER_IP" ]; then
    echo "HERE"
    MANAGER_IP="$DEFAULT_MANAGER_IP"
fi

# URLs for the API endpoints
if [ "$USE_LOAD_BALANCER" = true ]; then
    BASE_URL="http://$MANAGER_IP:80"
    login_data="http://$MANAGER_IP:5005/clearData"
    customerInfo_data="http://$MANAGER_IP:5006/clearData"
    register_url="http://$MANAGER_IP:5005/register"
    login_link="$BASE_URL/login"
    logout_link="$BASE_URL/logout"
else
    # Direct service access
    login_data="http://$MANAGER_IP:5005/clearData"
    customerInfo_data="http://$MANAGER_IP:5006/clearData"
    register_url="http://$MANAGER_IP:5005/register"
    login_link="http://$MANAGER_IP:5005/login"  # Direct to auth service
    logout_link="http://$MANAGER_IP:5005/logout"
fi

# Default number of users to add
default_users=10

# cookie folder for each user login
mkdir -p cookie

# Enhanced curl function with retry logic
make_request() {
    local url=$1
    local method=${2:-GET}
    local data=${3:-}
    local cookie_file=${4:-}
    local max_retries=3
    local retry_count=0
    
    while [ $retry_count -lt $max_retries ]; do
        local curl_cmd="curl -s -o /dev/null -w %{http_code} --connect-timeout 10 --max-time 30"
        
        if [ "$method" = "POST" ]; then
            curl_cmd="$curl_cmd -X POST"
        fi
        
        if [ -n "$data" ]; then
            curl_cmd="$curl_cmd -H 'Content-Type: application/json' -d '$data'"
        fi
        
        if [ -n "$cookie_file" ]; then
            curl_cmd="$curl_cmd --cookie-jar '$cookie_file' --cookie '$cookie_file'"
        fi
        
        curl_cmd="$curl_cmd '$url'"
        
        local response=$(eval $curl_cmd)
        
        if [ "$response" != "000" ]; then
            echo "$response"
            return 0
        fi
        
        retry_count=$((retry_count + 1))
        echo "[RETRY] Attempt $retry_count failed for $url, retrying..." >&2
        sleep 2
    done
    
    echo "000"
    return 1
}

# Function to test connectivity
test_connectivity() {
    echo "Testing connectivity to services..."
    
    # Test manager node
    if ping -c 1 -W 3 "$MANAGER_IP" > /dev/null 2>&1; then
        echo "[✓] Manager node ($MANAGER_IP) is reachable"
    else
        echo "[✗] Manager node ($MANAGER_IP) is not reachable"
        return 1
    fi
    
    # Test authentication service with actual endpoint
    auth_test=$(make_request "http://$MANAGER_IP:5005/" "GET")
    if [ "$auth_test" != "000" ]; then
        echo "[✓] Authentication service is accessible (status: $auth_test)"
    else
        echo "[✗] Authentication service is not accessible (status: $auth_test)"
    fi
    
    # Test load balancer if enabled
    if [ "$USE_LOAD_BALANCER" = true ]; then
        lb_test=$(make_request "http://$MANAGER_IP:80/" "GET")
        if [ "$lb_test" != "000" ]; then
            echo "[✓] Load balancer is accessible (status: $lb_test)"
        else
            echo "[✗] Load balancer is not accessible"
        fi
    fi
    
    # Test customer info service
    customer_test=$(make_request "http://$MANAGER_IP:5006/" "GET")
    if [ "$customer_test" != "000" ]; then
        echo "[✓] Customer info service is accessible (status: $customer_test)"
    else
        echo "[✗] Customer info service is not accessible (status: $customer_test)"
    fi
}

# Function to clear data for each username
cleanup() {
    start_index=$1
    end_index=$2
    for ((i = start_index; i < end_index; i++)); do
        username="user$i"

        (
            # Logout user
            logout_user "$username"

            for url in "$login_data" "$customerInfo_data"; do
                response=$(make_request "$url" "POST" "{\"username\": \"$username\"}")
                if [ "$response" -eq 200 ]; then
                    echo "[CLEANUP][+]  Data for username '$username' cleared successfully at $url."
                elif [ "$response" -eq 404 ]; then
                    echo "[CLEANUP][?]  No data found for username '$username' at $url."
                else
                    echo "[CLEANUP][-]  Failed to clear data for username '$username' at $url. Status code: $response"
                fi
            done
        )&
    done

    wait
    echo "================================================================"
    echo "Cleanup completed for users from $start_index to $((end_index - 1))."
    echo "================================================================"
}

login_user() {
    username=$1
    password=$2
    cookie_file="cookie/cookies_$username.txt"

    # For form data, use different curl approach
    login_response=$(curl -s -o /dev/null -w "%{http_code}" \
        --connect-timeout 10 --max-time 30 \
        -X POST "$login_link" \
        -d "username=$username&password=$password" \
        --cookie-jar "$cookie_file")
        
    if [ "$login_response" -eq 200 ] || [ "$login_response" -eq 302 ]; then
        echo "[LOGIN][+]     User $username logged IN successfully. Cookies saved in $cookie_file."
    else
        echo "[LOGIN][-]     Failed to log-in user $username. Status code: $login_response"
    fi
}

logout_user() {
  username=$1
  cookie_file="cookie/cookies_$username.txt"

  # Follow redirect and capture final status
  logout_response=$(curl -s -L -o /dev/null -w "%{http_code}" "$logout_link" \
    --cookie "$cookie_file" --cookie-jar "$cookie_file")

  if [ "$logout_response" = "200" ] || [ "$logout_response" = "302" ]; then
    echo "[LOGOUT][+]   User $username logged OUT successfully. Status code: $logout_response"
  else
    echo "[LOGOUT][-]   Failed to log-out user $username. Status code: $logout_response"
  fi
}


# ASYNC WAY with better error handling
add_users() {
    default_users=${1:-10}
    
    echo "Starting user registration for $default_users users..."
    
    for ((i = 1; i <= default_users; i++)); do
        username="user$i"
        password="user$i"
        user_data=$(jq -n --arg username "$username" --arg password "$password" \
            --arg name "User $i" --arg email "$username@example.com" \
            --arg contact "+91 98765432$(printf '%02d' $i)" \
            --arg address "${i}00 Main St, Anytown, AnyState" \
            '{username: $username, password: $password, name: $name, email: $email, contact: $contact, address: $address}')

        # Register user in the background
        (
            register_response=$(make_request "$register_url" "POST" "$user_data")
            if [ "$register_response" -eq 200 ]; then
                echo "[REGISTER][+]  User $username registered successfully."
                
                # Login user (after registration)
                sleep 1  # Small delay to ensure registration is complete
                login_user "$username" "$password"
            else
                echo "[REGISTER][-]  Failed to register user $username. Status code: $register_response"
            fi
        ) &
    done

    # Wait for all background processes to complete
    wait
    echo "================================================"
    echo "All users processed concurrently."
    echo "================================================"
}

# Main script to handle flags
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --test)
            test_connectivity
            exit 0
            ;;
        --refresh)
            shift
            if [ $# -lt 2 ]; then
                echo "Error: --refresh requires start_index and end_index"
                echo "Usage: $0 --refresh <start_index> <end_index>"
                exit 1
            fi
            cleanup "$1" "$2"
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
            test_connectivity
            if [ $? -eq 0 ]; then
                add_users "$num_users"
            else
                echo "Connectivity test failed. Please check your services."
                exit 1
            fi
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--ip <manager_ip>] [--test] [--refresh <usernames...>] [--load <number_of_users>] [--login <username> <password>] [--logout <username>]"
            echo "Examples:"
            echo "  $0 --ip 192.168.1.100 --test"
            echo "  $0 --ip=192.168.1.100 --load 5"
            echo "  $0 --load 10  # Uses default IP: $DEFAULT_MANAGER_IP"
            exit 1
            ;;
    esac
done