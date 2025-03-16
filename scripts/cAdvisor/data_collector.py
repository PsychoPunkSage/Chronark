import requests
import pandas as pd
import time
import matplotlib.pyplot as plt
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
        Collect metrics for all Docker containers.
        
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
            # Skip containers without stats
            if 'stats' not in container_data or not container_data['stats']:
                continue
            
            # Get the latest stats
            latest_stats = container_data['stats'][-1]
            
            # Get container name from aliases
            container_name = "unknown"
            if 'aliases' in container_data and container_data['aliases']:
                container_name = container_data['aliases'][0]
            
            # Extract CPU usage
            cpu_data = latest_stats.get('cpu', {})
            cpu_usage = cpu_data.get('usage', {})
            total_cpu_usage = cpu_usage.get('total', 0)
            
            # Extract memory usage
            memory_data = latest_stats.get('memory', {})
            memory_usage = memory_data.get('usage', 0)
            memory_working_set = memory_data.get('working_set', 0)
            
            # Extract network usage
            network_data = latest_stats.get('network', {})
            rx_bytes = network_data.get('rx_bytes', 0)
            tx_bytes = network_data.get('tx_bytes', 0)
            
            # Extract filesystem stats
            filesystem_data = latest_stats.get('filesystem', [])
            total_usage = sum(fs.get('usage', 0) for fs in filesystem_data)
            
            metrics.append({
                'timestamp': timestamp,
                'container_id': container_id,
                'container_name': container_name,
                'cpu_usage': total_cpu_usage,
                'memory_usage_bytes': memory_usage,
                'memory_working_set_bytes': memory_working_set,
                'network_rx_bytes': rx_bytes,
                'network_tx_bytes': tx_bytes,
                'filesystem_usage_bytes': total_usage
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
                combined_csv_filename = f"{self.output_dir}/metrics_{timestamp_str}.csv"
                metrics_df.to_csv(combined_csv_filename, index=False)
                print(f"Saved combined metrics to {combined_csv_filename}")
                
                # Save individual container metrics to separate CSV files
                self.save_per_container_metrics(metrics_df, timestamp_str)
                
                # Generate and save plots
                self.generate_plots(metrics_df, timestamp_str)
            
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
            
            print(f"Updated metrics for {container_name} in {csv_filename}")
    
    def generate_plots(self, df, timestamp_str):
        """
        Generate plots from metrics dataframe.
        
        Args:
            df: DataFrame with metrics
            timestamp_str: Timestamp string for filenames
        """
        # CPU usage plot
        plt.figure(figsize=(12, 6))
        cpu_plot = df.sort_values('cpu_usage', ascending=False).plot.bar(
            x='container_name', 
            y='cpu_usage', 
            title='CPU Usage by Container',
            rot=45
        )
        plt.tight_layout()
        plt.savefig(f"{self.output_dir}/cpu_usage_{timestamp_str}.png")
        
        # Memory usage plot
        plt.figure(figsize=(12, 6))
        # Convert to MB for readability
        df['memory_mb'] = df['memory_working_set_bytes'] / (1024 * 1024)
        memory_plot = df.sort_values('memory_mb', ascending=False).plot.bar(
            x='container_name', 
            y='memory_mb', 
            title='Memory Usage (MB) by Container',
            rot=45
        )
        plt.tight_layout()
        plt.savefig(f"{self.output_dir}/memory_usage_{timestamp_str}.png")
        
        # Network usage plot
        plt.figure(figsize=(12, 6))
        # Convert to MB for readability
        df['network_rx_mb'] = df['network_rx_bytes'] / (1024 * 1024)
        df['network_tx_mb'] = df['network_tx_bytes'] / (1024 * 1024)
        network_data = df.sort_values('network_rx_mb', ascending=False)[['container_name', 'network_rx_mb', 'network_tx_mb']]
        network_data.set_index('container_name').plot.bar(
            title='Network Usage (MB) by Container',
            rot=45
        )
        plt.tight_layout()
        plt.savefig(f"{self.output_dir}/network_usage_{timestamp_str}.png")

    def analyze_historical_data(self, pattern="metrics_*.csv"):
        """
        Analyze historical metrics data.
        
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
        
        # Group by container name and calculate statistics
        container_stats = all_data.groupby('container_name').agg({
            'cpu_usage': ['mean', 'max', 'std'],
            'memory_usage_bytes': ['mean', 'max', 'std'],
            'network_rx_bytes': ['mean', 'max', 'sum'],
            'network_tx_bytes': ['mean', 'max', 'sum'],
            'filesystem_usage_bytes': ['mean', 'max']
        })
        
        # Convert bytes to more readable units
        container_stats['memory_usage_bytes', 'mean'] /= (1024 * 1024)  # MB
        container_stats['memory_usage_bytes', 'max'] /= (1024 * 1024)  # MB
        container_stats['memory_usage_bytes', 'std'] /= (1024 * 1024)  # MB
        
        container_stats['network_rx_bytes', 'mean'] /= (1024 * 1024)  # MB
        container_stats['network_rx_bytes', 'max'] /= (1024 * 1024)  # MB
        container_stats['network_rx_bytes', 'sum'] /= (1024 * 1024)  # MB
        
        container_stats['network_tx_bytes', 'mean'] /= (1024 * 1024)  # MB
        container_stats['network_tx_bytes', 'max'] /= (1024 * 1024)  # MB
        container_stats['network_tx_bytes', 'sum'] /= (1024 * 1024)  # MB
        
        container_stats['filesystem_usage_bytes', 'mean'] /= (1024 * 1024)  # MB
        container_stats['filesystem_usage_bytes', 'max'] /= (1024 * 1024)  # MB
        
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
            print(f"No historical data found for container: {container_name}")
            return pd.DataFrame()
        
        # Get the single CSV file for this container
        csv_filename = f"{container_dir}/{safe_name}.csv"
        
        if not os.path.exists(csv_filename):
            print(f"No CSV file found for container: {container_name}")
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
    print("Collecting current metrics...")
    current_metrics = monitor.collect_container_metrics()
    print(current_metrics)
    
    # Option 2: Monitor continuously for 10 minutes (600 seconds), checking every minute
    # Uncomment the next line to run continuous monitoring
    monitor.monitor_continuously(interval=5, duration=600)
    
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