# Chronark: A Scalable and Secure Cloud-Native Benchmarking Framework

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)
[![Multi-Cloud](https://img.shields.io/badge/Multi--Cloud-AWS%20%7C%20GCP%20%7C%20Azure-orange.svg)](https://github.com/yourusername/chronark)

## Description

Chronark is a comprehensive cloud-native benchmarking framework designed to evaluate distributed microservice systems under realistic, security-aware conditions. Unlike traditional benchmarking platforms that focus solely on performance metrics, Chronark integrates automated multi-cloud deployment, penetration testing, fault resilience assessments, and fine-grained resource profiling into a unified platform.

Built upon and extending the capabilities of existing frameworks like DeathStarBench, Chronark addresses critical gaps in modern microservice evaluation by providing:

- **Zero-touch deployment** across AWS, GCP, Azure, and local environments
- **Security-aware benchmarking** with real-world CVE implementations
- **Banking-grade testbed** simulating realistic financial operations
- **Comprehensive observability** with container-level performance insights
- **Scalable architecture** supporting dynamic VM scaling and load distribution

## Table of Contents

- [Features](#features)
- [Comparison with Existing Frameworks](#comparison-with-existing-frameworks)
- [Unique Features](#unique-features)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation & Quick Start](#installation--quick-start)
- [Remote Deployment](#remote-deployment)
- [Vulnerability Testing](#vulnerability-testing)
- [Monitoring & Observability](#monitoring--observability)
- [Performance Evaluation](#performance-evaluation)
- [Contributing](#contributing)
- [License](#license)
- [Citation](#citation)

## Features

### **Zero-Touch Multi-Cloud Deployment**
- Single-command deployment across AWS, GCP, Azure, and local servers
- Automated Docker Swarm orchestration and configuration
- Dynamic VM scaling without manual reconfiguration

### **Security-Aware Benchmarking**
- Real-world CVE implementations (Redis CVE-2022-24834, MongoDB CVE-2020-7921, Node.js CVE-2024-27983)
- Penetration testing capabilities with exploit simulation
- Security response and resilience evaluation

### **Banking Microservice Testbed**
![Reference Image](./image/ref_img.png)
- Production-grade financial system simulation
- Realistic operations: registration, login, fund transfer, account management
- Regulatory compliance and fault tolerance modeling

### **Comprehensive Observability**
- Container-level resource monitoring with cAdvisor
- Distributed tracing with Jaeger
- Real-time CPU, memory, disk I/O, and network metrics
- Custom monitoring agents for trend analysis

### **Scalable Performance Testing**
- Linear scaling validation across multiple VM configurations
- Load testing with session-based authentication
- Comparative performance analysis tools

## Comparison with Existing Frameworks

| Framework | Latency/Throughput | Multi-Cloud | Auto Deploy | Security Eval | Zero-Touch | Banking Testbed |
|-----------|-------------------|-------------|-------------|---------------|------------|-----------------|
| **Chronark** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| DeathStarBench | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| TrainTicket | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| µSuite | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| SeBS | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| ServerlessBench | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Sinan | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| MicroRank | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |

## Unique Features

### **Real-World Vulnerability Integration**
Chronark uniquely incorporates actual CVEs into its testing environment:

- **Redis CVE-2022-24834**: Lua script heap overflow exploitation (CVSS 7.0)
- **MongoDB CVE-2020-7921**: Authorization bypass through serialization flaws (CVSS 4.6)
- **Node.js CVE-2024-27983**: HTTP/2 denial-of-service via race conditions (CVSS 8.2)

### **Automated Security Response Testing**
- Simulates Advanced Persistent Threat (APT) attack scenarios
- Tests intrusion detection system effectiveness
- Validates cloud provider security feature responses

### **Banking-Grade Compliance Testing**
- Implements realistic financial transaction workflows
- Tests regulatory compliance under load
- Evaluates data confidentiality and integrity measures

### **True Multi-Cloud Portability**
- Consistent deployment across heterogeneous cloud environments
- Platform-independent architecture with cloud-specific optimizations
- Comparative cloud provider performance analysis

## Architecture

Chronark employs a microservices architecture consisting of:

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Front-End     │    │   Load Balancer  │    │   Authentication│
│   (Node.js)     │◄──►│    (HAProxy)     │◄──►│    Service      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                        │
         ▼                        ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Banking       │    │   Investment     │    │   Customer      │
│   Services      │    │   Services       │    │   Services      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                        │
         ▼                        ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   MongoDB       │    │     Redis        │    │    Memcached    │
│   Databases     │    │     Cache        │    │     Cache       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Prerequisites

- **Docker** (version 20.10 or higher)
- **Docker Compose** (version 2.0 or higher)
- **Make** (for deployment scripts)

For remote deployments:
- Cloud provider CLI tools (AWS CLI, gcloud, Azure CLI)
- SSH access to target machines
- Appropriate cloud permissions for VM management

## Installation & Quick Start

### Local Deployment

1. **Clone the repository**
   ```bash
   git clone https://github.com/PsychoPunkSage/Chronark.git
   cd Chronark
   ```

2. **Start the system**
   ```bash
   sudo docker compose up -d
   ```

3. **Verify deployment**
   ```bash
   docker-compose ps
   ```

4. **Access services**
   - Banking Application: `http://localhost:8080`
   - Jaeger Tracing: `http://localhost:16686`
   - cAdvisor Monitoring: `http://localhost:9091`

### Load Testing

Generate test load with 1000 requests:
```bash
make load-test
```

## Remote Deployment

### AWS Deployment

Deploy to AWS infrastructure with a single command:

```bash
make aws-deploy
```

This script will:
- Provision EC2 instances across multiple availability zones
- Configure Docker Swarm cluster automatically
- Deploy the complete microservice stack
- Set up monitoring and logging infrastructure
- Configure security groups and networking

### Custom Cloud Deployment

For other cloud providers or custom configurations:

```bash
# Configure your target hosts in deployment/hosts.yml
vim deployment/hosts.yml

# Deploy to configured hosts
make deploy CLOUD_PROVIDER=gcp
make deploy CLOUD_PROVIDER=azure
```

### Deployment Configuration

Customize deployment parameters in `deployment/config.yml`:

```yaml
cluster:
  vm_count: 8
  vm_type: "e2-medium"  # GCP
  region: "us-central1"
  
security:
  enable_cves: true
  vulnerability_tests: ["redis", "mongodb", "nodejs"]
  
monitoring:
  enable_jaeger: true
  enable_cadvisor: true
  retention_days: 7
```

## Vulnerability Testing

### Automated Security Assessment

Run comprehensive security evaluation:

```bash
make security-test
```

### Individual CVE Testing

Test specific vulnerabilities:

```bash
# Redis heap overflow
make test-cve CVE=redis-2022-24834

# MongoDB authorization bypass
make test-cve CVE=mongodb-2020-7921

# Node.js DoS attack
make test-cve CVE=nodejs-2024-27983
```

### Custom Penetration Testing

Create custom attack scenarios:

```bash
# Generate attack payload
./scripts/generate-exploit.sh --target mongodb --payload custom.json

# Execute controlled attack
./scripts/execute-attack.sh --exploit custom-mongodb-exploit
```

## Monitoring & Observability

### Real-Time Metrics

Access comprehensive system metrics:

- **cAdvisor**: Container resource usage at `http://localhost:9091`
- **Jaeger**: Distributed tracing at `http://localhost:16686`
- **Custom Dashboard**: Performance analytics at `http://localhost:3000`

### Performance Analysis

Generate detailed performance reports:

```bash
# CPU and memory analysis
make analyze-performance

# Network throughput analysis
make analyze-network

# Security incident analysis
make analyze-security
```

### Log Aggregation

Centralized logging with structured output:

```bash
# View aggregated logs
make logs

# Filter by service
make logs SERVICE=authentication

# Export logs for analysis
make export-logs FORMAT=json TIMERANGE=1h
```

## Performance Evaluation

### Scalability Testing

Evaluate system performance across different VM configurations:

```bash
# Test with 3 VMs
make scale-test VMS=3

# Test with 8 VMs  
make scale-test VMS=8

# Generate comparative analysis
make compare-performance
```

### Benchmark Results

Based on extensive testing, Chronark demonstrates:

- **Linear scalability**: Deployment time scales linearly with VM count
- **Multi-cloud consistency**: <70s variation across AWS, GCP, Azure
- **Performance efficiency**: 21% improvement in operation latency with 8 VMs vs 3 VMs
- **Resource optimization**: Better CPU and memory distribution at scale

### Cloud Provider Comparison

Performance benchmarks across major cloud providers:

| Provider | Deployment Time | CPU Efficiency | Memory Usage | Network Latency |
|----------|----------------|----------------|--------------|-----------------|
| AWS      | 193.73s        | 95%           | 90.02 MB     | 12ms           |
| GCP      | 255.05s        | 92%           | 103.06 MB    | 15ms           |
| Azure    | 220.93s        | 94%           | 95.45 MB     | 14ms           |

### Development Setup

```bash
# Clone and setup development environment
git clone https://github.com/PsychoPunkSage/Chronark.git
cd Chronark

# Run tests
make test

# Run security checks
make security-check
```
