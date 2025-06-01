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

# echo "Building Redis images..."
build_and_push "redis-offer-banner" "./src/redis/Dockerfile.redis-offer-banner" "./src/redis"
build_and_push "redis-search" "./src/redis/Dockerfile.redis-search" "./src/redis"
build_and_push "redis-auth" "./src/redis/Dockerfile.redis-auth" "./src/redis"

# Build haproxy
build_and_push "haproxy" "./src/redis/Dockerfile.haproxy" "./src/redis"

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

# Build credit-card
build_and_push "credit-card" "./src/creditCard/Dockerfile.creditCard" "./src/creditCard"

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