import os
import sys
import time
import json
import socket
import paramiko
import subprocess
from getpass import getpass

class SwarmDeployer:
    def __init__(self, config_file):
        """Initialize the deployer with configuration from a JSON file."""
        self.config = self._load_config(config_file)
        self.manager_ip = None
        self.join_token = None
        self._validate_config()
    
    def _load_config(self, config_file):
        """Load configuration from JSON file."""
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            print(f"Successfully loaded configuration from {config_file}")
            return config
        except Exception as e:
            print(f"Error loading configuration from {config_file}: {e}")
            sys.exit(1)

    def _validate_config(self):
        """Validate configuration and prompt for missing data."""
        # Validate manager configuration
        if not self.config.get("manager"):
            choice = input("No manager specified. Use local machine as manager? (y/n): ")
            if choice.lower() == 'y':
                self.config["manager"] = {"type": "local"}
            else:
                print("Cannot proceed without a manager. Exiting.")
                sys.exit(1)

        # Manager validation (both local and remote)
        if self.config["manager"]["type"] == "remote":
            # For remote managers, ensure we have necessary credentials
            if not self.config["manager"].get("ip"):
                self.config["manager"]["ip"] = input("Enter manager IP address: ")
            if not self.config["manager"].get("username"):
                self.config["manager"]["username"] = input(f"Enter username for {self.config['manager']['ip']}: ")
            if not self.config["manager"].get("password"):
                self.config["manager"]["password"] = getpass(f"Enter password for {self.config['manager']['username']}@{self.config['manager']['ip']}: ")
        
        # Validate workers
        if not self.config.get("workers") or len(self.config["workers"]) == 0:
            print("Warning: No worker nodes specified.")
            add_worker = input("Would you like to add a worker? (y/n): ")
            if add_worker.lower() == 'y':
                worker = {}
                worker["ip"] = input("Enter worker IP address: ")
                worker["username"] = input(f"Enter username for {worker['ip']}: ")
                worker["password"] = getpass(f"Enter password for {worker['username']}@{worker['ip']}: ")
                self.config["workers"] = [worker]
        else:
            # Check for missing worker credentials
            for worker in self.config["workers"]:
                if not worker.get("password"):
                    worker["password"] = getpass(f"Enter password for {worker['username']}@{worker['ip']}: ")

        # Validate stack configuration
        if not self.config.get("stack"):
            self.config["stack"] = {}
        if not self.config["stack"].get("name"):
            self.config["stack"]["name"] = input("Enter stack name: ")
        if not self.config["stack"].get("compose_file"):
            self.config["stack"]["compose_file"] = input("Enter Docker Compose file (default: docker-compose-swarm.yml): ") or "docker-compose-swarm.yml"
        if not self.config["stack"].get("network_name"):
            self.config["stack"]["network_name"] = self.config["stack"]["name"]
        if "run_build" not in self.config["stack"]:
            run_build = input("Run build script before deployment? (y/n): ")
            self.config["stack"]["run_build"] = run_build.lower() == 'y'
        if self.config["stack"]["run_build"] and not self.config["stack"].get("build_script"):
            self.config["stack"]["build_script"] = input("Enter build script (default: build-images.sh): ") or "build-images.sh"

    def get_manager_ip(self):
        """Get manager IP based on configuration."""
        if self.config["manager"]["type"] == "local":
            # For local manager, use provided IP or get default IP
            if self.config["manager"].get("ip"):
                self.manager_ip = self.config["manager"]["ip"]
                print(f"Using specified local IP address: {self.manager_ip}")
            else:
                try:
                    # Get default IP address
                    cmd = "hostname -I | awk '{print $1}'"
                    result = subprocess.check_output(cmd, shell=True).decode().strip()
                    self.manager_ip = result
                    print(f"Detected local IP address: {self.manager_ip}")
                except subprocess.CalledProcessError as e:
                    print(f"Error getting local IP: {e}")
                    self.manager_ip = input("Enter local IP address for Swarm: ")
            return True
        else:
            self.manager_ip = self.config["manager"]["ip"]
            print(f"Using remote manager IP: {self.manager_ip}")
            return True    
        
    def init_swarm_manager(self):
        """Initialize Docker Swarm on manager node."""
        if self.config["manager"]["type"] == "local":
            return self._init_local_manager()
        else:
            return self._init_remote_manager()

    def _init_local_manager(self):
        """Initialize Docker Swarm on local machine as manager."""
        try:
            # Leave any existing swarm
            subprocess.run("sudo docker swarm leave --force", shell=True, stderr=subprocess.PIPE)
            
            # Initialize new swarm
            cmd = f"sudo docker swarm init --advertise-addr {self.manager_ip}"
            result = subprocess.check_output(cmd, shell=True).decode()
            
            # Extract join token
            cmd = "sudo docker swarm join-token worker -q"
            self.join_token = subprocess.check_output(cmd, shell=True).decode().strip()
            
            print("Successfully initialized swarm on local manager node")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error initializing swarm: {e}")
            return False

    def _init_remote_manager(self):
        """Initialize Docker Swarm on remote manager using SSH."""
        try:
            # Create SSH client
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Connect to manager node
            ssh.connect(
                self.config["manager"]["ip"],
                username=self.config["manager"]["username"],
                password=self.config["manager"]["password"]
            )
            
            # Leave any existing swarm
            channel = ssh.get_transport().open_session()
            channel.get_pty()
            channel.exec_command("sudo docker swarm leave --force")
            channel.send(f"{self.config['manager']['password']}\n")
            time.sleep(2)
            
            # Initialize new swarm
            channel = ssh.get_transport().open_session()
            channel.get_pty()
            init_cmd = f"sudo docker swarm init --advertise-addr {self.manager_ip}"
            channel.exec_command(init_cmd)
            channel.send(f"{self.config['manager']['password']}\n")
            time.sleep(5)
            
            # Extract join token
            channel = ssh.get_transport().open_session()
            channel.get_pty()
            channel.exec_command("sudo docker swarm join-token worker -q")
            channel.send(f"{self.config['manager']['password']}\n")
            time.sleep(2)
            
            self.join_token = channel.recv(1024).decode().strip()
            
            ssh.close()
            print("Successfully initialized swarm on remote manager node")
            return True
        except Exception as e:
            print(f"Error initializing remote manager: {e}")
            return False
        
    def setup_worker_nodes(self):
        """Configure all worker nodes and join them to the swarm."""
        success = True
        for worker in self.config["workers"]:
            print(f"\n--- Setting up worker: {worker['ip']} ---")
            if not self._setup_single_worker(worker):
                success = False
                print(f"Failed to set up worker: {worker['ip']}")
        return success

    def _setup_single_worker(self, worker):
        """Configure a single worker node via SSH and join it to the swarm."""
        try:
            # Create SSH client
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            # Connect to worker node
            ssh.connect(
                worker["ip"],
                username=worker["username"],
                password=worker["password"]
            )

            # Leave any existing swarm
            channel = ssh.get_transport().open_session()
            channel.get_pty()
            channel.exec_command("sudo docker swarm leave --force")
            channel.send(f"{worker['password']}\n")
            time.sleep(2)

            # Join the swarm
            channel = ssh.get_transport().open_session()
            channel.get_pty()
            join_command = f"sudo docker swarm join --token {self.join_token} {self.manager_ip}:2377"
            print(f"Executing join command: {join_command}")
            channel.exec_command(join_command)
            channel.send(f"{worker['password']}\n")
            time.sleep(5)

            join_output = channel.recv(1024).decode()
            join_error = channel.recv_stderr(1024).decode()
            # print(f"Join output: {join_output}")
            if join_error:
                print(f"Join error: {join_error}")

            # Verify swarm status
            channel = ssh.get_transport().open_session()
            channel.get_pty()
            channel.exec_command("sudo docker info | grep Swarm")
            channel.send(f"{worker['password']}\n")
            time.sleep(2)

            swarm_status = channel.recv(1024).decode()
            if "active" not in swarm_status.lower():
                print(f"Worker node failed to join swarm. Docker info output: {swarm_status}")
                return False

            print(f"Successfully joined worker {worker['ip']} to swarm")
            ssh.close()
            return True

        except Exception as e:
            print(f"Error setting up worker node {worker['ip']}: {e}")
            return False    
        
    def build_and_deploy_stack(self):
        """Build images and deploy the stack."""
        if self.config["manager"]["type"] == "local":
            return self._deploy_on_local_manager()
        else:
            return self._deploy_on_remote_manager()

    def _deploy_on_local_manager(self):
        """Build and deploy stack on local manager."""
        try:
            # Run build script if configured
            if self.config["stack"]["run_build"]:
                build_script = self.config["stack"]["build_script"]
                print(f"Making build script executable: {build_script}")
                subprocess.run(f"chmod +x {build_script}", shell=True, check=True)
                
                print(f"Running build script: {build_script}")
                subprocess.run(f"./{build_script}", shell=True, check=True)

            # Create network overlay
            network_name = self.config["stack"]["network_name"]
            print(f"Creating network overlay: {network_name}")
            subprocess.run(f"sudo docker network create --driver overlay {network_name}", shell=True, check=True)

            # Deploy stack
            stack_name = self.config["stack"]["name"]
            compose_file = self.config["stack"]["compose_file"]
            print(f"Deploying stack {stack_name} with compose file {compose_file}")
            subprocess.run(f"sudo docker stack deploy -c {compose_file} {stack_name}", shell=True, check=True)
            
            print("Successfully deployed stack")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error in build and deploy: {e}")
            return False

    def _deploy_on_remote_manager(self):
        """Build and deploy stack on remote manager using SSH."""
        try:
            # Create SSH client
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Connect to manager node
            ssh.connect(
                self.config["manager"]["ip"],
                username=self.config["manager"]["username"],
                password=self.config["manager"]["password"]
            )
            
            # Run build script if configured
            if self.config["stack"]["run_build"]:
                build_script = self.config["stack"]["build_script"]
                
                # Make build script executable
                channel = ssh.get_transport().open_session()
                channel.get_pty()
                channel.exec_command(f"chmod +x {build_script}")
                channel.send(f"{self.config['manager']['password']}\n")
                time.sleep(2)
                
                # Run build script
                channel = ssh.get_transport().open_session()
                channel.get_pty()
                channel.exec_command(f"./{build_script}")
                channel.send(f"{self.config['manager']['password']}\n")
                time.sleep(10)  # Allow time for build
                
                build_output = channel.recv(4096).decode()
                print(f"Build output: {build_output}")
            
            # Create network overlay
            network_name = self.config["stack"]["network_name"]
            channel = ssh.get_transport().open_session()
            channel.get_pty()
            channel.exec_command(f"sudo docker network create --driver overlay {network_name}")
            channel.send(f"{self.config['manager']['password']}\n")
            time.sleep(3)
            
            # Deploy stack
            stack_name = self.config["stack"]["name"]
            compose_file = self.config["stack"]["compose_file"]
            channel = ssh.get_transport().open_session()
            channel.get_pty()
            channel.exec_command(f"sudo docker stack deploy -c {compose_file} {stack_name}")
            channel.send(f"{self.config['manager']['password']}\n")
            time.sleep(5)
            
            deploy_output = channel.recv(2048).decode()
            print(f"Deploy output: {deploy_output}")
            
            ssh.close()
            print("Successfully deployed stack")
            return True
        except Exception as e:
            print(f"Error in remote build and deploy: {e}")
            return False
        
    def verify_deployment(self):
        """Verify that the deployment was successful."""
        if self.config["manager"]["type"] == "local":
            try:
                print("\nVerifying deployment...")
                result = subprocess.check_output("sudo docker node ls", shell=True).decode()
                print("\nDocker Swarm Nodes:")
                print(result)
                
                result = subprocess.check_output(f"sudo docker stack services {self.config['stack']['name']}", shell=True).decode()
                print("\nStack Services:")
                print(result)
                return True
            except subprocess.CalledProcessError as e:
                print(f"Error verifying deployment: {e}")
                return False
        else:
            try:
                # Create SSH client
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                
                # Connect to manager node
                ssh.connect(
                    self.config["manager"]["ip"],
                    username=self.config["manager"]["username"],
                    password=self.config["manager"]["password"]
                )
                
                # Check node status
                channel = ssh.get_transport().open_session()
                channel.get_pty()
                channel.exec_command("sudo docker node ls")
                channel.send(f"{self.config['manager']['password']}\n")
                time.sleep(2)
                
                nodes_output = channel.recv(4096).decode()
                print("\nDocker Swarm Nodes:")
                print(nodes_output)
                
                # Check services
                channel = ssh.get_transport().open_session()
                channel.get_pty()
                channel.exec_command(f"sudo docker stack services {self.config['stack']['name']}")
                channel.send(f"{self.config['manager']['password']}\n")
                time.sleep(2)
                
                services_output = channel.recv(4096).decode()
                print("\nStack Services:")
                print(services_output)
                
                ssh.close()
                return True
            except Exception as e:
                print(f"Error verifying remote deployment: {e}")
                return False
            
    def cleanup_deployment(self):
        """Remove all traces of the deployment and revert nodes to pre-deployment state."""
        print("\n=== Cleaning Up Deployment ===")
        
        # Clean up manager first
        manager_cleaned = self._cleanup_manager()
        
        # Clean up worker nodes
        workers_cleaned = self._cleanup_workers()
        
        if manager_cleaned and workers_cleaned:
            print("Cleanup completed successfully!")
            return True
        else:
            print("Cleanup completed with some issues.")
            return False
    
    def _cleanup_manager(self):
        """Clean up the manager node."""
        print("Cleaning up manager node...")
        
        if self.config["manager"]["type"] == "local":
            try:
                # Remove stack
                print(f"Removing stack {self.config['stack']['name']}...")
                subprocess.run(f"sudo docker stack rm {self.config['stack']['name']}", 
                              shell=True, check=False)
                
                # Wait for stack to be removed
                print("Waiting for stack to be fully removed...")
                time.sleep(10)
                
                # Remove overlay network
                print(f"Removing overlay network {self.config['stack']['network_name']}...")
                subprocess.run(f"sudo docker network rm {self.config['stack']['network_name']}", 
                              shell=True, check=False)
                
                # Leave swarm (forces removal of all data)
                print("Leaving swarm and removing all swarm data...")
                subprocess.run("sudo docker swarm leave --force", 
                              shell=True, check=False)
                
                return True
            except Exception as e:
                print(f"Error cleaning up manager: {e}")
                return False
        else:
            # Remote manager
            try:
                # Create SSH client
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                
                # Connect to manager node
                ssh.connect(
                    self.config["manager"]["ip"],
                    username=self.config["manager"]["username"],
                    password=self.config["manager"]["password"]
                )
                
                # Remove stack
                channel = ssh.get_transport().open_session()
                channel.get_pty()
                print(f"Removing stack {self.config['stack']['name']}...")
                channel.exec_command(f"sudo docker stack rm {self.config['stack']['name']}")
                channel.send(f"{self.config['manager']['password']}\n")
                time.sleep(5)
                
                # Wait for stack to be removed
                print("Waiting for stack to be fully removed...")
                time.sleep(10)
                
                # Remove network
                channel = ssh.get_transport().open_session()
                channel.get_pty()
                print(f"Removing overlay network {self.config['stack']['network_name']}...")
                channel.exec_command(f"sudo docker network rm {self.config['stack']['network_name']}")
                channel.send(f"{self.config['manager']['password']}\n")
                time.sleep(3)
                
                # Leave swarm
                channel = ssh.get_transport().open_session()
                channel.get_pty()
                print("Leaving swarm and removing all swarm data...")
                channel.exec_command("sudo docker swarm leave --force")
                channel.send(f"{self.config['manager']['password']}\n")
                time.sleep(3)
                
                ssh.close()
                return True
            except Exception as e:
                print(f"Error cleaning up remote manager: {e}")
                return False
    
    def _cleanup_workers(self):
        """Clean up all worker nodes."""
        print("Cleaning up worker nodes...")
        
        success = True
        for worker in self.config["workers"]:
            print(f"Cleaning up worker: {worker['ip']}...")
            
            try:
                # Create SSH client
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                
                # Connect to worker node
                ssh.connect(
                    worker["ip"],
                    username=worker["username"],
                    password=worker["password"]
                )
                
                # Leave swarm
                channel = ssh.get_transport().open_session()
                channel.get_pty()
                channel.exec_command("sudo docker swarm leave --force")
                channel.send(f"{worker['password']}\n")
                time.sleep(3)
                
                # Verify swarm is left
                channel = ssh.get_transport().open_session()
                channel.get_pty()
                channel.exec_command("sudo docker info | grep Swarm")
                channel.send(f"{worker['password']}\n")
                time.sleep(2)
                
                swarm_status = channel.recv(1024).decode()
                if "inactive" not in swarm_status.lower():
                    print(f"Warning: Worker {worker['ip']} may still be in swarm mode")
                    success = False
                
                ssh.close()
                print(f"Worker {worker['ip']} cleaned up successfully")
                
            except Exception as e:
                print(f"Error cleaning up worker {worker['ip']}: {e}")
                success = False
        
        return success


def main():
    print("=== Docker Swarm Deployer ===")
    
    # Check if config file is provided as argument
    if len(sys.argv) > 1:
        config_file = sys.argv[1]
    else:
        # Check if config file exists in the current directory
        default_config = "aws-config.json"
        if os.path.exists(default_config):
            use_default = input(f"Use existing config file '{default_config}'? (y/n): ")
            config_file = default_config if use_default.lower() == 'y' else input("Enter config file path: ")
        else:
            print("No configuration file found.")
            create_new = input("Create a new configuration? (y/n): ")
            if create_new.lower() == 'y':
                config_file = default_config
                # Create minimal config
                minimal_config = {
                    "manager": {"type": "local"},
                    "workers": [],
                    "stack": {}
                }
                with open(config_file, 'w') as f:
                    json.dump(minimal_config, f, indent=2)
                print(f"Created minimal configuration file: {config_file}")
            else:
                print("Cannot proceed without configuration. Exiting.")
                sys.exit(1)
    
    # Create deployer instance
    deployer = SwarmDeployer(config_file)

    # Ask user what operation to perform
    print("\nSelect operation:")
    print("1. Deploy Docker Swarm")
    print("2. Clean up Docker Swarm (revert to pre-deployment state)")
    operation = input("Enter option (1/2): ")

    if operation == "2":
        # Execute cleanup
        if deployer.cleanup_deployment():
            print("\n=== Cleanup Complete ===")
        else:
            print("\n=== Cleanup Completed with Issues ===")
        return
    
    # Execute deployment steps
    steps = [
        (deployer.get_manager_ip, "Getting manager IP"),
        (deployer.init_swarm_manager, "Initializing swarm manager"),
        (deployer.setup_worker_nodes, "Setting up worker nodes"),
        (deployer.build_and_deploy_stack, "Building and deploying stack"),
        (deployer.verify_deployment, "Verifying deployment")
    ]
    
    # Run each step
    for step_func, step_name in steps:
        print(f"\n=== {step_name} ===")
        if not step_func():
            print(f"Failed at step: {step_name}")
            choice = input("Continue anyway? (y/n): ")
            if choice.lower() != 'y':
                return
    
    print("\n=== Deployment Complete ===")


if __name__ == "__main__":
    main()