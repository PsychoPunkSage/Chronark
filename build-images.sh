#!/bin/bash

# Set your registry (if using one) or use local
DOCKER_HUB_USER="psychopunksage"
TAG=${1:-"latest"}
FORCE_REBUILD=${2:-"no"}

echo "Logging into Docker Hub as ${DOCKER_HUB_USER}..."
sudo docker login -u ${DOCKER_HUB_USER}

build_and_push() {
    local IMAGE_NAME="$1"
    local DOCKERFILE="$2"
    local CONTEXT="$3"
    
    # Build the image
    echo "Building ${IMAGE_NAME}..."
    sudo docker build -t ${DOCKER_HUB_USER}/${IMAGE_NAME}:${TAG} -f ${DOCKERFILE} ${CONTEXT}
    
    # Push to Docker Hub
    echo "Pushing ${IMAGE_NAME} to Docker Hub..."
    sudo docker push ${DOCKER_HUB_USER}/${IMAGE_NAME}:${TAG}
}

echo "Starting build process with smart disk space management..."

# Build acl
build_and_push "opa" "./src/acl/Dockerfile.opa" "./src/acl"

# Build offer-banner
build_and_push "offer-banner" "./src/offer_banner/Dockerfile.offer_banner" "./src/offer_banner"

# Build contacts 
build_and_push "contacts" "./src/contact/Dockerfile.contact" "./src/contact"

# Build search
build_and_push "search" "./src/search/Dockerfile.search" "./src/search"

# Build authentication
build_and_push "authentication" "./src/authentication/Dockerfile.authentication" "./src/authentication"

# Build customer-info
build_and_push "customer-info" "./src/customerInfo/Dockerfile.customerInfo" "./src/customerInfo"

# Build customer-activity
build_and_push "customer-activity" "./src/customerActivity/Dockerfile.customerActivity" "./src/customerActivity"

# Build personal-lending
build_and_push "personal-lending" "./src/personalLending/Dockerfile.personalLending" "./src/personalLending"

# Build business-lending
build_and_push "business-lending" "./src/businessLending/Dockerfile.businessLending" "./src/businessLending"

# Build mortgage
build_and_push "mortgage" "./src/mortgage/Dockerfile.mortgage" "./src/mortgage"

# Build investment
build_and_push "investment" "./src/investment-account/Dockerfile.investment" "./src/investment-account"

# Build deposit-account
build_and_push "deposit-account" "./src/depositAccount/Dockerfile.depositAccount" "./src/depositAccount"

# Build payments
build_and_push "payments" "./src/payments/Dockerfile.payments" "./src/payments"

# Build wealth-mgmt
build_and_push "wealth-mgmt" "./src/wealth_mgmt/Dockerfile.wealth_mgmt" "./src/wealth_mgmt"

# Build frontend
build_and_push "frontend1" "./src/frontend/Dockerfile.frontend1" "./src/frontend"
build_and_push "frontend2" "./src/frontend/Dockerfile.frontend2" "./src/frontend"
build_and_push "frontend3" "./src/frontend/Dockerfile.frontend3" "./src/frontend"

echo "Build process completed successfully."

# # Check available disk space
# DISK_USAGE=$(df -h / | grep / | awk '{print $5}' | sed 's/%//')
# if [ "$DISK_USAGE" -gt 85 ] && [ "$FORCE_REBUILD" != "yes" ]; then
#     echo "WARNING: Disk usage is at ${DISK_USAGE}%. Building all images may cause disk space issues."
#     echo "You can free up space with: sudo docker system prune -a"
#     read -p "Continue with build anyway? (y/n): " CONTINUE
#     if [ "$CONTINUE" != "y" ]; then
#         echo "Build aborted."
#         exit 1
#     fi
# fi

# # Function to build an image if it doesn't exist or if forced
# build_if_needed() {
#     local IMAGE_NAME="$1"
#     local DOCKERFILE="$2"
#     local CONTEXT="$3"
    
#     # Check if image exists
#     if [[ "$(sudo docker images -q ${REGISTRY}/${IMAGE_NAME}:${TAG} 2> /dev/null)" == "" ]] || [ "$FORCE_REBUILD" == "yes" ]; then
#         echo "Building ${IMAGE_NAME}..."
#         sudo docker build -t ${REGISTRY}/${IMAGE_NAME}:${TAG} -f ${DOCKERFILE} ${CONTEXT}
        
#         # Check if build succeeded
#         if [ $? -ne 0 ]; then
#             echo "Failed to build ${IMAGE_NAME}, cleaning up first and retrying..."
#             sudo docker system prune -f
#             sudo docker build -t ${REGISTRY}/${IMAGE_NAME}:${TAG} -f ${DOCKERFILE} ${CONTEXT}
            
#             # If it fails again, exit
#             if [ $? -ne 0 ]; then
#                 echo "Build failed for ${IMAGE_NAME} after cleanup. Exiting."
#                 exit 1
#             fi
#         fi

#         # Push to registry
#         echo "Pushing ${IMAGE_NAME} to registry..."
#         sudo docker push ${REGISTRY}/${IMAGE_NAME}:${TAG}
#     else
#         echo "Image ${REGISTRY}/${IMAGE_NAME}:${TAG} already exists, skipping build."
#         sudo docker push ${REGISTRY}/${IMAGE_NAME}:${TAG}
#     fi
# }

# # Build each service
# echo "Starting build process with smart disk space management..."

# # Build acl
# build_if_needed "opa" "./src/acl/Dockerfile.opa" "./src/acl"

# # Build offer-banner
# build_if_needed "offer-banner" "./src/offer_banner/Dockerfile.offer_banner" "./src/offer_banner"

# # Build contacts 
# build_if_needed "contacts" "./src/contact/Dockerfile.contact" "./src/contact"

# # Build search
# build_if_needed "search" "./src/search/Dockerfile.search" "./src/search"

# # Build authentication
# build_if_needed "authentication" "./src/authentication/Dockerfile.authentication" "./src/authentication"

# # Build customer-info
# build_if_needed "customer-info" "./src/customerInfo/Dockerfile.customerInfo" "./src/customerInfo"

# # Build customer-activity
# build_if_needed "customer-activity" "./src/customerActivity/Dockerfile.customerActivity" "./src/customerActivity"

# # Build personal-lending
# build_if_needed "personal-lending" "./src/personalLending/Dockerfile.personalLending" "./src/personalLending"

# # Build business-lending
# build_if_needed "business-lending" "./src/businessLending/Dockerfile.businessLending" "./src/businessLending"

# # Build mortgage
# build_if_needed "mortgage" "./src/mortgage/Dockerfile.mortgage" "./src/mortgage"

# # Build investment
# build_if_needed "investment" "./src/investment-account/Dockerfile.investment" "./src/investment-account"

# # Build deposit-account
# build_if_needed "deposit-account" "./src/depositAccount/Dockerfile.depositAccount" "./src/depositAccount"

# # Build payments
# build_if_needed "payments" "./src/payments/Dockerfile.payments" "./src/payments"

# # Build wealth-mgmt
# build_if_needed "wealth-mgmt" "./src/wealth_mgmt/Dockerfile.wealth_mgmt" "./src/wealth_mgmt"

# # Build frontend
# build_if_needed "frontend1" "./src/frontend/Dockerfile.frontend1" "./src/frontend"
# build_if_needed "frontend2" "./src/frontend/Dockerfile.frontend2" "./src/frontend"
# build_if_needed "frontend3" "./src/frontend/Dockerfile.frontend3" "./src/frontend"

# echo "Build process completed successfully."