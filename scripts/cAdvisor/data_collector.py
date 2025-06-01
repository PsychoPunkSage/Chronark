import requests
import pandas as pd
import time
from datetime import datetime
import os


class MicroservicesMonitor:
    """Monitor microservices using cAdvisor API."""
    
    def __init__(self, host="localhost", port=9091, output_dir="monitoring_data"):
        """
        Initialize the microservices monitor.
        
        Args:
            host: Hostname where cAdvisor is running
            port: Port where cAdvisor is exposed
            output_dir: Directory to store monitoring data
        """
        self.base_url = f"http://{host}:{port}"
        self.output_dir = output_dir
        
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
    
    def get_all_containers(self):
        """
        Get information about all containers.
        
        Returns:
            Dictionary containing container information
        """
        url = f"{self.base_url}/api/v1.3/containers"
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error getting containers: {e}")
            return {}
    
    def get_docker_containers(self):
        """
        Get Docker containers only.
        
        Returns:
            Dictionary containing Docker container information
        """
        url = f"{self.base_url}/api/v1.3/docker"
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error getting Docker containers: {e}")
            return {}
    
    def collect_container_metrics(self):
        """
        Collect metrics for all Docker containers with proper unit conversions.
        
        Returns:
            DataFrame with container metrics
        """
        containers = self.get_docker_containers()
        if not containers:
            print("No containers found")
            return pd.DataFrame()
        
        metrics = []
        timestamp = datetime.now().isoformat()
        
        for container_id, container_data in containers.items():
            # Skip containers without enough stats for rate calculation
            if 'stats' not in container_data or len(container_data['stats']) < 2:
                continue
            
            # Get the latest two stats for rate calculation
            latest_stats = container_data['stats'][-1]
            prev_stats = container_data['stats'][-2]
            
            # Calculate time delta between stats
            try:
                latest_time = datetime.strptime(latest_stats.get('timestamp', ''), '%Y-%m-%dT%H:%M:%S.%fZ')
                prev_time = datetime.strptime(prev_stats.get('timestamp', ''), '%Y-%m-%dT%H:%M:%S.%fZ')
                time_delta_seconds = (latest_time - prev_time).total_seconds()
                # Use a minimum time delta to avoid division by zero
                if time_delta_seconds <= 0:
                    time_delta_seconds = 1
            except (ValueError, TypeError):
                # If timestamp parsing fails, use a default delta
                time_delta_seconds = 1
            
            # Get container name from aliases
            container_name = "unknown"
            if 'aliases' in container_data and container_data['aliases']:
                container_name = container_data['aliases'][0]
            
            # Extract CPU usage
            cpu_data = latest_stats.get('cpu', {})
            prev_cpu_data = prev_stats.get('cpu', {})
            
            # Get CPU usage values
            cpu_usage = cpu_data.get('usage', {})
            prev_cpu_usage = prev_cpu_data.get('usage', {})
            
            # Calculate total CPU usage in cores (matching cAdvisor UI)
            total_cpu_usage_ns = cpu_usage.get('total', 0)
            prev_total_cpu_usage_ns = prev_cpu_usage.get('total', 0)
            cpu_usage_delta_ns = total_cpu_usage_ns - prev_total_cpu_usage_ns
            cpu_cores = round(cpu_usage_delta_ns / (time_delta_seconds * 1e9), 5)  # Convert to cores
            
            # User and system CPU usage for breakdown (matching cAdvisor UI)
            user_usage_ns = cpu_usage.get('user', 0)
            prev_user_usage_ns = prev_cpu_usage.get('user', 0)
            user_delta_ns = user_usage_ns - prev_user_usage_ns
            user_cores = round(user_delta_ns / (time_delta_seconds * 1e9), 5)
            
            system_usage_ns = cpu_usage.get('system', 0)
            prev_system_usage_ns = prev_cpu_usage.get('system', 0)
            system_delta_ns = system_usage_ns - prev_system_usage_ns
            system_cores = round(system_delta_ns / (time_delta_seconds * 1e9), 5)
            
            # Extract memory usage and convert to MB (matching cAdvisor UI)
            memory_data = latest_stats.get('memory', {})
            memory_usage = memory_data.get('usage', 0)
            memory_usage_mb = round(memory_usage / (1024 * 1024), 5)  # Convert to MB
            
            memory_working_set = memory_data.get('working_set', 0)
            memory_working_set_mb = round(memory_working_set / (1024 * 1024), 5)  # Convert to MB
            
            # Get memory limit and calculate percentage
            memory_limit = memory_data.get('limit', 0)
            memory_limit_mb = round(memory_limit / (1024 * 1024), 5) if memory_limit > 0 else 0
            memory_percent = round((memory_working_set / memory_limit * 100), 5) if memory_limit > 0 else 0
            
            # Extract network usage and calculate throughput (matching cAdvisor UI)
            network_data = latest_stats.get('network', {})
            prev_network_data = prev_stats.get('network', {})
            
            rx_bytes = network_data.get('rx_bytes', 0)
            prev_rx_bytes = prev_network_data.get('rx_bytes', 0)
            rx_bytes_per_second = round((rx_bytes - prev_rx_bytes) / time_delta_seconds, 5)
            
            tx_bytes = network_data.get('tx_bytes', 0)
            prev_tx_bytes = prev_network_data.get('tx_bytes', 0)
            tx_bytes_per_second = round((tx_bytes - prev_tx_bytes) / time_delta_seconds, 5)
            
            # Extract filesystem stats and convert to MB
            filesystem_data = latest_stats.get('filesystem', [])
            total_usage = sum(fs.get('usage', 0) for fs in filesystem_data)
            total_usage_mb = round(total_usage / (1024 * 1024), 5)  # Convert to MB
            
            # Store all metrics (both raw and converted)
            metrics.append({
                'timestamp': timestamp,
                'container_id': container_id,
                'container_name': container_name,
                
                # Raw metrics (original)
                'cpu_usage': total_cpu_usage_ns,
                'memory_usage_bytes': memory_usage,
                'memory_working_set_bytes': memory_working_set,
                'network_rx_bytes': rx_bytes,
                'network_tx_bytes': tx_bytes,
                'filesystem_usage_bytes': total_usage,
                
                # Converted metrics (matching cAdvisor UI)
                'cpu_cores': cpu_cores,
                'cpu_user_cores': user_cores,
                'cpu_system_cores': system_cores,
                'memory_usage_mb': memory_usage_mb,
                'memory_working_set_mb': memory_working_set_mb,
                'memory_limit_mb': memory_limit_mb,
                'memory_percent': memory_percent,
                'network_rx_bytes_per_second': rx_bytes_per_second,
                'network_tx_bytes_per_second': tx_bytes_per_second,
                'filesystem_usage_mb': total_usage_mb
            })
        
        return pd.DataFrame(metrics)
    
    def monitor_continuously(self, interval=60, duration=None):
        """
        Monitor containers continuously.
        
        Args:
            interval: Time between checks in seconds
            duration: Total monitoring duration in seconds (None for indefinite)
        """
        start_time = time.time()
        iteration = 0
        
        while True:
            current_time = time.time()
            elapsed = current_time - start_time
            
            if duration is not None and elapsed > duration:
                print(f"Monitoring completed after {elapsed:.2f} seconds")
                break
            
            print(f"Collecting metrics (iteration {iteration})...")
            metrics_df = self.collect_container_metrics()
            
            if not metrics_df.empty:
                timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                # Save combined metrics to CSV
                combined_csv_filename = f"{self.output_dir}/metrics.csv"
                metrics_df.to_csv(combined_csv_filename, index=False)
                # print(f"Saved combined metrics to {combined_csv_filename}")
                
                # Save individual container metrics to separate CSV files
                self.save_per_container_metrics(metrics_df, timestamp_str)
                
                # Generate and save plots
                # self.generate_plots(metrics_df, timestamp_str)
            
            iteration += 1
            
            # Wait for the next interval
            time_to_sleep = max(0, interval - (time.time() - current_time))
            if time_to_sleep > 0:
                print(f"Waiting {time_to_sleep:.2f} seconds until next collection...")
                time.sleep(time_to_sleep)
    
    def save_per_container_metrics(self, df, timestamp_str):
        """
        Save metrics segregated by container name.
        Appends to a single file per container instead of creating new files.
        
        Args:
            df: DataFrame with metrics
            timestamp_str: Timestamp string for logs
        """
        # Create containers directory if it doesn't exist
        containers_dir = f"{self.output_dir}/containers"
        if not os.path.exists(containers_dir):
            os.makedirs(containers_dir)
        
        # Group by container_name and save each to a separate file
        for container_name, container_df in df.groupby('container_name'):
            # Sanitize container name for filename
            safe_name = container_name.replace('/', '_').replace(':', '_')
            
            # Create container-specific directory if it doesn't exist
            container_dir = f"{containers_dir}/{safe_name}"
            if not os.path.exists(container_dir):
                os.makedirs(container_dir)
                
            # Save to CSV - use a fixed filename that we'll append to
            csv_filename = f"{container_dir}/{safe_name}.csv"
            
            # Check if file exists to handle headers correctly
            file_exists = os.path.isfile(csv_filename)
            
            # Append to CSV if exists, otherwise create new with headers
            container_df.to_csv(csv_filename, 
                               mode='a',  # Append mode
                               index=False,
                               header=not file_exists)  # Only include header if file is new
            
            # print(f"Updated metrics for {container_name} in {csv_filename}")

    def analyze_historical_data(self, pattern="metrics_*.csv"):
        """
        Analyze historical metrics data with converted units.
        
        Args:
            pattern: File pattern to match CSV files
            
        Returns:
            DataFrame with aggregated metrics
        """
        import glob
        
        # Find all matching CSV files
        csv_files = glob.glob(f"{self.output_dir}/{pattern}")
        
        if not csv_files:
            print("No historical data found")
            return pd.DataFrame()
        
        # Load and concatenate all CSV files
        all_data = pd.concat([pd.read_csv(f) for f in csv_files])
        
        # Convert timestamp to datetime
        all_data['timestamp'] = pd.to_datetime(all_data['timestamp'])
        
        # Define aggregation dict based on available columns
        agg_dict = {}
        
        # Add raw metrics (always available)
        agg_dict['cpu_usage'] = ['mean', 'max', 'std']
        agg_dict['memory_usage_bytes'] = ['mean', 'max', 'std']
        agg_dict['network_rx_bytes'] = ['mean', 'max', 'sum']
        agg_dict['network_tx_bytes'] = ['mean', 'max', 'sum']
        agg_dict['filesystem_usage_bytes'] = ['mean', 'max']
        
        # Add converted metrics (if available)
        if 'cpu_cores' in all_data.columns:
            agg_dict['cpu_cores'] = ['mean', 'max', 'std']
        
        if 'memory_usage_mb' in all_data.columns:
            agg_dict['memory_usage_mb'] = ['mean', 'max', 'std']
            agg_dict['memory_working_set_mb'] = ['mean', 'max', 'std']
            agg_dict['memory_percent'] = ['mean', 'max', 'std']
        
        if 'network_rx_bytes_per_second' in all_data.columns:
            agg_dict['network_rx_bytes_per_second'] = ['mean', 'max', 'std']
            agg_dict['network_tx_bytes_per_second'] = ['mean', 'max', 'std']
        
        if 'filesystem_usage_mb' in all_data.columns:
            agg_dict['filesystem_usage_mb'] = ['mean', 'max', 'std']
        
        # Group by container name and calculate statistics
        container_stats = all_data.groupby('container_name').agg(agg_dict)
        
        return container_stats
    
    def analyze_container_historical_data(self, container_name):
        """
        Analyze historical metrics data for a specific container.
        
        Args:
            container_name: Name of the container to analyze
            
        Returns:
            DataFrame with time series data for the specified container
        """
        # Sanitize container name for directory matching
        safe_name = container_name.replace('/', '_').replace(':', '_')
        container_dir = f"{self.output_dir}/containers/{safe_name}"
        
        if not os.path.exists(container_dir):
            # print(f"No historical data found for container: {container_name}")
            return pd.DataFrame()
        
        # Get the single CSV file for this container
        csv_filename = f"{container_dir}/{safe_name}.csv"
        
        if not os.path.exists(csv_filename):
            # print(f"No CSV file found for container: {container_name}")
            return pd.DataFrame()
        
        # Load the CSV file
        container_data = pd.read_csv(csv_filename)
        
        # Convert timestamp to datetime and sort
        container_data['timestamp'] = pd.to_datetime(container_data['timestamp'])
        container_data = container_data.sort_values('timestamp')
        
        return container_data

# Example usage
if __name__ == "__main__":
    # Create a monitor
    monitor = MicroservicesMonitor()
    
    # Option 1: Collect metrics once
    # print("Collecting current metrics...")
    current_metrics = monitor.collect_container_metrics()
    # print(current_metrics)
    
    # Option 2: Monitor continuously for 10 minutes (600 seconds), checking every minute
    # Uncomment the next line to run continuous monitoring
    monitor.monitor_continuously(interval=0.5, duration=600)
    
    # Option 3: Monitor indefinitely, checking every 5 minutes
    # Uncomment the next line to run indefinite monitoring
    # monitor.monitor_continuously(interval=300)
    
    # After collecting some data, you can analyze historical metrics
    # Uncomment the next lines to analyze historical data
    # historical_stats = monitor.analyze_historical_data()
    # print("\nHistorical Container Statistics:")
    # print(historical_stats)
    
    # Analyze data for a specific container
    # container_data = monitor.analyze_container_historical_data("ms-payments")
    # print(f"\nHistorical data for ms-payments:")
    # print(container_data)