"""
Fast Authentication Monitor - Optimized for Real-Time Monitoring
Collects authentication container metrics every 1 second with minimal delays.
"""

import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import pandas as pd
import requests


class FastAuthMonitor:
    """Ultra-fast authentication monitor with aggressive timeouts and parallel collection."""

    def __init__(self, cadvisor_nodes, port=9091):
        self.cadvisor_nodes = cadvisor_nodes
        self.port = port

        # Aggressive timeout settings for speed
        self.timeout = 1.5  # Very short timeout
        self.max_workers = len(cadvisor_nodes)  # One thread per node

        # Create output directory
        os.makedirs("DATA/authentication", exist_ok=True)

        print("⚡ Fast Authentication Monitor")
        print(f"   Nodes: {len(cadvisor_nodes)}")
        print(f"   Timeout: {self.timeout}s per node")
        print(f"   Workers: {self.max_workers}")
        print("   Output: DATA/authentication/fast_auth_metrics.csv")

    def get_auth_containers_fast(self, node_ip):
        """Get auth containers with very short timeout."""
        url = f"http://{node_ip}:{self.port}/api/v1.3/docker"
        try:
            # Super short timeout for speed
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            containers = response.json()

            # Filter for authentication containers only
            auth_containers = {}
            for container_id, container_data in containers.items():
                if "aliases" in container_data and container_data["aliases"]:
                    container_name = container_data["aliases"][0]
                    # Look for authentication in container name
                    if "authentication" in container_name.lower():
                        auth_containers[container_id] = container_data

            return node_ip, auth_containers, True

        except Exception:
            # Return failure but don't print error to keep output clean
            return node_ip, {}, False

    def extract_auth_metrics_fast(
        self, container_id, container_data, timestamp, node_ip
    ):
        """Fast metric extraction for auth containers."""
        try:
            if "stats" not in container_data or len(container_data["stats"]) < 2:
                return None

            latest_stats = container_data["stats"][-1]
            prev_stats = container_data["stats"][-2]

            # Get container name
            container_name = (
                container_data["aliases"][0]
                if container_data.get("aliases")
                else "unknown"
            )

            # Quick time delta calculation
            try:
                latest_time = datetime.strptime(
                    latest_stats.get("timestamp", ""), "%Y-%m-%dT%H:%M:%S.%fZ"
                )
                prev_time = datetime.strptime(
                    prev_stats.get("timestamp", ""), "%Y-%m-%dT%H:%M:%S.%fZ"
                )
                time_delta = (latest_time - prev_time).total_seconds()
                if time_delta <= 0:
                    time_delta = 1
            except:
                time_delta = 1

            # Essential metrics only for speed
            cpu_data = latest_stats.get("cpu", {}).get("usage", {})
            prev_cpu_data = prev_stats.get("cpu", {}).get("usage", {})
            cpu_delta = cpu_data.get("total", 0) - prev_cpu_data.get("total", 0)
            cpu_cores = round(cpu_delta / (time_delta * 1e9), 6)

            # Memory in MB
            memory_mb = round(
                latest_stats.get("memory", {}).get("working_set", 0) / (1024 * 1024), 2
            )

            # Network metrics
            network_data = latest_stats.get("network", {})
            prev_network_data = prev_stats.get("network", {})
            rx_rate = round(
                (network_data.get("rx_bytes", 0) - prev_network_data.get("rx_bytes", 0))
                / time_delta,
                2,
            )
            tx_rate = round(
                (network_data.get("tx_bytes", 0) - prev_network_data.get("tx_bytes", 0))
                / time_delta,
                2,
            )

            return {
                "timestamp": timestamp,
                "node_ip": node_ip,
                "container_id": container_id[:12],
                "container_name": container_name,
                "cpu_cores": cpu_cores,
                "memory_mb": memory_mb,
                "rx_bytes_per_sec": rx_rate,
                "tx_bytes_per_sec": tx_rate,
            }

        except Exception:
            return None

    def collect_auth_metrics_parallel(self):
        """Collect auth metrics using parallel execution for maximum speed."""
        timestamp = datetime.now().isoformat()
        all_metrics = []
        successful_nodes = 0
        failed_nodes = 0

        # Use ThreadPoolExecutor for parallel collection from all nodes
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all requests simultaneously
            future_to_node = {
                executor.submit(self.get_auth_containers_fast, node): node
                for node in self.cadvisor_nodes
            }

            # Collect results as they complete (don't wait for slow nodes)
            for future in as_completed(future_to_node, timeout=self.timeout + 0.5):
                node_ip = future_to_node[future]
                try:
                    node_ip, auth_containers, success = future.result()

                    if success and auth_containers:
                        successful_nodes += 1
                        print(f"✓ {node_ip}: {len(auth_containers)} auth", end=" ")

                        # Extract metrics from auth containers
                        for container_id, container_data in auth_containers.items():
                            metrics = self.extract_auth_metrics_fast(
                                container_id, container_data, timestamp, node_ip
                            )
                            if metrics:
                                all_metrics.append(metrics)
                    else:
                        failed_nodes += 1
                        print(f"✗ {node_ip}", end=" ")

                except Exception:
                    failed_nodes += 1
                    print(f"✗ {node_ip}", end=" ")

        return pd.DataFrame(all_metrics), successful_nodes, failed_nodes

    def monitor_auth_fast(self, interval=1.0, duration=600):
        """Fast authentication monitoring with guaranteed timing intervals."""
        start_time = time.time()
        iteration = 0

        print("\n⚡ Starting FAST Authentication Monitoring")
        print(f"   Target interval: {interval}s")
        print(f"   Duration: {duration}s")
        print(f"   Total iterations: {int(duration / interval)}")
        print("-" * 70)

        while True:
            iteration_start_time = time.time()
            elapsed = iteration_start_time - start_time

            if elapsed > duration:
                print(f"\n✅ Monitoring completed after {elapsed:.1f} seconds")
                break

            # Collect metrics in parallel from all nodes
            print(f"[{elapsed:6.1f}s] Iter {iteration:3d}: ", end="")

            auth_df, successful, failed = self.collect_auth_metrics_parallel()

            if not auth_df.empty:
                # Save to CSV (append mode)
                csv_file = "DATA/authentication/fast_auth_metrics.csv"
                file_exists = os.path.isfile(csv_file)
                auth_df.to_csv(csv_file, mode="a", index=False, header=not file_exists)

                # Calculate real-time stats
                total_containers = len(auth_df)
                avg_cpu = auth_df["cpu_cores"].mean()
                avg_memory = auth_df["memory_mb"].mean()
                total_rx = auth_df["rx_bytes_per_sec"].sum()
                total_tx = auth_df["tx_bytes_per_sec"].sum()

                # Collection timing
                collection_time = time.time() - iteration_start_time

                print(
                    f"| Auth: {total_containers:2d} containers | "
                    f"CPU: {avg_cpu:7.5f} | MEM: {avg_memory:6.1f}MB | "
                    f"Net: {total_rx:6.0f}↓{total_tx:6.0f}↑ | "
                    f"Nodes: {successful}/{len(self.cadvisor_nodes)} | "
                    f"Time: {collection_time:.3f}s"
                )
            else:
                collection_time = time.time() - iteration_start_time
                print(
                    f"| No auth containers found | "
                    f"Nodes: {successful}/{len(self.cadvisor_nodes)} | "
                    f"Time: {collection_time:.3f}s"
                )

            iteration += 1

            # Calculate precise sleep time to maintain exact interval
            total_iteration_time = time.time() - iteration_start_time
            sleep_time = max(0, interval - total_iteration_time)

            # Only sleep if we have time left in the interval
            if sleep_time > 0:
                time.sleep(sleep_time)
            elif total_iteration_time > interval:
                print(f" ⚠️ Slow iteration: {total_iteration_time:.3f}s > {interval}s")

    def get_summary_stats(self):
        """Print summary of collected data."""
        csv_file = "DATA/authentication/fast_auth_metrics.csv"

        if not os.path.exists(csv_file):
            print("No data collected yet.")
            return

        try:
            df = pd.read_csv(csv_file)

            print("\n📊 AUTHENTICATION MONITORING SUMMARY")
            print("=" * 50)
            print(f"Total records: {len(df)}")
            print(f"Unique containers: {df['container_id'].nunique()}")
            print(
                f"Monitoring period: {df['timestamp'].min()} to {df['timestamp'].max()}"
            )
            print(f"Average CPU usage: {df['cpu_cores'].mean():.6f} cores")
            print(f"Average memory usage: {df['memory_mb'].mean():.2f} MB")
            print(f"Peak memory usage: {df['memory_mb'].max():.2f} MB")
            print(f"Data file size: {os.path.getsize(csv_file) / 1024:.1f} KB")

            # Per-node statistics
            print("\nPer-node container distribution:")
            node_counts = (
                df.groupby("node_ip")["container_id"]
                .nunique()
                .sort_values(ascending=False)
            )
            for node, count in node_counts.items():
                print(f"  {node}: {count} containers")

        except Exception as e:
            print(f"Error reading summary: {e}")


# Usage example and main execution
if __name__ == "__main__":
    # Your GCP internal IP addresses
    SWARM_NODES = [
        "10.160.0.8",  # quasar-worker-0
        "10.160.0.9",  # quasar-worker-1
        "10.160.0.10",  # quasar-worker-2
        "10.160.0.21",  # quasar-worker-3
        "10.160.0.12",  # quasar-worker-4
        "10.160.0.20",  # quasar-worker-5
        "10.160.0.16",  # quasar-worker-6
        "10.160.0.22",  # quasar-worker-7
    ]

    # Create the fast monitor
    monitor = FastAuthMonitor(cadvisor_nodes=SWARM_NODES)

    try:
        # Monitor authentication service for 10 minutes with 1-second intervals
        monitor.monitor_auth_fast(interval=1.0, duration=600)

    except KeyboardInterrupt:
        print("\n⚠️  Monitoring stopped by user")

    finally:
        # Show summary of collected data
        monitor.get_summary_stats()
        print("\n💾 Data saved to: DATA/authentication/fast_auth_metrics.csv")
        print("✅ Fast monitoring session completed!")
