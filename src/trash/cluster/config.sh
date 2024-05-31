#!/bin/bash

function error_exit() {
  echo "Error: $1" >&2
  exit 1
}

NETWORK_NAME="redis"

if [[ "$1" != "--up" && "$1" != "--down" ]]; then
  error_exit "Usage: $0 --up or $0 --down"
fi

# Start Redis and Sentinel containers ( --up )
if [[ "$1" == "--up" ]]; then

  sudo docker network create $NETWORK_NAME || true

  sudo docker run -d --rm --name redis-0 --net redis -v ${PWD}/redis-0:/etc/redis/ redis:6.0-alpine redis-server /etc/redis/redis.conf
  sudo docker run -d --rm --name redis-1 --net redis -v ${PWD}/redis-1:/etc/redis/ redis:6.0-alpine redis-server /etc/redis/redis.conf
  sudo docker run -d --rm --name redis-2 --net redis -v ${PWD}/redis-2:/etc/redis/ redis:6.0-alpine redis-server /etc/redis/redis.conf
  
  sudo docker run -d --rm --name sentinel-0 --net redis -v ${PWD}/sentinel-0:/etc/redis/ redis:6.0-alpine redis-sentinel /etc/redis/sentinel.conf
  sudo docker run -d --rm --name sentinel-1 --net redis -v ${PWD}/sentinel-1:/etc/redis/ redis:6.0-alpine redis-sentinel /etc/redis/sentinel.conf
  sudo docker run -d --rm --name sentinel-2 --net redis -v ${PWD}/sentinel-2:/etc/redis/ redis:6.0-alpine redis-sentinel /etc/redis/sentinel.conf

  echo "Redis cluster with Sentinel started successfully!"

# Stop Redis and Sentinel containers ( --down )
elif [[ "$1" == "--down" ]]; then

  for container in redis-0 redis-1 redis-2; do
    sudo docker rm -f $container || true
  done

  for container in sentinel-0 sentinel-1 sentinel-2; do
    sudo docker rm -f $container || true
  done

  sudo docker network rm $NETWORK_NAME || true

  echo "Redis cluster with Sentinel stopped and removed."

fi

