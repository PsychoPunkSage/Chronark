#!/usr/bin/env python3
import os
import sys
import time
import json
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

        # Manager validation
        if self.config["manager"]["type"] == "remote":
            if not self.config["manager"].get("ip"):
                self.config["manager"]["ip"] = input("Enter manager IP address: ")
            if not self.config["manager"].get("username"):
                self.config["manager"]["username"] = input(f"Enter username for {self.config['manager']['ip']}: ")
                
            # Auth method
            if not self.config["manager"].get("auth_method"):
                auth_choice = input(f"Choose authentication method for {self.config['manager']['ip']} (password/keyfile): ")
                self.config["manager"]["auth_method"] = auth_choice.lower()
            
            # Get credentials
            if self.config["manager"]["auth_method"] == "keyfile":
                if not self.config["manager"].get("key_file"):
                    self.config["manager"]["key_file"] = input(f"Enter path to key file: ")
            else:
                self.config["manager"]["auth_method"] = "password"
                if not self.config["manager"].get("password"):
                    self.config["manager"]["password"] = getpass(f"Enter password for {self.config['manager']['username']}@{self.config['manager']['ip']}: ")
            
            # Project directory
            if not self.config["manager"].get("project_dir"):
                project_dir = input(f"Enter project directory path (default: home directory): ")
                self.config["manager"]["project_dir"] = project_dir if project_dir else f"/home/{self.config['manager']['username']}"
        
        # Validate workers
        if not self.config.get("workers") or len(self.config["workers"]) == 0:
            print("Warning: No worker nodes specified.")
            add_worker = input("Would you like to add a worker? (y/n): ")
            if add_worker.lower() == 'y':
                worker = {}
                worker["ip"] = input("Enter worker IP address: ")
                worker["username"] = input(f"Enter username for {worker['ip']}: ")
                
                auth_choice = input(f"Choose authentication method (password/keyfile): ")
                worker["auth_method"] = auth_choice.lower()
                
                if worker["auth_method"] == "keyfile":
                    worker["key_file"] = input(f"Enter path to key file: ")
                else:
                    worker["auth_method"] = "password"
                    worker["password"] = getpass(f"Enter password for {worker['username']}@{worker['ip']}: ")
                
                self.config["workers"] = [worker]
        else:
            # Check worker credentials
            for worker in self.config["workers"]:
                if not worker.get("auth_method"):
                    if worker.get("key_file"):
                        worker["auth_method"] = "keyfile"
                    else:
                        worker["auth_method"] = "password"
                        
                if worker["auth_method"] == "keyfile" and not worker.get("key_file"):
                    worker["key_file"] = input(f"Enter path to key file for {worker['username']}@{worker['ip']}: ")
                elif worker["auth_method"] == "password" and not worker.get("password"):
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

    def get_manager_ip(self):
        """Get manager IP based on configuration."""
        if self.config["manager"]["type"] == "local":
            if self.config["manager"].get("ip"):
                self.manager_ip = self.config["manager"]["ip"]
                print(f"Using specified local IP address: {self.manager_ip}")
            else:
                try:
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
            self._connect_ssh(ssh, self.config["manager"])
            
            # Check if Docker is running
            print("Checking if Docker is running on manager...")
            if self.config["manager"]["auth_method"] == "keyfile":
                stdin, stdout, stderr = ssh.exec_command("systemctl status docker")
                docker_status = stdout.read().decode()
                if "active (running)" not in docker_status:
                    print("Docker is not running. Starting Docker...")
                    stdin, stdout, stderr = ssh.exec_command("sudo systemctl start docker")
                    time.sleep(3)
            else:
                channel = ssh.get_transport().open_session()
                channel.get_pty()
                channel.exec_command("systemctl status docker")
                channel.send(f"{self.config['manager']['password']}\n")
                time.sleep(2)
                docker_status = channel.recv(1024).decode()
                if "active (running)" not in docker_status:
                    print("Docker is not running. Starting Docker...")
                    channel = ssh.get_transport().open_session()
                    channel.get_pty()
                    channel.exec_command("sudo systemctl start docker")
                    channel.send(f"{self.config['manager']['password']}\n")
                    time.sleep(3)
            
            # Leave any existing swarm
            print("Leaving any existing swarm...")
            if self.config["manager"]["auth_method"] == "keyfile":
                stdin, stdout, stderr = ssh.exec_command("sudo docker swarm leave --force")
                stderr_output = stderr.read().decode()
                if stderr_output and "error" in stderr_output.lower():
                    print(f"Leave error: {stderr_output}")
            else:
                channel = ssh.get_transport().open_session()
                channel.get_pty()
                channel.exec_command("sudo docker swarm leave --force")
                channel.send(f"{self.config['manager']['password']}\n")
            time.sleep(3)
            
            # Initialize new swarm
            print(f"Initializing new swarm on {self.manager_ip}...")
            init_cmd = f"sudo docker swarm init --advertise-addr {self.manager_ip}"
            
            if self.config["manager"]["auth_method"] == "keyfile":
                stdin, stdout, stderr = ssh.exec_command(init_cmd, get_pty=True)
                time.sleep(5)
                init_output = stdout.read().decode()
                init_error = stderr.read().decode()
                print(f"Init output: {init_output}")
                if init_error:
                    print(f"Init error: {init_error}")
                    if "address already in use" in init_error.lower():
                        print("ERROR: The port required for Docker Swarm is already in use.")
                        return False
            else:
                channel = ssh.get_transport().open_session()
                channel.get_pty()
                channel.exec_command(init_cmd)
                channel.send(f"{self.config['manager']['password']}\n")
                time.sleep(5)
                init_output = channel.recv(1024).decode()
                init_error = channel.recv_stderr(1024).decode()
                print(f"Init output: {init_output}")
                if init_error:
                    print(f"Init error: {init_error}")
            
            # Extract join token
            print("Getting worker join token...")
            if self.config["manager"]["auth_method"] == "keyfile":
                stdin, stdout, stderr = ssh.exec_command("sudo docker swarm join-token worker -q")
                time.sleep(2)
                self.join_token = stdout.read().decode().strip()
                
                # Verify valid token
                if not self.join_token or len(self.join_token) < 10:
                    print("WARNING: Join token appears invalid. Retrying...")
                    stdin, stdout, stderr = ssh.exec_command("sudo docker swarm join-token worker -q")
                    time.sleep(3)
                    self.join_token = stdout.read().decode().strip()
            else:
                channel = ssh.get_transport().open_session()
                channel.get_pty()
                channel.exec_command("sudo docker swarm join-token worker -q")
                channel.send(f"{self.config['manager']['password']}\n")
                time.sleep(3)
                self.join_token = channel.recv(1024).decode().strip()
            
            print(f"Join token: {self.join_token}")
            
            # Verify swarm is active
            print("Verifying swarm is active...")
            if self.config["manager"]["auth_method"] == "keyfile":
                stdin, stdout, stderr = ssh.exec_command("sudo docker info | grep Swarm")
                swarm_status = stdout.read().decode()
            else:
                channel = ssh.get_transport().open_session()
                channel.get_pty()
                channel.exec_command("sudo docker info | grep Swarm")
                channel.send(f"{self.config['manager']['password']}\n")
                time.sleep(2)
                swarm_status = channel.recv(1024).decode()
            
            print(f"Swarm status: {swarm_status}")
            if "active" not in swarm_status.lower():
                print("WARNING: Swarm may not be properly initialized.")
            
            ssh.close()
            print("Successfully initialized swarm on remote manager node")
            return True
        except Exception as e:
            print(f"Error initializing remote manager: {e}")
            return False
        
    def _connect_ssh(self, ssh_client, node_config):
        """Connect to a node using SSH with password or key file."""
        try:
            if node_config["auth_method"] == "keyfile":
                # Connect using key file
                key_path = os.path.expanduser(node_config["key_file"])
                print(f"Connecting to {node_config['ip']} using key file: {key_path}")
                
                # Load private key
                try:
                    if key_path.endswith('.pem'):
                        try:
                            private_key = paramiko.RSAKey.from_private_key_file(key_path)
                        except Exception as e:
                            print(f"Failed to load as RSA key, trying other formats: {e}")
                            try:
                                private_key = paramiko.Ed25519Key.from_private_key_file(key_path)
                            except:
                                try:
                                    private_key = paramiko.ECDSAKey.from_private_key_file(key_path)
                                except:
                                    private_key = paramiko.DSSKey.from_private_key_file(key_path)
                    else:
                        try:
                            private_key = paramiko.RSAKey.from_private_key_file(key_path)
                        except:
                            try:
                                private_key = paramiko.Ed25519Key.from_private_key_file(key_path)
                            except:
                                try:
                                    private_key = paramiko.ECDSAKey.from_private_key_file(key_path)
                                except:
                                    private_key = paramiko.DSSKey.from_private_key_file(key_path)
                                    
                except Exception as e:
                    print(f"Error loading key file: {e}")
                    print("Please check that your key file exists and has correct permissions (chmod 400)")
                    raise
                
                # For AWS, verify key permissions
                if key_path.endswith('.pem') and os.name != 'nt':
                    key_stat = os.stat(key_path)
                    if key_stat.st_mode & 0o077:
                        print(f"WARNING: Permissions for {key_path} are too open. AWS requires permissions of 400.")
                        fix_perms = input("Would you like to fix the permissions now? (y/n): ")
                        if fix_perms.lower() == 'y':
                            os.chmod(key_path, 0o400)
                            print(f"Changed permissions of {key_path} to 400")
                
                # Connect with the key
                try:
                    ssh_client.connect(
                        node_config["ip"],
                        username=node_config["username"],
                        pkey=private_key,
                        timeout=10,
                        allow_agent=False,
                        look_for_keys=False,
                        banner_timeout=10
                    )
                except paramiko.SSHException as sshe:
                    print(f"SSH connection failed: {sshe}")
                    print("Attempting connection with alternative options...")
                    ssh_client.connect(
                        node_config["ip"],
                        username=node_config["username"],
                        pkey=private_key,
                        timeout=20,
                        allow_agent=True,
                        look_for_keys=True,
                        banner_timeout=20
                    )
            else:
                # Connect using password
                ssh_client.connect(
                    node_config["ip"],
                    username=node_config["username"],
                    password=node_config["password"],
                    timeout=10
                )
            
            # Test sudo access
            print(f"Testing sudo access on {node_config['ip']}...")
            if node_config["auth_method"] == "keyfile":
                stdin, stdout, stderr = ssh_client.exec_command("sudo -n echo 'sudo test'", get_pty=True)
                result = stdout.read().decode()
                error = stderr.read().decode()
                
                if "password" in error.lower():
                    print("WARNING: This instance requires a sudo password even with key authentication.")
                    sudo_password = input(f"Enter sudo password for {node_config['username']}@{node_config['ip']} (blank to skip): ")
                    if sudo_password:
                        node_config["sudo_password"] = sudo_password
            
            print(f"Successfully connected to {node_config['ip']}")
            return True
        except Exception as e:
            print(f"SSH connection error to {node_config['ip']}: {e}")
            print("\nTroubleshooting tips:")
            print("1. Ensure the host is reachable (ping the IP address)")
            print("2. Verify that port 22 is open in the security group/firewall")
            print("3. Check that the username is correct for the instance")
            print("4. For key-based auth, ensure the key has correct permissions (chmod 400)")
            raise
        
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
            self._connect_ssh(ssh, worker)

            # Check if Docker is running
            print("Checking if Docker is running...")
            stdin, stdout, stderr = ssh.exec_command("systemctl status docker")
            if "active (running)" not in stdout.read().decode():
                print("Docker is not running. Starting Docker...")
                if worker["auth_method"] == "keyfile":
                    stdin, stdout, stderr = ssh.exec_command("sudo systemctl start docker")
                    time.sleep(3)
                else:
                    channel = ssh.get_transport().open_session()
                    channel.get_pty()
                    channel.exec_command("sudo systemctl start docker")
                    channel.send(f"{worker['password']}\n")
                    time.sleep(3)

            # Leave any existing swarm
            print("Leaving any existing swarm...")
            if worker["auth_method"] == "keyfile":
                stdin, stdout, stderr = ssh.exec_command("sudo docker swarm leave --force")
                stderr_output = stderr.read().decode()
                if stderr_output and "error" in stderr_output.lower():
                    print(f"Leave error: {stderr_output}")
            else:
                channel = ssh.get_transport().open_session()
                channel.get_pty()
                channel.exec_command("sudo docker swarm leave --force")
                channel.send(f"{worker['password']}\n")
            time.sleep(3)

            # Join the swarm
            print(f"Joining the swarm with manager {self.manager_ip}...")
            join_command = f"sudo docker swarm join --token {self.join_token} {self.manager_ip}:2377"
            print(f"Executing join command: {join_command}")
            
            if worker["auth_method"] == "keyfile":
                stdin, stdout, stderr = ssh.exec_command(join_command, get_pty=True)
                time.sleep(10)
                join_output = stdout.read().decode()
                join_error = stderr.read().decode()
            else:
                channel = ssh.get_transport().open_session()
                channel.get_pty()
                channel.exec_command(join_command)
                channel.send(f"{worker['password']}\n")
                time.sleep(10)
                join_output = channel.recv(1024).decode()
                join_error = channel.recv_stderr(1024).decode()
            
            print(f"Join output: {join_output}")
            if join_error:
                print(f"Join error: {join_error}")

            # Verify swarm status
            print("Verifying swarm status...")
            time.sleep(5)
            
            max_retries = 3
            for attempt in range(max_retries):
                if worker["auth_method"] == "keyfile":
                    stdin, stdout, stderr = ssh.exec_command("sudo docker info | grep Swarm")
                    swarm_status = stdout.read().decode()
                else:
                    channel = ssh.get_transport().open_session()
                    channel.get_pty()
                    channel.exec_command("sudo docker info | grep Swarm")
                    channel.send(f"{worker['password']}\n")
                    time.sleep(2)
                    swarm_status = channel.recv(1024).decode()
                
                print(f"Swarm status (attempt {attempt+1}): {swarm_status}")
                
                if "active" in swarm_status.lower():
                    print(f"Successfully joined worker {worker['ip']} to swarm")
                    ssh.close()
                    return True
                elif attempt < max_retries - 1:
                    print(f"Worker not active yet, waiting 5 seconds before retry...")
                    time.sleep(5)
            
            print(f"Worker node failed to join swarm after {max_retries} attempts.")
            return False

        except Exception as e:
            print(f"Error setting up worker node {worker['ip']}: {e}")
            return False    
    
    def deploy_stack(self):
        """Deploy the stack."""
        if self.config["manager"]["type"] == "local":
            return self._deploy_on_local_manager()
        else:
            return self._deploy_on_remote_manager()
            
    def _deploy_on_local_manager(self):
        """Deploy stack on local manager."""
        try:
            # Create network overlay
            network_name = self.config["stack"]["network_name"]
            print(f"Creating network overlay: {network_name}")
            try:
                subprocess.run(f"sudo docker network create --driver overlay {network_name}", shell=True, check=True)
            except subprocess.CalledProcessError:
                print(f"Network {network_name} may already exist, continuing...")

            # Deploy stack
            stack_name = self.config["stack"]["name"]
            compose_file = self.config["stack"]["compose_file"]
            print(f"Deploying stack {stack_name} with compose file {compose_file}")
            subprocess.run(f"sudo docker stack deploy -c {compose_file} {stack_name}", shell=True, check=True)

            print("Successfully deployed stack")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error in deployment: {e}")
            return False
        
    def _deploy_on_remote_manager(self):
        """Deploy stack on remote manager using SSH."""
        try:
            # Create SSH client
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Connect to manager node
            self._connect_ssh(ssh, self.config["manager"])
            
            # Get project directory
            project_dir = self.config["manager"].get("project_dir", f"/home/{self.config['manager']['username']}")
            
            # Change to project directory
            print(f"Changing to project directory: {project_dir}")
            stdin, stdout, stderr = ssh.exec_command(f"cd {project_dir} && pwd")
            current_dir = stdout.read().decode().strip()
            error = stderr.read().decode()
            
            if error:
                print(f"Error accessing project directory: {error}")
                return False
                    
            print(f"Working in directory: {current_dir}")
            
            # Check available disk space on remote server
            print("Checking available disk space on remote server...")
            stdin, stdout, stderr = ssh.exec_command(f"df -h /")
            df_output = stdout.read().decode()
            print(f"Current disk usage on remote server:\n{df_output}")
                
            # Check if compose file exists
            compose_file = self.config["stack"]["compose_file"]
            stdin, stdout, stderr = ssh.exec_command(f"cd {project_dir} && ls -la {compose_file}")
            if "No such file or directory" in stderr.read().decode():
                print(f"Compose file {compose_file} not found in {project_dir}")
                return False
            
            # Create network overlay
            network_name = self.config["stack"]["network_name"]
            print(f"Creating network overlay: {network_name}")
            if self.config["manager"]["auth_method"] == "keyfile":
                stdin, stdout, stderr = ssh.exec_command(f"cd {project_dir} && sudo docker network create --driver overlay {network_name}")
                time.sleep(3)
                network_error = stderr.read().decode()
                if network_error and "already exists" not in network_error:
                    print(f"Network creation error: {network_error}")
            else:
                channel = ssh.get_transport().open_session()
                channel.get_pty()
                channel.exec_command(f"cd {project_dir} && sudo docker network create --driver overlay {network_name}")
                channel.send(f"{self.config['manager']['password']}\n")
                time.sleep(3)
            
            # Deploy stack
            stack_name = self.config["stack"]["name"]
            print(f"Deploying stack {stack_name} with compose file {compose_file}")
            if self.config["manager"]["auth_method"] == "keyfile":
                stdin, stdout, stderr = ssh.exec_command(f"cd {project_dir} && sudo docker stack deploy -c {compose_file} {stack_name}")
                time.sleep(5)
                deploy_output = stdout.read().decode()
                deploy_error = stderr.read().decode()
                print(f"Deploy output: {deploy_output}")
                if deploy_error:
                    print(f"Deploy error: {deploy_error}")
            else:
                channel = ssh.get_transport().open_session()
                channel.get_pty()
                channel.exec_command(f"cd {project_dir} && sudo docker stack deploy -c {compose_file} {stack_name}")
                channel.send(f"{self.config['manager']['password']}\n")
                time.sleep(5)
                deploy_output = channel.recv(2048).decode()
                print(f"Deploy output: {deploy_output}")
            
            ssh.close()
            print("Successfully deployed stack")
            return True
        except Exception as e:
            print(f"Error in remote deployment: {e}")
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
                
                # Check for failing services
                print("\nChecking for failing services...")
                result = subprocess.check_output(f"sudo docker stack services {self.config['stack']['name']} --format '{{.Name}} {{.Replicas}}'", shell=True).decode()
                lines = result.split('\n')
                failing_services = []
                
                for line in lines:
                    if not line.strip():
                        continue
                    parts = line.split()
                    if len(parts) >= 2 and '0/' in parts[1]:
                        failing_services.append(parts[0])
                
                if failing_services:
                    print("\nFailing services detected:")
                    for service in failing_services:
                        print(f"- {service}")
                        # Get logs for failing service
                        try:
                            logs = subprocess.check_output(f"sudo docker service logs {service} --tail 10", shell=True).decode()
                            print(f"Last 10 log lines:\n{logs}\n")
                        except:
                            print("Could not retrieve logs")
                else:
                    print("All services appear to be running correctly!")
                
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
                self._connect_ssh(ssh, self.config["manager"])
                
                # Get project directory
                project_dir = self.config["manager"].get("project_dir", f"/home/{self.config['manager']['username']}")
                
                # Check node status
                print("\nVerifying deployment...")
                if self.config["manager"]["auth_method"] == "keyfile":
                    stdin, stdout, stderr = ssh.exec_command("sudo docker node ls")
                    time.sleep(2)
                    nodes_output = stdout.read().decode()
                    nodes_error = stderr.read().decode()
                    if nodes_error:
                        print(f"Error retrieving node list: {nodes_error}")
                else:
                    channel = ssh.get_transport().open_session()
                    channel.get_pty()
                    channel.exec_command("sudo docker node ls")
                    channel.send(f"{self.config['manager']['password']}\n")
                    time.sleep(2)
                    nodes_output = channel.recv(4096).decode()
                
                print("\nDocker Swarm Nodes:")
                print(nodes_output)
                
                # Check services
                if self.config["manager"]["auth_method"] == "keyfile":
                    stdin, stdout, stderr = ssh.exec_command(f"cd {project_dir} && sudo docker stack services {self.config['stack']['name']}")
                    time.sleep(2)
                    services_output = stdout.read().decode()
                    services_error = stderr.read().decode()
                    if services_error:
                        print(f"Error retrieving services: {services_error}")
                else:
                    channel = ssh.get_transport().open_session()
                    channel.get_pty()
                    channel.exec_command(f"cd {project_dir} && sudo docker stack services {self.config['stack']['name']}")
                    channel.send(f"{self.config['manager']['password']}\n")
                    time.sleep(2)
                    services_output = channel.recv(4096).decode()
                
                print("\nStack Services:")
                print(services_output)
                
                # Check for failing services
                print("\nChecking for failing services...")
                if self.config["manager"]["auth_method"] == "keyfile":
                    stdin, stdout, stderr = ssh.exec_command(f"cd {project_dir} && sudo docker stack services {self.config['stack']['name']} --format '{{.Name}} {{.Replicas}}'")
                    time.sleep(2)
                    services_list = stdout.read().decode()
                else:
                    channel = ssh.get_transport().open_session()
                    channel.get_pty()
                    channel.exec_command(f"cd {project_dir} && sudo docker stack services {self.config['stack']['name']} --format '{{.Name}} {{.Replicas}}'")
                    channel.send(f"{self.config['manager']['password']}\n")
                    time.sleep(2)
                    services_list = channel.recv(4096).decode()
                
                lines = services_list.split('\n')
                failing_services = []
                
                for line in lines:
                    if not line.strip():
                        continue
                    parts = line.split()
                    if len(parts) >= 2 and '0/' in parts[1]:
                        failing_services.append(parts[0])
                
                if failing_services:
                    print("\nFailing services detected:")
                    for service in failing_services:
                        print(f"- {service}")
                        # Get logs for failing service
                        try:
                            if self.config["manager"]["auth_method"] == "keyfile":
                                stdin, stdout, stderr = ssh.exec_command(f"sudo docker service logs {service} --tail 10")
                                time.sleep(2)
                                logs = stdout.read().decode()
                                print(f"Last 10 log lines:\n{logs}\n")
                            else:
                                channel = ssh.get_transport().open_session()
                                channel.get_pty()
                                channel.exec_command(f"sudo docker service logs {service} --tail 10")
                                channel.send(f"{self.config['manager']['password']}\n")
                                time.sleep(2)
                                logs = channel.recv(4096).decode()
                                print(f"Last 10 log lines:\n{logs}\n")
                        except Exception as e:
                            print(f"Could not retrieve logs: {e}")
                else:
                    print("All services appear to be running correctly!")
                
                ssh.close()
                return True
            except Exception as e:
                print(f"Error verifying remote deployment: {e}")
                return False
                
    def diagnose_service_failures(self):
        """Diagnose and fix common service failures."""
        print("\n=== Diagnosing Service Failures ===")
        
        if self.config["manager"]["type"] == "local":
            try:
                # Check Docker service health
                print("\nChecking Docker service health...")
                docker_status = subprocess.check_output("sudo systemctl status docker", shell=True).decode()
                if "active (running)" not in docker_status:
                    print("Docker service is not running properly. Attempting to restart...")
                    subprocess.run("sudo systemctl restart docker", shell=True, check=True)
                    time.sleep(5)
                
                # Check resource usage
                print("\nChecking system resource usage...")
                cpu = subprocess.check_output("top -bn1 | grep Cpu | awk '{print $2+$4}'", shell=True).decode().strip()
                mem = subprocess.check_output("free | grep Mem | awk '{print $3/$2 * 100.0}'", shell=True).decode().strip()
                print(f"CPU usage: {cpu}%")
                print(f"Memory usage: {mem}%")
                
                # Check failing services
                print("\nChecking service logs for connection errors...")
                result = subprocess.check_output(f"sudo docker stack services {self.config['stack']['name']} --format '{{{{.Name}}}}'", shell=True).decode()
                services = result.split('\n')
                for service in services:
                    if not service.strip():
                        continue
                    try:
                        logs = subprocess.check_output(f"sudo docker service logs {service} --tail 20 2>&1 | grep -i 'error\\|connection\\|refused\\|failed'", shell=True, stderr=subprocess.PIPE).decode()
                        if logs:
                            print(f"Service {service} has connection issues:")
                            print(logs)
                    except:
                        pass
                
                return True
            except Exception as e:
                print(f"Error during diagnosis: {e}")
                return False
        else:
            # Remote diagnosis
            try:
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                self._connect_ssh(ssh, self.config["manager"])
                
                # Check Docker service
                print("\nChecking Docker service health...")
                if self.config["manager"]["auth_method"] == "keyfile":
                    stdin, stdout, stderr = ssh.exec_command("sudo systemctl status docker")
                    docker_status = stdout.read().decode()
                else:
                    channel = ssh.get_transport().open_session()
                    channel.get_pty()
                    channel.exec_command("sudo systemctl status docker")
                    channel.send(f"{self.config['manager']['password']}\n")
                    time.sleep(2)
                    docker_status = channel.recv(4096).decode()
                
                if "active (running)" not in docker_status:
                    print("Docker service is not running properly. Attempting to restart...")
                    if self.config["manager"]["auth_method"] == "keyfile":
                        stdin, stdout, stderr = ssh.exec_command("sudo systemctl restart docker")
                    else:
                        channel = ssh.get_transport().open_session()
                        channel.get_pty()
                        channel.exec_command("sudo systemctl restart docker")
                        channel.send(f"{self.config['manager']['password']}\n")
                    time.sleep(5)
                
                ssh.close()
                return True
            except Exception as e:
                print(f"Error during remote diagnosis: {e}")
                return False

def main():
    print("=== Docker Swarm Deployer ===")
    
    # Check if config file is provided as argument
    if len(sys.argv) > 1:
        config_file = sys.argv[1]
    else:
        # Check if config file exists in the current directory
        default_config = "gcp-config.json"
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
                    "manager": {"type": "remote"},
                    "workers": [],
                    "stack": {"name": "my-app"}
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
    print("3. Diagnose service failures")
    print("4. Redeploy stack only (no swarm init)")
    operation = input("Enter option (1/2/3/4): ")

    if operation == "2":
        # Execute cleanup
        if deployer.cleanup_deployment():
            print("\n=== Cleanup Complete ===")
        else:
            print("\n=== Cleanup Completed with Issues ===")
        return
    elif operation == "3":
        # Execute diagnosis
        if deployer.diagnose_service_failures():
            print("\n=== Diagnosis Complete ===")
        else:
            print("\n=== Diagnosis Failed ===")
        return
    elif operation == "4":
        # Just redeploy the stack
        print("\n=== Redeploying Stack Only ===")
        deployer.get_manager_ip()
        if deployer.deploy_stack() and deployer.verify_deployment():
            print("\n=== Redeployment Complete ===")
        else:
            print("\n=== Redeployment Failed ===")
        return
    
    # Execute deployment steps
    steps = [
        (deployer.get_manager_ip, "Getting manager IP"),
        (deployer.init_swarm_manager, "Initializing swarm manager"),
        (deployer.setup_worker_nodes, "Setting up worker nodes"),
        (deployer.deploy_stack, "Deploying stack"),
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
    
    # Ask if user wants to diagnose any failures
    check_services = deployer.verify_deployment()
    if check_services:
        diagnose = input("\nWould you like to diagnose any service failures? (y/n): ")
        if diagnose.lower() == 'y':
            deployer.diagnose_service_failures()


if __name__ == "__main__":
    main()