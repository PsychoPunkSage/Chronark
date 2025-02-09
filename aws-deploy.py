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
            subprocess.run("docker swarm leave --force", shell=True, stderr=subprocess.PIPE)
            
            # Initialize new swarm
            cmd = f"docker swarm init --advertise-addr {self.manager_ip}"
            result = subprocess.check_output(cmd, shell=True).decode()
            
            # Extract join token from output
            cmd = "docker swarm join-token worker -q"
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
            
            # Leave any existing swarm
            stdin, stdout, stderr = ssh.exec_command("docker swarm leave --force")
            time.sleep(2)
            
            # Join the swarm
            join_command = f"docker swarm join --token {self.join_token} {self.manager_ip}:2377"
            stdin, stdout, stderr = ssh.exec_command(join_command)
            
            # Wait for command to complete and check output
            time.sleep(5)
            error = stderr.read().decode().strip()
            if error:
                print(f"Error on worker node: {error}")
                return False
                
            print("Successfully joined worker node to swarm")
            ssh.close()
            return True
        except Exception as e:
            print(f"Error setting up worker node: {e}")
            return False

    def build_and_deploy_stack(self):
        """Build images and deploy the stack."""
        try:
            # Make build script executable
            subprocess.run("chmod +x build-images.sh", shell=True, check=True)
            
            # Build images
            print("Building Docker images...")
            subprocess.run("./build-images.sh", shell=True, check=True)
            
            # Deploy stack
            print("Deploying stack...")
            subprocess.run("docker stack deploy -c paste.txt vittmitra", shell=True, check=True)
            
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