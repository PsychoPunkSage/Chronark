# DEPRECATED (ONLY FOR INFO PURPOSE)

## Deployment

### Configuration:
```
#persistence
dir /data
dbfilename dump.rdb
appendonly yes
appendfilename "appendonly.aof"
```

>> All the configuration of `Redis` and `Sentinels` are present in respective folders

### Running `Redis` replicas
> Create a `Redis` network:
```bash
docker network create redis
```

> Create 3 `Redis` nodes:
* redis-0

<details>
<summary>redis-0 config</summary>

```
protected-mode no
port 6379

#authentication
masterauth a-very-complex-password-here
requirepass a-very-complex-password-here
```

</details>

```bash
docker run -d --rm --name redis-0 --net redis -v ${PWD}/redis-0:/etc/redis/ redis:6.0-alpine redis-server /etc/redis/redis.conf
```
* redis-1

<details>
<summary>redis-1 config</summary>

```
protected-mode no
port 6379
slaveof redis-0 6379

#authentication
masterauth a-very-complex-password-here
requirepass a-very-complex-password-here
```

</details>

```bash
docker run -d --rm --name redis-1 --net redis -v ${PWD}/redis-1:/etc/redis/ redis:6.0-alpine redis-server /etc/redis/redis.conf
```
* redis-2

<details>
<summary>redis-2 config</summary>

```
protected-mode no
port 6379
slaveof redis-0 6379

#authentication
masterauth a-very-complex-password-here
requirepass a-very-complex-password-here
```

</details>

```bash
docker run -d --rm --name redis-2 --net redis -v ${PWD}/redis-2:/etc/redis/ redis:6.0-alpine redis-server /etc/redis/redis.conf
```

### Running `Sentinels`
> Create `Cluster` by running 3 `Sentinel` service.
* sentinel-0

<details>
<summary>sentinel-0 config</summary>

```
port 4001
sentinel monitor mymaster redis-0 6379 2
sentinel down-after-milliseconds mymaster 4001
sentinel failover-timeout mymaster 60000
sentinel parallel-syncs mymaster 1
sentinel auth-pass mymaster a-very-complex-password-here
```

</details>

```bash
docker run -d --rm --name sentinel-0 --net redis -v ${PWD}/sentinel-0:/etc/redis/ redis:6.0-alpine redis-sentinel /etc/redis/sentinel.conf
```
* sentinel-1

<details>
<summary>sentinel-1 config</summary>

```
port 4001
sentinel monitor mymaster redis-0 6379 2
sentinel down-after-milliseconds mymaster 4001
sentinel failover-timeout mymaster 60000
sentinel parallel-syncs mymaster 1
sentinel auth-pass mymaster a-very-complex-password-here
```

</details>

```bash
docker run -d --rm --name sentinel-1 --net redis -v ${PWD}/sentinel-1:/etc/redis/ redis:6.0-alpine redis-sentinel /etc/redis/sentinel.conf
```
* sentinel-2

<details>
<summary>sentinel-1 config</summary>

```
port 4001
sentinel monitor mymaster redis-0 6379 2
sentinel down-after-milliseconds mymaster 4001
sentinel failover-timeout mymaster 60000
sentinel parallel-syncs mymaster 1
sentinel auth-pass mymaster a-very-complex-password-here
```

</details>

```bash
docker run -d --rm --name sentinel-2 --net redis -v ${PWD}/sentinel-2:/etc/redis/ redis:6.0-alpine redis-sentinel /etc/redis/sentinel.conf
```
