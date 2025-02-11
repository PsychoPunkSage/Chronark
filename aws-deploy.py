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
            # Get IP address from the physical network interface <Specific to PsychoPunkSage>
            cmd = "ip addr show enx0c37964e6574 | grep -w inet | awk '{print $2}' | cut -d/ -f1"
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

            # # Test connectivity to manager
            # print(f"Testing connectivity to manager node ({self.manager_ip})...")

            # # Test ping
            # channel = ssh.get_transport().open_session()
            # channel.get_pty()
            # channel.exec_command(f"ping -c 1 {self.manager_ip}")
            # time.sleep(3)
            # ping_result = channel.recv(1024).decode()
            # print(f"Ping test result:\n{ping_result}")

            # # Test Docker port
            # channel = ssh.get_transport().open_session()
            # channel.get_pty()
            # channel.exec_command(f"nc -zv {self.manager_ip} 2377")
            # time.sleep(2)
            # port_result = channel.recv(1024).decode()
            # print(f"Port 2377 test result:\n{port_result}")

            # Leave any existing swarm
            channel = ssh.get_transport().open_session()
            channel.get_pty()
            channel.exec_command("sudo docker swarm leave --force")
            channel.send(f"{self.worker_password}\n")
            time.sleep(2)

            # Join the swarm
            channel = ssh.get_transport().open_session()
            channel.get_pty()
            join_command = f"sudo docker swarm join --token {self.join_token} {self.manager_ip}:2377"
            print(f"Executing join command: {join_command}")
            channel.exec_command(join_command)
            channel.send(f"{self.worker_password}\n")
            time.sleep(5)

            join_output = channel.recv(1024).decode()
            join_error = channel.recv_stderr(1024).decode()
            print(f"Join output: {join_output}")
            if join_error:
                print(f"Join error: {join_error}")

            # Verify swarm status
            channel = ssh.get_transport().open_session()
            channel.get_pty()
            channel.exec_command("sudo docker info | grep Swarm")
            channel.send(f"{self.worker_password}\n")
            time.sleep(2)

            swarm_status = channel.recv(1024).decode()
            if "active" not in swarm_status.lower():
                print(f"Worker node failed to join swarm. Docker info output: {swarm_status}")
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
    WORKER_USERNAME = "psychopunk_sage"
    
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