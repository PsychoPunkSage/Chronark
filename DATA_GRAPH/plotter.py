import os
import warnings

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

warnings.filterwarnings("ignore")

# Set style for professional plots
plt.style.use("seaborn-v0_8-whitegrid")
sns.set_palette("husl")

# Configuration
plt.rcParams["figure.figsize"] = (12, 8)
plt.rcParams["font.size"] = 12
plt.rcParams["axes.titlesize"] = 14
plt.rcParams["axes.labelsize"] = 12
plt.rcParams["xtick.labelsize"] = 10
plt.rcParams["ytick.labelsize"] = 10
plt.rcParams["legend.fontsize"] = 11


class AuthMicroserviceAnalyzer:
    def __init__(self, base_path="/content/DATA"):
        self.base_path = base_path
        # self.experiments = [
        #     "DATA1000C", "DATA1000L", "DATA1500C", "DATA1500L",
        #     "DATA2000C", "DATA2000L", "DATA2500C", "DATA2500L",
        #     "DATA3000C", "DATA3000L", "DATA4000CB", "DATA4000LB"
        # ]
        self.experiments = [
            "DATA1000C",
            "DATA1000L",
            "DATA1500C",
            "DATA1500L",
            "DATA2000C",
            "DATA2000L",
            "DATA2500C",
            "DATA2500L",
            "DATA3000C",
            "DATA3000L",
        ]

    def load_experiment_data(self, experiment_name):
        """Load and combine data from all nodes for a specific experiment"""
        experiment_path = os.path.join(
            self.base_path, experiment_name, "authentication"
        )

        if not os.path.exists(experiment_path):
            print(f"Warning: Path {experiment_path} does not exist")
            return None

        all_data = []
        node_files = []

        # Get list of CSV files
        for file in os.listdir(experiment_path):
            if file.endswith(".csv") and (
                "node_" in file or "authentication_instance_" in file
            ):
                node_files.append(file)

        print(f"Processing {experiment_name}: Found {len(node_files)} node files")

        for file in node_files:
            file_path = os.path.join(experiment_path, file)
            try:
                # Extract node IP from filename
                if "node_" in file:
                    node_ip = (
                        file.replace("node_", "").replace(".csv", "").replace("_", ".")
                    )
                else:
                    # For newer format files
                    node_ip = file.split("_")[-1].replace(".csv", "").replace("_", ".")

                df = pd.read_csv(file_path)
                df["node_ip"] = node_ip
                df["source_file"] = file
                all_data.append(df)

            except Exception as e:
                print(f"Error reading {file}: {e}")
                continue

        if not all_data:
            print(f"No valid data found for {experiment_name}")
            return None

        # Combine all node data
        combined_df = pd.concat(all_data, ignore_index=True)

        # Convert timestamp to datetime and create relative time
        combined_df["timestamp"] = pd.to_datetime(combined_df["timestamp"])
        min_time = combined_df["timestamp"].min()
        combined_df["relative_time"] = (
            combined_df["timestamp"] - min_time
        ).dt.total_seconds()

        return combined_df

    def create_individual_plots(self, data, experiment_name):
        """Create separate plots for CPU, Memory, and Network"""
        max_time = data["relative_time"].max()

        # Create output directory
        output_dir = experiment_name
        os.makedirs(output_dir, exist_ok=True)

        # Extract experiment details for titles
        user_count = (
            experiment_name.replace("DATA", "")
            .replace("C", "")
            .replace("L", "")
            .replace("B", "")
        )
        operation_type = (
            "Cleanup & Logout" if "C" in experiment_name else "Login & Registration"
        )
        if "B" in experiment_name:
            operation_type += " (Batch)"

        # Aggregate data by time intervals for cleaner visualization
        time_bins = np.linspace(0, max_time, 100)
        data["time_bin"] = pd.cut(data["relative_time"], time_bins)

        # Calculate mean and std for each metric
        binned_data = (
            data.groupby("time_bin")[
                ["cpu_cores", "memory_mb", "rx_bytes_per_sec", "tx_bytes_per_sec"]
            ]
            .agg(["mean", "std"])
            .reset_index()
        )
        binned_data["time_center"] = binned_data["time_bin"].apply(lambda x: x.mid)
        binned_data = binned_data.dropna()

        if len(binned_data) == 0:
            print(f"Warning: No valid binned data for {experiment_name}")
            return

        # 1. CPU Plot
        plt.figure(figsize=(12, 8))
        plt.plot(
            binned_data["time_center"],
            binned_data[("cpu_cores", "mean")],
            color="#e74c3c",
            linewidth=2,
            label="CPU Usage",
        )
        plt.fill_between(
            binned_data["time_center"],
            binned_data[("cpu_cores", "mean")] - binned_data[("cpu_cores", "std")],
            binned_data[("cpu_cores", "mean")] + binned_data[("cpu_cores", "std")],
            color="#e74c3c",
            alpha=0.2,
            label="±1 Std Dev",
        )
        plt.xlabel("Time (seconds)", fontsize=12)
        plt.ylabel("CPU Utilization", fontsize=12)
        plt.title(
            f"CPU Utilization - {user_count} Users ({operation_type})",
            fontsize=14,
            fontweight="bold",
        )
        plt.gca().yaxis.set_major_formatter(
            plt.FuncFormatter(lambda x, p: f"{x * 100:.2f}%")
        )
        plt.grid(True, alpha=0.3)
        plt.legend()
        plt.tight_layout()
        plt.savefig(f"{output_dir}/cpu_utilization.png", dpi=300, bbox_inches="tight")
        plt.close()

        # 2. Memory Plot
        plt.figure(figsize=(12, 8))
        plt.plot(
            binned_data["time_center"],
            binned_data[("memory_mb", "mean")],
            color="#3498db",
            linewidth=2,
            label="Memory Usage",
        )
        plt.fill_between(
            binned_data["time_center"],
            binned_data[("memory_mb", "mean")] - binned_data[("memory_mb", "std")],
            binned_data[("memory_mb", "mean")] + binned_data[("memory_mb", "std")],
            color="#3498db",
            alpha=0.2,
            label="±1 Std Dev",
        )
        plt.xlabel("Time (seconds)", fontsize=12)
        plt.ylabel("Memory Usage (MB)", fontsize=12)
        plt.title(
            f"Memory Usage - {user_count} Users ({operation_type})",
            fontsize=14,
            fontweight="bold",
        )
        plt.grid(True, alpha=0.3)
        plt.legend()
        plt.tight_layout()
        plt.savefig(f"{output_dir}/memory_usage.png", dpi=300, bbox_inches="tight")
        plt.close()

        # 3. Network Plot (RX + TX combined)
        plt.figure(figsize=(12, 8))
        plt.plot(
            binned_data["time_center"],
            binned_data[("rx_bytes_per_sec", "mean")],
            color="#2ecc71",
            linewidth=2,
            label="Network RX",
        )
        plt.plot(
            binned_data["time_center"],
            binned_data[("tx_bytes_per_sec", "mean")],
            color="#f39c12",
            linewidth=2,
            label="Network TX",
        )
        plt.fill_between(
            binned_data["time_center"],
            binned_data[("rx_bytes_per_sec", "mean")]
            - binned_data[("rx_bytes_per_sec", "std")],
            binned_data[("rx_bytes_per_sec", "mean")]
            + binned_data[("rx_bytes_per_sec", "std")],
            color="#2ecc71",
            alpha=0.2,
        )
        plt.fill_between(
            binned_data["time_center"],
            binned_data[("tx_bytes_per_sec", "mean")]
            - binned_data[("tx_bytes_per_sec", "std")],
            binned_data[("tx_bytes_per_sec", "mean")]
            + binned_data[("tx_bytes_per_sec", "std")],
            color="#f39c12",
            alpha=0.2,
        )
        plt.xlabel("Time (seconds)", fontsize=12)
        plt.ylabel("Network Traffic (bytes/sec)", fontsize=12)
        plt.title(
            f"Network Traffic - {user_count} Users ({operation_type})",
            fontsize=14,
            fontweight="bold",
        )
        plt.gca().yaxis.set_major_formatter(
            plt.FuncFormatter(
                lambda x, p: f"{x / 1024:.1f}K"
                if x < 1024 * 1024
                else f"{x / (1024 * 1024):.1f}M"
            )
        )
        plt.grid(True, alpha=0.3)
        plt.legend()
        plt.tight_layout()
        plt.savefig(f"{output_dir}/network_traffic.png", dpi=300, bbox_inches="tight")
        plt.close()

        print(f"✓ Created 3 plots in {output_dir}/ directory")

    def create_summary_stats(self, data, experiment_name):
        """Create summary statistics table and save in experiment folder"""
        output_dir = experiment_name
        os.makedirs(output_dir, exist_ok=True)

        print(f"\n--- Summary Statistics for {experiment_name} ---")

        metrics = ["cpu_cores", "memory_mb", "rx_bytes_per_sec", "tx_bytes_per_sec"]
        stats_data = []

        for metric in metrics:
            stats = {
                "Metric": metric,
                "Mean": data[metric].mean(),
                "Median": data[metric].median(),
                "Std Dev": data[metric].std(),
                "Min": data[metric].min(),
                "Max": data[metric].max(),
                "P95": data[metric].quantile(0.95),
                "P99": data[metric].quantile(0.99),
            }
            stats_data.append(stats)

        stats_df = pd.DataFrame(stats_data)

        # Format the display
        pd.set_option("display.float_format", "{:.4f}".format)
        print(stats_df.to_string(index=False))

        # Save to CSV in experiment folder
        stats_df.to_csv(f"{output_dir}/summary_stats.csv", index=False)
        print(f"✓ Summary statistics saved to {output_dir}/summary_stats.csv")

    def analyze_experiment(self, experiment_name):
        """Analyze a single experiment and create separate plots"""
        print(f"\n=== Analyzing {experiment_name} ===")

        data = self.load_experiment_data(experiment_name)
        if data is None:
            return

        # Extract experiment details
        user_count = (
            experiment_name.replace("DATA", "")
            .replace("C", "")
            .replace("L", "")
            .replace("B", "")
        )
        operation_type = (
            "Cleanup & Logout" if "C" in experiment_name else "Login & Registration"
        )
        if "B" in experiment_name:
            operation_type += " (Batch)"

        print(f"Users: {user_count}, Operation: {operation_type}")
        print(f"Duration: {data['relative_time'].max():.1f} seconds")
        print(f"Total data points: {len(data)}")
        print(f"Nodes involved: {data['node_ip'].nunique()}")

        # Create individual plots
        self.create_individual_plots(data, experiment_name)

        # Create summary statistics
        self.create_summary_stats(data, experiment_name)

    def create_comparison_plot(self):
        """Create comparison plots across all experiments"""
        print("\n=== Creating Comparison Analysis ===")

        comparison_data = []

        for exp in self.experiments:
            data = self.load_experiment_data(exp)
            if data is not None:
                # Calculate aggregate metrics
                user_count = int(
                    exp.replace("DATA", "")
                    .replace("C", "")
                    .replace("L", "")
                    .replace("B", "")
                )
                operation_type = (
                    "Cleanup & Logout" if "C" in exp else "Login & Registration"
                )
                if "B" in exp:
                    operation_type += " (Batch)"

                summary = {
                    "experiment": exp,
                    "user_count": user_count,
                    "operation_type": operation_type,
                    "avg_cpu": data["cpu_cores"].mean(),
                    "avg_memory": data["memory_mb"].mean(),
                    "avg_rx": data["rx_bytes_per_sec"].mean(),
                    "avg_tx": data["tx_bytes_per_sec"].mean(),
                    "max_cpu": data["cpu_cores"].max(),
                    "max_memory": data["memory_mb"].max(),
                    "duration": data["relative_time"].max(),
                }
                comparison_data.append(summary)

        if not comparison_data:
            print("No data available for comparison")
            return

        comp_df = pd.DataFrame(comparison_data)

        # Create comparison plots
        fig, axes = plt.subplots(2, 3, figsize=(24, 16))
        fig.suptitle(
            "Performance Comparison Across All Experiments",
            fontsize=16,
            fontweight="bold",
        )

        # Separate data by operation type
        cleanup_data = comp_df[comp_df["operation_type"].str.contains("Cleanup")]
        login_data = comp_df[comp_df["operation_type"].str.contains("Login")]

        # CPU comparison
        ax = axes[0, 0]
        if not cleanup_data.empty:
            ax.plot(
                cleanup_data["user_count"],
                cleanup_data["avg_cpu"],
                "o-",
                label="Cleanup & Logout",
                linewidth=2,
                markersize=8,
            )
        if not login_data.empty:
            ax.plot(
                login_data["user_count"],
                login_data["avg_cpu"],
                "s-",
                label="Login & Registration",
                linewidth=2,
                markersize=8,
            )
        ax.set_xlabel("Number of Users")
        ax.set_ylabel("Average CPU Utilization")
        ax.set_title("CPU Utilization vs User Count")
        ax.legend()
        ax.grid(True, alpha=0.3)

        # Memory comparison
        ax = axes[0, 1]
        if not cleanup_data.empty:
            ax.plot(
                cleanup_data["user_count"],
                cleanup_data["avg_memory"],
                "o-",
                label="Cleanup & Logout",
                linewidth=2,
                markersize=8,
            )
        if not login_data.empty:
            ax.plot(
                login_data["user_count"],
                login_data["avg_memory"],
                "s-",
                label="Login & Registration",
                linewidth=2,
                markersize=8,
            )
        ax.set_xlabel("Number of Users")
        ax.set_ylabel("Average Memory Usage (MB)")
        ax.set_title("Memory Usage vs User Count")
        ax.legend()
        ax.grid(True, alpha=0.3)

        # Network RX comparison
        ax = axes[0, 2]
        if not cleanup_data.empty:
            ax.plot(
                cleanup_data["user_count"],
                cleanup_data["avg_rx"],
                "o-",
                label="Cleanup & Logout",
                linewidth=2,
                markersize=8,
            )
        if not login_data.empty:
            ax.plot(
                login_data["user_count"],
                login_data["avg_rx"],
                "s-",
                label="Login & Registration",
                linewidth=2,
                markersize=8,
            )
        ax.set_xlabel("Number of Users")
        ax.set_ylabel("Average RX (bytes/sec)")
        ax.set_title("Network RX vs User Count")
        ax.legend()
        ax.grid(True, alpha=0.3)

        # Network TX comparison
        ax = axes[1, 0]
        if not cleanup_data.empty:
            ax.plot(
                cleanup_data["user_count"],
                cleanup_data["avg_tx"],
                "o-",
                label="Cleanup & Logout",
                linewidth=2,
                markersize=8,
            )
        if not login_data.empty:
            ax.plot(
                login_data["user_count"],
                login_data["avg_tx"],
                "s-",
                label="Login & Registration",
                linewidth=2,
                markersize=8,
            )
        ax.set_xlabel("Number of Users")
        ax.set_ylabel("Average TX (bytes/sec)")
        ax.set_title("Network TX vs User Count")
        ax.legend()
        ax.grid(True, alpha=0.3)

        # Duration comparison
        ax = axes[1, 1]
        if not cleanup_data.empty:
            ax.plot(
                cleanup_data["user_count"],
                cleanup_data["duration"],
                "o-",
                label="Cleanup & Logout",
                linewidth=2,
                markersize=8,
            )
        if not login_data.empty:
            ax.plot(
                login_data["user_count"],
                login_data["duration"],
                "s-",
                label="Login & Registration",
                linewidth=2,
                markersize=8,
            )
        ax.set_xlabel("Number of Users")
        ax.set_ylabel("Experiment Duration (seconds)")
        ax.set_title("Experiment Duration vs User Count")
        ax.legend()
        ax.grid(True, alpha=0.3)

        # Resource utilization heatmap
        ax = axes[1, 2]
        # Create a simplified operation type for heatmap
        comp_df["op_simple"] = comp_df["operation_type"].apply(
            lambda x: "Cleanup" if "Cleanup" in x else "Login"
        )
        heatmap_data = comp_df.pivot_table(
            values="avg_cpu", index="user_count", columns="op_simple", fill_value=0
        )
        if not heatmap_data.empty:
            sns.heatmap(heatmap_data, annot=True, fmt=".4f", cmap="YlOrRd", ax=ax)
            ax.set_title("CPU Utilization Heatmap")

        plt.tight_layout()
        plt.savefig("performance_comparison_analysis.png", dpi=300, bbox_inches="tight")
        plt.show()

        # Save comparison data
        comp_df.to_csv("experiment_comparison_summary.csv", index=False)
        print("\nComparison data saved to 'experiment_comparison_summary.csv'")

    def run_complete_analysis(self):
        """Run complete analysis for all experiments"""
        print("Starting comprehensive authentication microservice analysis...")
        print(f"Base path: {self.base_path}")

        # Analyze each experiment individually
        for experiment in self.experiments:
            self.analyze_experiment(experiment)

        # Create comparison analysis
        self.create_comparison_plot()

        print("\n=== Analysis Complete ===")
        print("Generated files:")
        print("- Individual folders with 3 plots each (CPU, Memory, Network)")
        print("- Summary statistics CSV in each folder")
        print("- Comprehensive comparison analysis")


# Usage Instructions


def main():
    """
    Main function to run the analysis

    Before running this script in Google Colab:
    1. Upload your DATA folder to Colab or mount Google Drive
    2. Update the base_path in the analyzer initialization if needed
    3. Run the analysis
    """

    # Initialize analyzer
    # Change the path below to match your data location
    analyzer = AuthMicroserviceAnalyzer(base_path="DATA")

    # Run complete analysis
    analyzer.run_complete_analysis()


# Example of how to run individual experiment analysis


def analyze_single_experiment(experiment_name):
    """Analyze a single experiment"""
    analyzer = AuthMicroserviceAnalyzer(base_path="DATA")
    analyzer.analyze_experiment(experiment_name)


# Uncomment the line below to run the complete analysis
main()

# Or run individual experiments like this:
# analyze_single_experiment("DATA1000C")
