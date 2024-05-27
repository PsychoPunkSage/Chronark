# DATABASE Mgmt.

## Image:

> **Image:** `redis6.0-alpine`

## Running Redis

> Create a network
```bash
docker network create redis
```

> Launch Redis
```bash
docker run -it --rm --name redis --net redis -p 6379:6379 redis:6.0-alpine
```

> Launching Redis with Custom Config
```bash
# Make sure you are inside `offer_banner` folder
docker run -it --rm --name redis --net redis -v ${PWD}/config:/etc/redis/ redis:6.0-alpine redis-server /etc/redis/redis.conf

docker run -d --rm --name redis-0 --net redis -v ${PWD}/redis-0:/etc/redis/ -p 6379:6379 redis:6.0-alpine redis-server /etc/redis/redis.conf
```

## Security

> Don't expose `Redis` to public as anyone can connect with it. Always use strong passwords in redis.conf

```
requirepass SuperSecretSecureStrongPass
```

## Persistence
> I have turned on both `rdb` ans `aof` mode.

```bash
docker volume create redis
# Make sure you are inside `offer_banner` folder
docker run -it --rm --name redis --net redis -v ${PWD}/config:/etc/redis/ -v redis:/data/ redis:6.0-alpine redis-server /etc/redis/redis.conf
```

# My Deployment:

