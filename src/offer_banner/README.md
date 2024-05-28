# DATABASE Mgmt.

## Image:

> **Image:** `redis6.0-alpine`

## Running Redis

> Create a network
```bash
docker network create redis
```

> Launch Redis
<details>
<summary>Normal Launch</summary>

```bash
docker run -it --rm --name redis --net redis -p 6379:6379 redis:6.0-alpine
```

</details><br>


> Launching Redis with Custom Config (better)

<details>
<summary>Custom Launch</summary>

```bash
# Make sure you are inside `offer_banner/conf` folder
docker run -d --rm --name db-redis-offer-banner --net redis -v ${PWD}:/etc/redis/ -p 6379:6379 redis:6.0-alpine redis-server /etc/redis/redis.conf
```

</details><br>

## Security

> Don't expose `Redis` to public as anyone can connect with it. Always use strong passwords in redis.conf

```
requirepass SuperSecretSecureStrongPass
```

## Persistence (Optional)
> I have turned on both `rdb` ans `aof` mode.

```bash
docker volume create redis
# Make sure you are inside `offer_banner` folder
docker run -it --rm --name redis --net redis -v ${PWD}/config:/etc/redis/ -v redis:/data/ redis:6.0-alpine redis-server /etc/redis/redis.conf
```

<!-- # My Deployment: -->

