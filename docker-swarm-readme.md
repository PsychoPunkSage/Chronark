# Docker Swarm Deployment Guide

## Architecture Overview
This deployment uses a Docker Swarm architecture with:
- 1 Manager Node
- 1+ Worker Nodes (for now ONLY 1)
- **`Overlay`** network for cross-node communication
- Multiple replicated services

## Step-by-Step Deployment Guide

### 1. Build Images
On each node, build the required images:
```bash
./build-images.sh
```

### 2. Initialize Swarm (Manager Node)

1. Get your manager node's IP address:
```bash
ifconfig
# Look for your primary network interface (e.g., eth0, wlan0)
# Example output: eth0: inet 10.105.8.94
```

2. Initialize the swarm:
```bash
sudo docker swarm init --advertise-addr <YOUR_IP>
# Example: sudo docker swarm init --advertise-addr 10.105.8.94
```

3. Save the join token command that is displayed. It looks like:
```bash
docker swarm join --token SWMTKN-1-xxxxxx <YOUR_IP>:2377
```

### 3. Join Workers to Swarm (Worker Nodes)

On each worker node:
```bash
sudo docker swarm join --token SWMTKN-1-xxxxxx <MANAGER_IP>:2377
```

### 4. Verify Swarm Setup (Manager Node)

```bash
# List all nodes in the swarm
sudo docker node ls
```

### 5. Create Overlay Network (Manager Node)

```bash
sudo docker network create --driver overlay vittmitra
```

### 6. Deploy Stack (Manager Node)

```bash
sudo docker stack deploy -c docker-compose-swarm.yml vittmitra
```

### 7. Monitor Deployment

```bash
# List all services
sudo docker service ls

# Check service replicas
sudo docker service ls --format "{{.Name}}: {{.Replicas}}"

# View tasks across nodes
sudo docker node ps $(sudo docker node ls -q)

# Check specific service logs
sudo docker service logs <service_name>
```

### 8. Access Services

- Frontend services: http://<MANAGER_IP>:4001, :4002, :4003
- HAProxy: http://<MANAGER_IP>:80
- Monitoring:
  - Grafana: http://<MANAGER_IP>:3000
  - Prometheus: http://<MANAGER_IP>:9090
  - Jaeger: http://<MANAGER_IP>:16686

## Troubleshooting

### Check Service Status
```bash
# View service details
sudo docker service inspect <service_name>

# Check service logs
sudo docker service logs <service_name>

# Force update a service
sudo docker service update --force <service_name>
```

### Check Container Status on Specific Node
```bash
# List running containers
sudo docker ps

# View container stats
sudo docker stats
```

## Cleanup

### Remove Stack (Manager Node)
```bash
# Remove the stack
sudo docker stack rm vittmitra

# Verify all services are removed
sudo docker service ls
```

### Leave Swarm
On worker nodes:
```bash
sudo docker swarm leave
```

On manager node (after all workers have left):
```bash
sudo docker swarm leave --force
```

### Optional Cleanup
```bash
# Clean up networks
sudo docker network prune

# Clean up volumes (warning: deletes data)
sudo docker volume prune

# Clean up unused images
sudo docker image prune

# Complete cleanup (warning: removes all unused objects)
sudo docker system prune -a --volumes
```