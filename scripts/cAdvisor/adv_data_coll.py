import re
import threading
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests


class OrganizedSwarmMonitor:
    """
    Monitor microservices across Docker Swarm with organized data storage.

    Data Structure:
    DATA/
    ├── authentication/
    │   ├── auth_instance_node1_container123.csv
    │   ├── auth_instance_node2_container456.csv
    │   └── ...
    ├── customer-info/
    │   ├── customer-info_instance_node1_container789.csv
    │   └── ...
    ├── payments/
    └── ...
    """

    def __init__(self, cadvisor_nodes, port=9091, base_dir="DATA"):
        """
        Initialize the organized swarm monitor.

        Args:
            cadvisor_nodes: List of node IPs where cAdvisor is running
            port: cAdvisor port (default: 9091)
            base_dir: Base directory for data storage (default: "DATA")
        """
        self.cadvisor_nodes = cadvisor_nodes
        self.port = port
        self.base_dir = Path(base_dir)

        # Create base DATA directory
        self.base_dir.mkdir(exist_ok=True)

        # Microservices we're interested in (from your service list)
        self.target_services = {
            "authentication",
            "business-lending",
            "contacts",
            "credit-card",
            "customer-activity",
            "customer-info",
            "deposit-account",
            "frontend-1",
            "frontend-2",
            "frontend-3",
            "investment",
            "mortgage",
            "offer-banner",
            "payments",
            "personal-lending",
            "search",
            "wealth-mgmt",
            "opa",
        }

        print(f"Monitoring {len(self.target_services)} microservices")
        print(f"Data will be stored in: {self.base_dir.absolute()}")

    def sanitize_name(self, name):
        """Sanitize container/service name for use in filenames."""
        # Remove problematic characters and replace with underscores
        return re.sub(r"[^\w\-_.]", "_", name)

    def extract_service_name(self, container_name):
        """
        Extract service name from container name.
        Examples:
        - 'my-app_authentication.1.abc123' -> 'authentication'
        - 'my-app_customer-info.2.def456' -> 'customer-info'
        """
        # Remove my-app_ prefix and instance suffix
        if container_name.startswith("my-app_"):
            service_part = container_name[7:]  # Remove 'my-app_'
            # Split by '.' and take the first part
            service_name = service_part.split(".")[0]
            return service_name
        return container_name

    def get_containers_from_node(self, node_ip):
        """Get containers from a specific node."""
        url = f"http://{node_ip}:{self.port}/api/v1.3/docker"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            containers = response.json()
            print(f"✓ {node_ip}: {len(containers)} containers")
            return node_ip, containers
        except Exception as e:
            print(f"✗ {node_ip}: {e}")
            return node_ip, {}

    def get_all_containers(self):
        """Get containers from all nodes in parallel."""
        all_containers = {}

        def fetch_node(node_ip):
            node_ip, containers = self.get_containers_from_node(node_ip)
            all_containers[node_ip] = containers

        # Fetch from all nodes in parallel
        threads = []
        for node in self.cadvisor_nodes:
            t = threading.Thread(target=fetch_node, args=(node,))
            t.start()
            threads.append(t)

        # Wait for completion
        for t in threads:
            t.join()

        return all_containers

    def extract_container_metrics(
        self, container_id, container_data, timestamp, node_ip
    ):
        """Extract metrics from a single container."""
        try:
            # Need at least 2 stats for rate calculation
            if "stats" not in container_data or len(container_data["stats"]) < 2:
                return None

            latest_stats = container_data["stats"][-1]
            prev_stats = container_data["stats"][-2]

            # Get container name
            container_name = "unknown"
            if "aliases" in container_data and container_data["aliases"]:
                container_name = container_data["aliases"][0]

            # Extract service name
            service_name = self.extract_service_name(container_name)

            # Only monitor our target services
            if service_name not in self.target_services:
                return None

            # Calculate time delta
            try:
                latest_time = datetime.strptime(
                    latest_stats.get("timestamp", ""), "%Y-%m-%dT%H:%M:%S.%fZ"
                )
                prev_time = datetime.strptime(
                    prev_stats.get("timestamp", ""), "%Y-%m-%dT%H:%M:%S.%fZ"
                )
                time_delta_seconds = (latest_time - prev_time).total_seconds()
                if time_delta_seconds <= 0:
                    time_delta_seconds = 1
            except:
                time_delta_seconds = 1

            # CPU metrics
            cpu_data = latest_stats.get("cpu", {})
            prev_cpu_data = prev_stats.get("cpu", {})
            cpu_usage = cpu_data.get("usage", {})
            prev_cpu_usage = prev_cpu_data.get("usage", {})

            total_cpu_usage_ns = cpu_usage.get("total", 0)
            prev_total_cpu_usage_ns = prev_cpu_usage.get("total", 0)
            cpu_usage_delta_ns = total_cpu_usage_ns - prev_total_cpu_usage_ns
            cpu_cores = round(cpu_usage_delta_ns /
                              (time_delta_seconds * 1e9), 6)

            # Memory metrics
            memory_data = latest_stats.get("memory", {})
            memory_usage_bytes = memory_data.get("usage", 0)
            memory_usage_mb = round(memory_usage_bytes / (1024 * 1024), 3)
            memory_working_set_bytes = memory_data.get("working_set", 0)
            memory_working_set_mb = round(
                memory_working_set_bytes / (1024 * 1024), 3)

            memory_limit = memory_data.get("limit", 0)
            memory_limit_mb = (
                round(memory_limit / (1024 * 1024),
                      3) if memory_limit > 0 else 0
            )
            memory_percent = (
                round((memory_working_set_bytes / memory_limit * 100), 3)
                if memory_limit > 0
                else 0
            )

            # Network metrics
            network_data = latest_stats.get("network", {})
            prev_network_data = prev_stats.get("network", {})

            rx_bytes = network_data.get("rx_bytes", 0)
            prev_rx_bytes = prev_network_data.get("rx_bytes", 0)
            rx_bytes_per_sec = round(
                (rx_bytes - prev_rx_bytes) / time_delta_seconds, 3)

            tx_bytes = network_data.get("tx_bytes", 0)
            prev_tx_bytes = prev_network_data.get("tx_bytes", 0)
            tx_bytes_per_sec = round(
                (tx_bytes - prev_tx_bytes) / time_delta_seconds, 3)

            # Filesystem metrics
            filesystem_data = latest_stats.get("filesystem", [])
            total_fs_usage = sum(fs.get("usage", 0) for fs in filesystem_data)
            fs_usage_mb = round(total_fs_usage / (1024 * 1024), 3)

            return {
                "timestamp": timestamp,
                "node_ip": node_ip,
                "container_id": container_id[:12],  # Short container ID
                "container_name": container_name,
                "service_name": service_name,
                "cpu_cores": cpu_cores,
                "memory_usage_mb": memory_usage_mb,
                "memory_working_set_mb": memory_working_set_mb,
                "memory_limit_mb": memory_limit_mb,
                "memory_percent": memory_percent,
                "network_rx_bytes_per_sec": rx_bytes_per_sec,
                "network_tx_bytes_per_sec": tx_bytes_per_sec,
                "filesystem_usage_mb": fs_usage_mb,
                "raw_memory_bytes": memory_usage_bytes,
                "raw_network_rx_bytes": rx_bytes,
                "raw_network_tx_bytes": tx_bytes,
            }

        except Exception as e:
            print(f"Error extracting metrics for {container_id}: {e}")
            return None

    def save_container_data(self, metrics_list):
        """
        Save container data organized by service and instance.

        Args:
            metrics_list: List of container metrics dictionaries
        """
        if not metrics_list:
            return

        # Group by service and then by container
        service_containers = {}
        for metric in metrics_list:
            service_name = metric["service_name"]
            container_id = metric["container_id"]
            node_ip = metric["node_ip"]

            if service_name not in service_containers:
                service_containers[service_name] = {}

            # Create unique key for this container instance
            container_key = f"{container_id}_{node_ip}"

            if container_key not in service_containers[service_name]:
                service_containers[service_name][container_key] = []

            service_containers[service_name][container_key].append(metric)

        # Save each container's data to separate CSV files
        for service_name, containers in service_containers.items():
            # Create service directory
            service_dir = self.base_dir / service_name
            service_dir.mkdir(exist_ok=True)

            for container_key, container_metrics in containers.items():
                # Create filename for this container instance
                safe_container_key = self.sanitize_name(container_key)
                csv_filename = (
                    service_dir /
                    f"{service_name}_instance_{safe_container_key}.csv"
                )

                # Convert to DataFrame
                df = pd.DataFrame(container_metrics)

                # Check if file exists to handle headers
                file_exists = csv_filename.exists()

                # Append to CSV
                df.to_csv(csv_filename, mode="a",
                          index=False, header=not file_exists)

    def collect_all_metrics(self):
        """Collect metrics from all nodes and containers."""
        all_node_containers = self.get_all_containers()

        if not all_node_containers:
            print("No containers found across swarm")
            return []

        all_metrics = []
        timestamp = datetime.now().isoformat()

        for node_ip, containers in all_node_containers.items():
            if not containers:
                continue

            for container_id, container_data in containers.items():
                metrics = self.extract_container_metrics(
                    container_id, container_data, timestamp, node_ip
                )
                if metrics:
                    all_metrics.append(metrics)

        return all_metrics

    def monitor_continuously(self, interval=0.5, duration=None):
        """
        Monitor all microservices continuously.

        Args:
            interval: Collection interval in seconds
            duration: Total duration in seconds (None for indefinite)
        """
        start_time = time.time()
        iteration = 0

        print(f"\n{'=' * 70}")
        print("Starting Swarm Monitoring")
        print(f"Nodes: {len(self.cadvisor_nodes)}")
        print(f"Target Services: {len(self.target_services)}")
        print(f"Interval: {interval}s")
        print(f"Duration: {duration}s" if duration else "Duration: Indefinite")
        print(f"Data Directory: {self.base_dir.absolute()}")
        print(f"{'=' * 70}")

        while True:
            current_time = time.time()
            elapsed = current_time - start_time

            if duration is not None and elapsed > duration:
                print(f"\n✓ Monitoring completed after {elapsed:.1f} seconds")
                break

            iteration_start = time.time()
            print(
                f"\n[{elapsed:8.1f}s] Iteration {
                    iteration:4d} - Collecting metrics..."
            )

            # Collect metrics from all containers
            all_metrics = self.collect_all_metrics()

            if all_metrics:
                # Save organized data
                self.save_container_data(all_metrics)

                # Generate summary statistics
                df = pd.DataFrame(all_metrics)
                service_counts = df.groupby("service_name").size()

                print(f"          Total containers monitored: {
                      len(all_metrics)}")
                print(f"          Services active: {len(service_counts)}")

                # Show top 5 services by container count
                top_services = service_counts.head(5)
                for service, count in top_services.items():
                    avg_cpu = df[df["service_name"] ==
                                 service]["cpu_cores"].mean()
                    avg_mem = df[df["service_name"] == service][
                        "memory_working_set_mb"
                    ].mean()
                    print(
                        f"          {service:20s}: {count:2d} containers | "
                        f"CPU: {avg_cpu:6.4f} | MEM: {avg_mem:6.1f} MB"
                    )
            else:
                print("          No target service containers found")

            iteration += 1

            # Calculate sleep time
            collection_time = time.time() - iteration_start
            sleep_time = max(0, interval - collection_time)

            if sleep_time > 0:
                time.sleep(sleep_time)

    def get_data_summary(self):
        """Print a summary of collected data."""
        print(f"\n{'=' * 50}")
        print("DATA COLLECTION SUMMARY")
        print(f"{'=' * 50}")

        if not self.base_dir.exists():
            print("No data directory found.")
            return

        total_files = 0
        total_size = 0

        for service_dir in self.base_dir.iterdir():
            if service_dir.is_dir():
                csv_files = list(service_dir.glob("*.csv"))
                if csv_files:
                    service_size = sum(f.stat().st_size for f in csv_files)
                    total_files += len(csv_files)
                    total_size += service_size

                    print(
                        f"{service_dir.name:20s}: {len(csv_files):3d} files | "
                        f"{service_size / 1024 / 1024:6.2f} MB"
                    )

        print(f"{'=' * 50}")
        print(f"Total: {total_files} files | {
              total_size / 1024 / 1024:.2f} MB")
        print(f"Data location: {self.base_dir.absolute()}")


# Usage Example
if __name__ == "__main__":
    # Replace with your actual node IPs
    # SWARM_NODES = [
    #     "35.200.204.177",  # Your load test target
    #     "35.200.163.35",  # Replace with actual internal IPs
    #     "34.93.68.169",  # of your 8 swarm nodes
    #     "34.100.249.50",
    #     "34.47.195.53",
    #     "34.93.247.5",
    #     "34.47.198.13",
    #     "34.47.210.45",
    # ]
    SWARM_NODES = [
        "10.160.0.8",   # quasar-worker-0
        "10.160.0.9",   # quasar-worker-1
        "10.160.0.10",  # quasar-worker-2
        "10.160.0.21",  # quasar-worker-3
        "10.160.0.12",  # quasar-worker-4
        "10.160.0.20",  # quasar-worker-5
        "10.160.0.16",  # quasar-worker-6
        "10.160.0.22",  # quasar-worker-7
    ]

  # Create monitor
  monitor = OrganizedSwarmMonitor(
       cadvisor_nodes=SWARM_NODES, port=9091, base_dir="DATA"
       )

   try:
        # Monitor for 10 minutes during load test
        monitor.monitor_continuously(interval=0.5, duration=600)
    except KeyboardInterrupt:
        print("\n⚠️  Monitoring stopped by user")
    finally:
        # Show summary of collected data
        monitor.get_data_summary()
