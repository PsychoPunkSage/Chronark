#!/bin/bash

set -e

REDIS_CONTAINER_NAME="db-redis-offer-banner"
OFFER_BANNER_CONTAINER_NAME="ms-offer-banner"
FRONTEND_CONTAINER_NAME="ms-frontend"
NETWORK_NAME="vittmitra"
REDIS_IMAGE="redis:6.0-alpine"
OFFER_BANNER_IMAGE="offer_banner:latest"
FRONTEND_IMAGE="frontend:latest"
REDIS_CONFIG_PATH="${PWD}/src/offer_banner/conf"
OFFER_BANNER_PATH="${PWD}/src/offer_banner"
FRONTEND_PATH="${PWD}/src/frontend"

function start_containers() {
    echo "____________________"
    echo "| Creating Network |"
    echo "--------------------"
    sudo docker network create $NETWORK_NAME

    echo "_________________________________"
    echo "| Launching Configured Redis DB |"
    echo "---------------------------------"
    
    cd $REDIS_CONFIG_PATH
    # echo " <REDIS> Stopping previous reference"
    # sudo docker stop $REDIS_CONTAINER_NAME || true
    echo " <REDIS> Launching the image....."
    sudo docker run -d --rm --name $REDIS_CONTAINER_NAME --net $NETWORK_NAME -v ${PWD}:/etc/redis/ -p 6379:6379 $REDIS_IMAGE redis-server /etc/redis/redis.conf
    
    echo "_______________________________________"
    echo "| Launching OFFER-BANNER microservice |"
    echo "---------------------------------------"
    cd $OFFER_BANNER_PATH
    echo "Location::> ${OFFER_BANNER_PATH}"
    # echo " <ms-offer-banner> Removing previous reference"
    # sudo docker rm $OFFER_BANNER_CONTAINER_NAME || true
    echo " <ms-offer-banner> Building the image....."
    sudo docker build -f Dockerfile.offer_banner -t $OFFER_BANNER_IMAGE .
    echo " <ms-offer-banner> Running the image....."
    sudo docker run -p 5002:5002 --net $NETWORK_NAME --name $OFFER_BANNER_CONTAINER_NAME -d -e REDIS_PASSWORD="a-very-complex-password-here" -e REDIS_PORT="6379" -e REDIS_HOST="$REDIS_CONTAINER_NAME" $OFFER_BANNER_IMAGE
    
    echo "___________________________________"
    echo "| Launching frontend microservice |"
    echo "-----------------------------------"
    cd $FRONTEND_PATH
    # echo " <ms-frontend> Removing previous reference"
    # sudo docker rm $FRONTEND_CONTAINER_NAME || true
    echo " <ms-frontend> Building the image....."
    sudo docker build -f Dockerfile.frontend -t $FRONTEND_IMAGE .
    echo " <ms-frontend> Running the image....."
    sudo docker run -p 4001:4001 --net $NETWORK_NAME --name $FRONTEND_CONTAINER_NAME -d -e OFFER_BANNER_SERVICE_HOST="$OFFER_BANNER_CONTAINER_NAME" -e OFFER_BANNER_SERVICE_PORT="5002"  $FRONTEND_IMAGE
    
    echo "__________________________________"
    echo "| VISIT::> http://127.0.0.1:4001 |"
    echo "|--------------------------------|"
}

function stop_containers() {
    echo "Stopping and removing containers..."
    sudo docker stop $REDIS_CONTAINER_NAME || true
    sudo docker stop $OFFER_BANNER_CONTAINER_NAME || true
    sudo docker stop $FRONTEND_CONTAINER_NAME || true
    sudo docker rm $OFFER_BANNER_CONTAINER_NAME || true
    sudo docker rm $FRONTEND_CONTAINER_NAME || true
    sudo docker network rm $NETWORK_NAME || true
    echo "Containers stopped and removed."
}

if [ "$1" == "up" ]; then
    start_containers
elif [ "$1" == "down" ]; then
    stop_containers
else
    echo "Usage: $0 {up|down}"
    exit 1
fi
