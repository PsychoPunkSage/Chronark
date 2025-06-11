#!/bin/bash

# Default configuration
DEFAULT_MANAGER_IP="localhost"
MANAGER_IP=""
USE_LOAD_BALANCER=true  # Set to false to test services directly

# Metrics
STATS_DIR="/tmp/load_test_$$"
mkdir -p "$STATS_DIR"
REGISTERED_USERS_FILE="$STATS_DIR/registered_users.txt"

# Statistics tracking functions
increment_stat() {
    local stat_file="$STATS_DIR/$1"
    local count=$(cat "$stat_file" 2>/dev/null || echo 0)
    echo $((count + 1)) > "$stat_file"
}

get_stat() {
    cat "$STATS_DIR/$1" 2>/dev/null || echo 0
}

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
    load=$1
    for ((i = 1; i <= load; i++)); do
        username="user$i"

        (
            # Logout user
            logout_user "$username"

            for url in "$login_data" "$customerInfo_data"; do
                response=$(make_request "$url" "POST" "{\"username\": \"$username\"}")
                if [ "$response" -eq 200 ]; then
                    echo "[CLEANUP][+]  Data for username '$username' cleared successfully at $url."
                    increment_stat "cleanup_success"
                elif [ "$response" -eq 404 ]; then
                    echo "[CLEANUP][?]  No data found for username '$username' at $url."
                    increment_stat "cleanup_not_found"
                else
                    echo "[CLEANUP][-]  Failed to clear data for username '$username' at $url. Status code: $response"
                    increment_stat "cleanup_failed"
                fi
            done
        )&
    done

    wait
    echo "================================================================"
    echo "Cleanup completed for users from 1 to $((load))."
    print_stats
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
        increment_stat "login_success"
    else
        echo "[LOGIN][-]     Failed to log-in user $username. Status code: $login_response"
        increment_stat "login_failed"
    fi
}

# logout_user() {
#   username=$1
#   cookie_file="cookie/cookies_$username.txt"

#   # Follow redirect and capture final status
#   logout_response=$(curl -s -L -o /dev/null -w "%{http_code}" "$logout_link" \
#     --cookie "$cookie_file" --cookie-jar "$cookie_file")

#   if [ "$logout_response" = "200" ] || [ "$logout_response" = "302" ]; then
#     echo "[LOGOUT][+]   User $username logged OUT successfully. Status code: $logout_response"
#   else
#     echo "[LOGOUT][-]   Failed to log-out user $username. Status code: $logout_response"
#   fi
# }

login_user() {
    local username=$1
    local password=$2
    local cookie_file="cookie/cookies_$username.txt"
    local max_retries=3
    local retry_count=0

    while [ $retry_count -lt $max_retries ]; do
        # For form data, use different curl approach
        login_response=$(curl -s -o /dev/null -w "%{http_code}" \
            --connect-timeout 10 --max-time 30 \
            -X POST "$login_link" \
            -d "username=$username&password=$password" \
            --cookie-jar "$cookie_file")
            
        if [ "$login_response" -eq 200 ] || [ "$login_response" -eq 302 ]; then
            echo "[LOGIN][+]     User $username logged IN successfully. Cookies saved in $cookie_file."
            increment_stat "login_success"
            return 0
        else
            retry_count=$((retry_count + 1))
            echo "[LOGIN][-]     Failed to log-in user $username (attempt $retry_count/$max_retries). Status code: $login_response"
            
            if [ $retry_count -lt $max_retries ]; then
                echo "[LOGIN][RETRY] Retrying login for $username in 2 seconds..."
                sleep 2
            fi
        fi
    done
    
    echo "[LOGIN][-]     Failed to log-in user $username after $max_retries attempts."
    increment_stat "login_failed"
    return 1
}

# ASYNC WAY with better error handling
# add_users() {
#     default_users=${1:-10}
    
#     echo "Starting user registration for $default_users users..."
    
#     for ((i = 1; i <= default_users; i++)); do
#         username="user$i"
#         password="user$i"
#         user_data=$(jq -n --arg username "$username" --arg password "$password" \
#             --arg name "User $i" --arg email "$username@example.com" \
#             --arg contact "+91 98765432$(printf '%02d' $i)" \
#             --arg address "${i}00 Main St, Anytown, AnyState" \
#             '{username: $username, password: $password, name: $name, email: $email, contact: $contact, address: $address}')

#         # Register user in the background
#         (
#             register_response=$(make_request "$register_url" "POST" "$user_data")
#             if [ "$register_response" -eq 200 ]; then
#                 echo "[REGISTER][+]  User $username registered successfully."
#                 increment_stat "register_success"

#                 # Login user (after registration)
#                 sleep 1  # Small delay to ensure registration is complete
#                 login_user "$username" "$password"
#             else
#                 echo "[REGISTER][-]  Failed to register user $username. Status code: $register_response"
#                 increment_stat "register_failed"
#             fi
#         ) &
#     done

#     # Wait for all background processes to complete
#     wait
#     echo "================================================"
#     echo "All users processed concurrently."
#     print_stats
# }

add_users() {
    default_users=${1:-10}

    # Initialize the registered users file
    > "$REGISTERED_USERS_FILE"
    
    echo "Starting user registration for $default_users users..."
    echo "Phase 1: Registering all users..."
    
    # Phase 1: Register all users concurrently
    for ((i = 1; i <= default_users; i++)); do
        username="user$i"
        password="user$i"
        user_data=$(jq -n --arg username "$username" --arg password "$password" \
            --arg name "User $i" --arg email "$username@example.com" \
            --arg contact "+91 98765432$(printf '%02d' $i)" \
            --arg address "${i}00 Main St, Anytown, AnyState" \
            '{username: $username, password: $password, name: $name, email: $email, contact: $contact, address: $address}')

        # Register user in the background with retry logic
        (
            register_user_with_retry "$username" "$password" "$user_data"
        ) &
    done

    # Wait for all registration processes to complete
    wait
    local registered_count=0
    if [ -f "$REGISTERED_USERS_FILE" ]; then
        registered_count=$(wc -l < "$REGISTERED_USERS_FILE")
    fi

    echo "Phase 1 completed. Registration stats:"
    echo "  ✅ Successful: $(get_stat "register_success")"
    echo "  ❌ Failed:     $(get_stat "register_failed")"
    echo "  📊 Total:      $(($(get_stat "register_success") + $(get_stat "register_failed")))"
    echo "  📋 Users to login: $registered_count"
    echo ""
    
    echo "Phase 2: Logging in all successfully registered users..."
    
    # Phase 2: Login all users (only those that were successfully registered)
    if [ "$registered_count" -gt 0 ]; then
        while IFS= read -r username; do
            password="$username"  # password same as username
            
            # Login user in the background with retry logic
            (
                login_user "$username" "$password"
            ) &
        done < "$REGISTERED_USERS_FILE"
        
        # Wait for all login processes to complete
        wait
    else
        echo "No users were successfully registered. Skipping login phase."
    fi
    
    echo "================================================"
    echo "All users processed in separate phases."
    print_stats
}

register_user_with_retry() {
    local username=$1
    local password=$2
    local user_data=$3
    local max_retries=3
    local retry_count=0
    
    while [ $retry_count -lt $max_retries ]; do
        register_response=$(make_request "$register_url" "POST" "$user_data")
        
        if [ "$register_response" -eq 200 ]; then
            echo "[REGISTER][+]  User $username registered successfully."
            increment_stat "register_success"
            echo "$username" >> "$REGISTERED_USERS_FILE"
            return 0
        else
            retry_count=$((retry_count + 1))
            echo "[REGISTER][-]  Failed to register user $username (attempt $retry_count/$max_retries). Status code: $register_response"
            
            if [ $retry_count -lt $max_retries ]; then
                echo "[REGISTER][RETRY] Retrying registration for $username in 2 seconds..."
                sleep 2
            fi
        fi
    done
    
    echo "[REGISTER][-]  Failed to register user $username after $max_retries attempts."
    increment_stat "register_failed"
    return 1
}

print_stats() {
    local register_success=$(get_stat "register_success")
    local register_failed=$(get_stat "register_failed")
    local login_success=$(get_stat "login_success")
    local login_failed=$(get_stat "login_failed")
    local cleanup_success=$(get_stat "cleanup_success")
    local cleanup_not_found=$(get_stat "cleanup_not_found")
    local cleanup_failed=$(get_stat "cleanup_failed")
    
    echo ""
    echo "================================================"
    echo "              LOAD TEST STATISTICS"
    echo "================================================"
    echo "REGISTRATION:"
    echo "  ✅ Successful: $register_success"
    echo "  ❌ Failed:     $register_failed"
    echo "  📊 Total:      $((register_success + register_failed))"
    echo ""
    echo "LOGIN:"
    echo "  ✅ Successful: $login_success" 
    echo "  ❌ Failed:     $login_failed"
    echo "  📊 Total:      $((login_success + login_failed))"
    echo ""
    if [ $((cleanup_success + cleanup_not_found + cleanup_failed)) -gt 0 ]; then
        echo "CLEANUP:"
        echo "  ✅ Successful: $cleanup_success"
        echo "  ❓ Not Found:  $cleanup_not_found"
        echo "  ❌ Failed:     $cleanup_failed"
        echo "  📊 Total:      $((cleanup_success + cleanup_not_found + cleanup_failed))"
        echo ""
    fi
    echo "================================================"
    
    # Cleanup temp files
    rm -rf "$STATS_DIR"
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
            if [ $# -lt 1 ]; then
                echo "Error: --refresh requires no. of accounts to be deleted"
                echo "Usage: $0 --refresh <load>"
                exit 1
            fi
            cleanup "$1"
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