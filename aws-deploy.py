#!/usr/bin/env python3
import time
import paramiko
import subprocess
from getpass import getpass

class SwarmDeployer:
    def __init__(self, worker_ip, worker_username):
        self.worker_ip = worker_ip
        self.worker_username = worker_username
        self.worker_password = None
        self.join_token = None
        self.manager_ip = None

    def get_local_ip(self):
        """Get the local machine's IP address that will be used for Swarm."""
        try:
            # Get IP address that can be reached by the worker
            cmd = "hostname -I | awk '{print $1}'"
            result = subprocess.check_output(cmd, shell=True).decode().strip()
            self.manager_ip = result
            print(f"Local IP address: {self.manager_ip}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error getting local IP: {e}")
            return False

    def init_swarm_manager(self):
        """Initialize Docker Swarm on local machine as manager."""
        try:
            # Leave any existing swarm
            subprocess.run("sudo docker swarm leave --force", shell=True, stderr=subprocess.PIPE)
            
            # Initialize new swarm
            cmd = f"sudo docker swarm init --advertise-addr {self.manager_ip}"
            result = subprocess.check_output(cmd, shell=True).decode()
            
            # Extract join token from output
            cmd = "sudo docker swarm join-token worker -q"
            self.join_token = subprocess.check_output(cmd, shell=True).decode().strip()
            
            print("Successfully initialized swarm on manager node")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error initializing swarm: {e}")
            return False

    def setup_worker_node(self):
        """Configure worker node via SSH and join it to the swarm."""
        try:
            # Create SSH client
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            # Get password if not already set
            if not self.worker_password:
                self.worker_password = getpass(f"Enter password for {self.worker_username}@{self.worker_ip}: ")

            # Connect to worker node
            ssh.connect(self.worker_ip, username=self.worker_username, password=self.worker_password)

            # Create a channel for running sudo commands
            channel = ssh.get_transport().open_session()
            channel.get_pty()  # Request PTY

            # Leave any existing swarm
            channel.exec_command("sudo docker swarm leave --force")
            channel.send(f"{self.worker_password}\n")  # Send password when prompted
            time.sleep(2)

            # Create a new channel for join command
            channel = ssh.get_transport().open_session()
            channel.get_pty()  # Request PTY

            # Join the swarm
            join_command = f"sudo docker swarm join --token {self.join_token} {self.manager_ip}:2377"
            channel.exec_command(join_command)
            channel.send(f"{self.worker_password}\n")  # Send password when prompted

            # Wait for command to complete and check output
            time.sleep(5)

            # Verify the node joined successfully by checking node status
            verify_channel = ssh.get_transport().open_session()
            verify_channel.get_pty()
            verify_channel.exec_command("sudo docker info | grep Swarm")
            verify_channel.send(f"{self.worker_password}\n")
            time.sleep(2)

            output = verify_channel.recv(1024).decode()
            if "active" not in output.lower():
                print(f"Worker node failed to join swarm. Docker info output: {output}")
                return False

            print("Successfully joined worker node to swarm")
            print("Verifying connection...")

            # Check if node can communicate with manager
            test_channel = ssh.get_transport().open_session()
            test_channel.get_pty()
            test_channel.exec_command(f"sudo docker node ls")
            test_channel.send(f"{self.worker_password}\n")
            time.sleep(2)

            test_output = test_channel.recv(1024).decode()
            print(f"Node status: {test_output}")

            ssh.close()
            return True
        except Exception as e:
            print(f"Error setting up worker node: {e}")
            return False  
          
    def build_and_deploy_stack(self):
        """Build images and deploy the stack."""
        try:
            # # Make build script executable
            # subprocess.run("chmod +x build-images.sh", shell=True, check=True)
            
            # # Build images
            # print("Building Docker images...")
            # subprocess.run("./build-images.sh", shell=True, check=True)

            # Network Overlay
            print("Creating network overlay...")
            subprocess.run("sudo docker network create --driver overlay vittmitra", shell=True, check=True)

            # Deploy stack
            print("Deploying stack...")
            subprocess.run("sudo docker stack deploy -c docker-compose-swarm.yml vittmitra", shell=True, check=True)
            
            print("Successfully deployed stack")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error in build and deploy: {e}")
            return False

def main():
    # Configuration
    WORKER_IP = "10.5.30.190"
    WORKER_USERNAME = "psychopunk_sage"  # Replace with actual username
    
    # Create deployer instance
    deployer = SwarmDeployer(WORKER_IP, WORKER_USERNAME)
    
    # Execute deployment steps
    steps = [
        (deployer.get_local_ip, "Getting local IP"),
        (deployer.init_swarm_manager, "Initializing swarm manager"),
        (deployer.setup_worker_node, "Setting up worker node"),
        (deployer.build_and_deploy_stack, "Building and deploying stack")
    ]
    
    # Run each step
    for step_func, step_name in steps:
        print(f"\n=== {step_name} ===")
        if not step_func():
            print(f"Failed at step: {step_name}")
            return
    
    print("\n=== Deployment Complete ===")
    print("To verify deployment, run: docker node ls")

if __name__ == "__main__":
    main()