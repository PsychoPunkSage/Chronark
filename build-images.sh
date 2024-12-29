#!/bin/bash

# Set your registry (if using one) or use local
REGISTRY=${1:-"local"}
TAG=${2:-"latest"}

# Build offer-banner
sudo docker build -t ${REGISTRY}/offer-banner:${TAG} -f ./src/offer_banner/Dockerfile.offer_banner ./src/offer_banner

# Build contacts
sudo docker build -t ${REGISTRY}/contacts:${TAG} -f ./src/contact/Dockerfile.contact ./src/contact

# Build search
sudo docker build -t ${REGISTRY}/search:${TAG} -f ./src/search/Dockerfile.search ./src/search

# Build authentication
sudo docker build -t ${REGISTRY}/authentication:${TAG} -f ./src/authentication/Dockerfile.authentication ./src/authentication

# Build customer-info
sudo docker build -t ${REGISTRY}/customer-info:${TAG} -f ./src/customerInfo/Dockerfile.customerInfo ./src/customerInfo

# Build customer-activity
sudo docker build -t ${REGISTRY}/customer-activity:${TAG} -f ./src/customerActivity/Dockerfile.customerActivity ./src/customerActivity

# Build personal-lending
sudo docker build -t ${REGISTRY}/personal-lending:${TAG} -f ./src/personalLending/Dockerfile.personalLending ./src/personalLending

# Build business-lending
sudo docker build -t ${REGISTRY}/business-lending:${TAG} -f ./src/businessLending/Dockerfile.businessLending ./src/businessLending

# Build mortgage
sudo docker build -t ${REGISTRY}/mortgage:${TAG} -f ./src/mortgage/Dockerfile.mortgage ./src/mortgage

# Build investment
sudo docker build -t ${REGISTRY}/investment:${TAG} -f ./src/investment-account/Dockerfile.investment ./src/investment-account

# Build deposit-account
sudo docker build -t ${REGISTRY}/deposit-account:${TAG} -f ./src/depositAccount/Dockerfile.depositAccount ./src/depositAccount

# Build payments
sudo docker build -t ${REGISTRY}/payments:${TAG} -f ./src/payments/Dockerfile.payments ./src/payments

# Build wealth-mgmt
sudo docker build -t ${REGISTRY}/wealth-mgmt:${TAG} -f ./src/wealth_mgmt/Dockerfile.wealth_mgmt ./src/wealth_mgmt

# Build frontend
sudo docker build -t ${REGISTRY}/frontend:${TAG} -f ./src/frontend/Dockerfile.frontend1 ./src/frontend