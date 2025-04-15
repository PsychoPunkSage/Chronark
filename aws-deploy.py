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
                
            # Ask about authentication method
            if not self.config["manager"].get("auth_method"):
                auth_choice = input(f"Choose authentication method for {self.config['manager']['ip']} (password/keyfile): ")
                self.config["manager"]["auth_method"] = auth_choice.lower()
            
            # Get appropriate credentials based on auth method
            if self.config["manager"]["auth_method"] == "keyfile":
                if not self.config["manager"].get("key_file"):
                    self.config["manager"]["key_file"] = input(f"Enter path to key file for {self.config['manager']['username']}@{self.config['manager']['ip']}: ")
            else:  # Default to password auth
                self.config["manager"]["auth_method"] = "password"
                if not self.config["manager"].get("password"):
                    self.config["manager"]["password"] = getpass(f"Enter password for {self.config['manager']['username']}@{self.config['manager']['ip']}: ")
            
            # Ask for project directory on the remote manager
            if not self.config["manager"].get("project_dir"):
                project_dir = input(f"Enter project directory path on {self.config['manager']['ip']} (default: home directory): ")
                self.config["manager"]["project_dir"] = project_dir if project_dir else f"/home/{self.config['manager']['username']}"
        
        # Validate workers
        if not self.config.get("workers") or len(self.config["workers"]) == 0:
            print("Warning: No worker nodes specified.")
            add_worker = input("Would you like to add a worker? (y/n): ")
            if add_worker.lower() == 'y':
                worker = {}
                worker["ip"] = input("Enter worker IP address: ")
                worker["username"] = input(f"Enter username for {worker['ip']}: ")
                
                # Ask about authentication method
                auth_choice = input(f"Choose authentication method for {worker['ip']} (password/keyfile): ")
                worker["auth_method"] = auth_choice.lower()
                
                if worker["auth_method"] == "keyfile":
                    worker["key_file"] = input(f"Enter path to key file for {worker['username']}@{worker['ip']}: ")
                else:
                    worker["auth_method"] = "password"
                    worker["password"] = getpass(f"Enter password for {worker['username']}@{worker['ip']}: ")
                
                self.config["workers"] = [worker]
        else:
            # Check for missing worker credentials
            for worker in self.config["workers"]:
                if not worker.get("auth_method"):
                    # Detect auth method based on available credentials
                    if worker.get("key_file"):
                        worker["auth_method"] = "keyfile"
                    else:
                        worker["auth_method"] = "password"
                        
                # Ensure credentials are available
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
        if "run_build" not in self.config["stack"]:
            run_build = input("Run build script before deployment? (y/n): ")
            self.config["stack"]["run_build"] = run_build.lower() == 'y'
        if self.config["stack"]["run_build"] and not self.config["stack"].get("build_script"):
            self.config["stack"]["build_script"] = input("Enter build script (default: build-images.sh): ") or "build-images.sh"

    def setup_registry(self):
        """Set up a Docker registry service on the manager node."""
        print("\nSetting up Docker registry service...")

        if self.config["manager"]["type"] == "local":
            try:
                # Check if registry service already exists
                result = subprocess.run("sudo docker service ls --filter name=registry -q", shell=True, capture_output=True, text=True)

                if result.stdout.strip():
                    print("Registry service already exists, skipping creation.")
                    return True
                
                print("Creating registry service on port 5000...")
                cmd = "sudo docker service create --name registry --publish 5000:5000 registry:2"
                subprocess.run(cmd, shell=True, check=True)

                # Wait for registry to be available
                print("Waiting for registry service to be available...")
                for i in range(30):  # Wait up to 30 seconds
                    try:
                        result = subprocess.run("curl -s http://localhost:5000/v2/ > /dev/null", 
                                               shell=True, check=False)
                        if result.returncode == 0:
                            print("Registry service is up and running.")
                            return True
                    except:
                        pass
                    
                    print("Registry not yet available, waiting...")
                    time.sleep(1)

                print("WARNING: Registry service didn't become available in time.")
                print("Continuing anyway, but deployment may fail.")
                return False
                
            except subprocess.CalledProcessError as e:
                print(f"Error setting up registry service: {e}")
                return False
        else:
            try:
                # Create SSH client
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

                # Connect to manager node
                self._connect_ssh(ssh, self.config["manager"])

                # Check if registry service already exists
                if self.config["manager"].get("auth_method") == "keyfile":
                    stdin, stdout, stderr = ssh.exec_command("sudo docker service ls --filter name=registry -q")
                    registry_exists = stdout.read().decode().strip()

                    if registry_exists:
                        print("Registry service already exists, skipping creation.")
                        ssh.close()
                        return True
                    
                    # Create registry service
                    print("Creating registry service on port 5000...")
                    stdin, stdout, stderr = ssh.exec_command(
                        "sudo docker service create --name registry --publish 5000:5000 registry:2"
                    )
                    time.sleep(5)
                    error = stderr.read().decode()
                    if error and "already exists" not in error:
                        print(f"Error creating registry: {error}")
                        ssh.close()
                        return False
                else:
                    channel = ssh.get_transport().open_session()
                    channel.get_pty()
                    channel.exec_command("sudo docker service ls --filter name=registry -q")
                    channel.send(f"{self.config['manager']['password']}\n")
                    time.sleep(2)
                    registry_exists = channel.recv(1024).decode().strip()

                    if registry_exists:
                        print("Registry service already exists, skipping creation.")
                        ssh.close()
                        return True

                    # Create registry service
                    channel = ssh.get_transport().open_session()
                    channel.get_pty()
                    channel.exec_command("sudo docker service create --name registry --publish 5000:5000 registry:2")
                    channel.send(f"{self.config['manager']['password']}\n")
                    time.sleep(5)

                # Wait for registry to be available
                print("Waiting for registry service to be available...")
                for i in range(30):
                    if self.config["manager"].get("auth_method") == "keyfile":
                        stdin, stdout, stderr = ssh.exec_command("curl -s http://localhost:5000/v2/ > /dev/null && echo 'success'")
                        result = stdout.read().decode().strip()
                        if result == "success":
                            print("Registry service is up and running.")
                            ssh.close()
                            return True
                    else:
                        channel = ssh.get_transport().open_session()
                        channel.get_pty()
                        channel.exec_command("curl -s http://localhost:5000/v2/ > /dev/null && echo 'success'")
                        time.sleep(2)
                        result = channel.recv(1024).decode().strip()
                        if "success" in result:
                            print("Registry service is up and running.")
                            ssh.close()
                            return True

                    print(f"Registry not yet available, waiting... ({i+1}/30)")
                    time.sleep(1)

                print("WARNING: Registry service didn't become available in time.")
                print("Continuing anyway, but deployment may fail.")
                ssh.close()
                return False
            except Exception as e:
                print(f"Error setting up registry on remote manager: {e}")
                return False

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
            self._connect_ssh(ssh, self.config["manager"])
            
            # Check if Docker is running
            print("Checking if Docker is running on manager...")
            if self.config["manager"].get("auth_method") == "keyfile":
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
            if self.config["manager"].get("auth_method") == "keyfile":
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
            
            if self.config["manager"].get("auth_method") == "keyfile":
                stdin, stdout, stderr = ssh.exec_command(init_cmd, get_pty=True)
                time.sleep(5)
                init_output = stdout.read().decode()
                init_error = stderr.read().decode()
                print(f"Init output: {init_output}")
                if init_error:
                    print(f"Init error: {init_error}")
                    if "address already in use" in init_error.lower():
                        print("ERROR: The port required for Docker Swarm is already in use.")
                        print("This may indicate another swarm is running or a service is using port 2377.")
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
            if self.config["manager"].get("auth_method") == "keyfile":
                stdin, stdout, stderr = ssh.exec_command("sudo docker swarm join-token worker -q")
                time.sleep(2)
                self.join_token = stdout.read().decode().strip()
                
                # Verify we got a valid token
                if not self.join_token or len(self.join_token) < 10:
                    print("WARNING: Join token appears invalid or empty. Retrying...")
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
            if self.config["manager"].get("auth_method") == "keyfile":
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
            if node_config.get("auth_method") == "keyfile":
                # Connect using key file
                key_path = os.path.expanduser(node_config["key_file"])
                print(f"Connecting to {node_config['ip']} using key file: {key_path}")
                
                # Load private key
                try:
                    # For AWS .pem files, we need to handle them specially
                    if key_path.endswith('.pem'):
                        try:
                            # Try RSA key first (most common for AWS)
                            private_key = paramiko.RSAKey.from_private_key_file(key_path)
                        except Exception as e:
                            print(f"Failed to load as RSA key, trying other formats: {e}")
                            try:
                                # Try other key types if RSA fails
                                private_key = paramiko.Ed25519Key.from_private_key_file(key_path)
                            except:
                                try:
                                    private_key = paramiko.ECDSAKey.from_private_key_file(key_path)
                                except:
                                    # Last resort, try DSS
                                    private_key = paramiko.DSSKey.from_private_key_file(key_path)
                    else:
                        # For non-AWS keys, try standard format detection
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
                if key_path.endswith('.pem') and os.name != 'nt':  # Skip permission check on Windows
                    key_stat = os.stat(key_path)
                    if key_stat.st_mode & 0o077:  # Check if group or others have permissions
                        print(f"WARNING: Permissions for {key_path} are too open. AWS requires permissions of 400.")
                        fix_perms = input("Would you like to fix the permissions now? (y/n): ")
                        if fix_perms.lower() == 'y':
                            os.chmod(key_path, 0o400)
                            print(f"Changed permissions of {key_path} to 400")
                
                # Connect with the key and allow for common connection options
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
            
            # Test sudo access - important for Docker commands
            print(f"Testing sudo access on {node_config['ip']}...")
            if node_config.get("auth_method") == "keyfile":
                # For AWS instances with proper setup, sudo shouldn't require password
                stdin, stdout, stderr = ssh_client.exec_command("sudo -n echo 'sudo test'", get_pty=True)
                result = stdout.read().decode()
                error = stderr.read().decode()
                
                if "password" in error.lower():
                    print("WARNING: This instance requires a sudo password even with key authentication.")
                    print("For AWS instances, you might want to configure passwordless sudo.")
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
            print("5. For AWS instances, ensure you're using the correct key pair for the instance\n")
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
                if worker.get("auth_method") == "keyfile":
                    # For AWS instances, Docker should be able to start without sudo password
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
            if worker.get("auth_method") == "keyfile":
                # For AWS instances, we can use exec_command with sudo without needing interactive password
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

            # Join the swarm - AWS instances need to ensure ports are open in security group
            print("Checking required ports for Docker Swarm...")
            # ports_to_check = [2377, 7946, 4789]
            # for port in ports_to_check:
            #     stdin, stdout, stderr = ssh.exec_command(f"nc -zv {self.manager_ip} {port} 2>&1")
            #     result = stdout.read().decode() + stderr.read().decode()
            #     if "succeeded" not in result.lower() and "open" not in result.lower():
            #         print(f"WARNING: Port {port} does not appear to be accessible on manager {self.manager_ip}")
            #         print("Make sure your AWS security groups allow these ports between instances")
            
            # Join the swarm with longer timeout
            print(f"Joining the swarm with manager {self.manager_ip}...")
            join_command = f"sudo docker swarm join --token {self.join_token} {self.manager_ip}:2377"
            print(f"Executing join command: {join_command}")
            
            if worker.get("auth_method") == "keyfile":
                stdin, stdout, stderr = ssh.exec_command(join_command, get_pty=True)
                # Wait longer for AWS instances
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

            # Verify swarm status - give it more time to join
            print("Verifying swarm status...")
            time.sleep(5)  # Additional wait for swarm status to update
            
            max_retries = 3
            for attempt in range(max_retries):
                if worker.get("auth_method") == "keyfile":
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
            
            print(f"Worker node failed to join swarm after {max_retries} attempts. Last status: {swarm_status}")
            return False

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
            # Set registry information
            registry_host = "localhost:5000"
            self.config["registry"] = registry_host
            print(f"Using local registry at {registry_host}")

            # Check available disk space before building
            df_output = subprocess.check_output("df -h /", shell=True).decode()
            print(f"Current disk usage:\n{df_output}")

            # Extract available space percentage
            available_line = [line for line in df_output.split('\n') if line.strip() and '/' in line][0]
            usage_percent = int(available_line.split()[4].replace('%', ''))

            # Run build script if configured and we have enough space
            if self.config["stack"]["run_build"]:
                if usage_percent > 85:
                    print("WARNING: Disk usage is above 85%. Skipping build to avoid running out of space.")
                    print("Proceeding with deployment using existing images.")

                    # Ask user if they want to continue
                    choice = input("Continue with deployment without building? (y/n): ")
                    if choice.lower() != 'y':
                        print("Deployment aborted by user.")
                        return False
                else:
                    # Check if images already exist
                    existing_images = subprocess.check_output("sudo docker images --format '{{.Repository}}'", shell=True).decode()

                    # If multiple images from our script already exist, ask user if rebuild is necessary
                    registry = self.config.get("registry", "local")
                    if f"{registry}/contacts" in existing_images and f"{registry}/search" in existing_images:
                        rebuild = input("Some images already exist. Rebuild all images? (y/n): ")

                        if rebuild.lower() == 'n':
                            print("Skipping build, using existing images.")
                        else:
                            # Run the build script
                            build_script = self.config["stack"]["build_script"]
                            print(f"Making build script executable: {build_script}")
                            subprocess.run(f"chmod +x {build_script}", shell=True, check=True)

                            print(f"Running build script: {build_script}")
                            subprocess.run(f"./{build_script}", shell=True, check=True)
                    else:
                        # No existing images found, need to build
                        build_script = self.config["stack"]["build_script"]
                        print(f"Making build script executable: {build_script}")
                        subprocess.run(f"chmod +x {build_script}", shell=True, check=True)

                        print(f"Running build script: {build_script}")
                        subprocess.run(f"./{build_script}", shell=True, check=True)

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
            print(f"Error in build and deploy: {e}")
            return False
        
    def _deploy_on_remote_manager(self):
        """Build and deploy stack on remote manager using SSH."""
        try:
            registry_host = f"{self.manager_ip}:5000"
            self.config["registry"] = registry_host
            print(f"Using registry at {registry_host}")
            
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
            
            # Parse disk usage
            usage_line = [line for line in df_output.split('\n') if line.strip() and '/' in line][0]
            usage_percent = int(usage_line.split()[4].replace('%', ''))
            
            # Run build script if configured
            if self.config["stack"]["run_build"]:
                # Warn if disk space is low
                if usage_percent > 85:
                    print(f"WARNING: Disk usage on remote server is at {usage_percent}%. Building may cause 'no space left' errors.")
                    proceed = input("Continue with build? (y/n): ")
                    if proceed.lower() != 'y':
                        print("Skipping build due to disk space concerns.")
                        self.config["stack"]["run_build"] = False
                        
                if self.config["stack"]["run_build"]:
                    build_script = self.config["stack"]["build_script"]
                    
                    # Check if build script exists
                    stdin, stdout, stderr = ssh.exec_command(f"cd {project_dir} && ls -la {build_script}")
                    if "No such file or directory" in stderr.read().decode():
                        print(f"Build script {build_script} not found in {project_dir}")
                        print("Skipping build script execution.")
                        self.config["stack"]["run_build"] = False
                    
                    if self.config["stack"]["run_build"]:
                        # Check if some images already exist
                        stdin, stdout, stderr = ssh.exec_command(f"cd {project_dir} && sudo docker images | grep {self.config.get('registry', 'local')}")
                        existing_images = stdout.read().decode()
                        
                        # If images exist, ask if we should build anyway
                        if existing_images and "REPOSITORY" in existing_images:
                            force_rebuild = input("Some Docker images already exist on the remote server. Rebuild all? (y/n): ")
                            if force_rebuild.lower() != 'y':
                                print("Skipping build, using existing images.")
                                self.config["stack"]["run_build"] = False
                        
                        if self.config["stack"]["run_build"]:
                            # Check if Docker system has enough space
                            stdin, stdout, stderr = ssh.exec_command("sudo docker system df")
                            docker_space = stdout.read().decode()
                            print(f"Docker space usage:\n{docker_space}")
                            
                            # Clean up if needed
                            if usage_percent > 70:
                                clean = input("Run docker system prune to free up space before building? (y/n): ")
                                if clean.lower() == 'y':
                                    print("Cleaning up Docker system...")
                                    if self.config["manager"].get("auth_method") == "keyfile":
                                        stdin, stdout, stderr = ssh.exec_command("sudo docker system prune -f")
                                        time.sleep(5)
                                    else:
                                        channel = ssh.get_transport().open_session()
                                        channel.get_pty()
                                        channel.exec_command("sudo docker system prune -f")
                                        channel.send(f"{self.config['manager']['password']}\n")
                                        time.sleep(5)
                            
                            # Make build script executable
                            print(f"Making build script executable: {build_script}")
                            stdin, stdout, stderr = ssh.exec_command(f"cd {project_dir} && chmod +x {build_script}")
                            time.sleep(1)
                            
                            # Run build script
                            registry = self.config.get('registry', 'local')
                            tag = self.config.get('tag', 'latest')
                            print(f"Running build script: ./{build_script} {registry} {tag}")
                            
                            if self.config["manager"].get("auth_method") == "keyfile":
                                stdin, stdout, stderr = ssh.exec_command(f"cd {project_dir} && ./{build_script} {registry} {tag}", get_pty=True)
                            else:
                                channel = ssh.get_transport().open_session()
                                channel.get_pty()
                                channel.exec_command(f"cd {project_dir} && ./{build_script} {registry} {tag}")
                                if self.config["manager"].get("auth_method") != "keyfile":
                                    channel.send(f"{self.config['manager']['password']}\n")
                            
                            # Allow time for build and provide progress updates
                            print("Build in progress. This may take some time...")
                            
                            # For keyfile auth, we can read output in real-time
                            if self.config["manager"].get("auth_method") == "keyfile":
                                while not stdout.channel.exit_status_ready():
                                    if stdout.channel.recv_ready():
                                        build_output = stdout.channel.recv(1024).decode()
                                        if build_output:
                                            print(build_output, end='')
                                    time.sleep(1)
                            else:
                                # For password auth, we just wait with periodic updates
                                for i in range(6):
                                    print(f"Build in progress... ({i+1}/6)")
                                    time.sleep(10)
                
            # Check if compose file exists
            compose_file = self.config["stack"]["compose_file"]
            stdin, stdout, stderr = ssh.exec_command(f"cd {project_dir} && ls -la {compose_file}")
            if "No such file or directory" in stderr.read().decode():
                print(f"Compose file {compose_file} not found in {project_dir}")
                return False
            
            # Create network overlay
            network_name = self.config["stack"]["network_name"]
            print(f"Creating network overlay: {network_name}")
            if self.config["manager"].get("auth_method") == "keyfile":
                stdin, stdout, stderr = ssh.exec_command(f"cd {project_dir} && sudo docker network create --driver overlay {network_name}")
                time.sleep(3)
                network_output = stdout.read().decode()
                network_error = stderr.read().decode()
                if network_error and "already exists" not in network_error:
                    print(f"Network creation error: {network_error}")
            else:
                channel = ssh.get_transport().open_session()
                channel.get_pty()
                channel.exec_command(f"cd {project_dir} && sudo docker network create --driver overlay {network_name}")
                if self.config["manager"].get("auth_method") != "keyfile":
                    channel.send(f"{self.config['manager']['password']}\n")
                time.sleep(3)
            
            # Deploy stack
            stack_name = self.config["stack"]["name"]
            print(f"Deploying stack {stack_name} with compose file {compose_file}")
            if self.config["manager"].get("auth_method") == "keyfile":
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
                if self.config["manager"].get("auth_method") != "keyfile":
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
                self._connect_ssh(ssh, self.config["manager"])
                
                # Get project directory
                project_dir = self.config["manager"].get("project_dir", f"/home/{self.config['manager']['username']}")
                
                # Check node status
                print("\nVerifying deployment...")
                if self.config["manager"].get("auth_method") == "keyfile":
                    stdin, stdout, stderr = ssh.exec_command(f"cd {project_dir} && sudo docker node ls")
                    time.sleep(2)
                    nodes_output = stdout.read().decode()
                    nodes_error = stderr.read().decode()
                    if nodes_error:
                        print(f"Error retrieving node list: {nodes_error}")
                else:
                    channel = ssh.get_transport().open_session()
                    channel.get_pty()
                    channel.exec_command(f"cd {project_dir} && sudo docker node ls")
                    if self.config["manager"].get("auth_method") != "keyfile":
                        channel.send(f"{self.config['manager']['password']}\n")
                    time.sleep(2)
                    nodes_output = channel.recv(4096).decode()
                
                print("\nDocker Swarm Nodes:")
                print(nodes_output)
                
                # Check services
                if self.config["manager"].get("auth_method") == "keyfile":
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
                    if self.config["manager"].get("auth_method") != "keyfile":
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
                self._connect_ssh(ssh, self.config["manager"])
                
                # Get project directory
                project_dir = self.config["manager"].get("project_dir", f"/home/{self.config['manager']['username']}")
                
                # Remove stack
                print(f"Removing stack {self.config['stack']['name']}...")
                if self.config["manager"].get("auth_method") == "keyfile":
                    stdin, stdout, stderr = ssh.exec_command(f"cd {project_dir} && sudo docker stack rm {self.config['stack']['name']}")
                    time.sleep(5)
                    stack_error = stderr.read().decode()
                    if stack_error:
                        print(f"Stack removal error: {stack_error}")
                else:
                    channel = ssh.get_transport().open_session()
                    channel.get_pty()
                    channel.exec_command(f"cd {project_dir} && sudo docker stack rm {self.config['stack']['name']}")
                    if self.config["manager"].get("auth_method") != "keyfile":
                        channel.send(f"{self.config['manager']['password']}\n")
                    time.sleep(5)
                
                # Wait for stack to be removed
                print("Waiting for stack to be fully removed...")
                time.sleep(10)
                
                # Remove network
                print(f"Removing overlay network {self.config['stack']['network_name']}...")
                if self.config["manager"].get("auth_method") == "keyfile":
                    stdin, stdout, stderr = ssh.exec_command(f"cd {project_dir} && sudo docker network rm {self.config['stack']['network_name']}")
                    time.sleep(3)
                    network_error = stderr.read().decode()
                    if network_error:
                        print(f"Network removal error: {network_error}")
                else:
                    channel = ssh.get_transport().open_session()
                    channel.get_pty()
                    channel.exec_command(f"cd {project_dir} && sudo docker network rm {self.config['stack']['network_name']}")
                    if self.config["manager"].get("auth_method") != "keyfile":
                        channel.send(f"{self.config['manager']['password']}\n")
                    time.sleep(3)
                
                # Leave swarm
                print("Leaving swarm and removing all swarm data...")
                if self.config["manager"].get("auth_method") == "keyfile":
                    stdin, stdout, stderr = ssh.exec_command("sudo docker swarm leave --force")
                    time.sleep(3)
                    swarm_error = stderr.read().decode()
                    if swarm_error:
                        print(f"Swarm leave error: {swarm_error}")
                else:
                    channel = ssh.get_transport().open_session()
                    channel.get_pty()
                    channel.exec_command("sudo docker swarm leave --force")
                    if self.config["manager"].get("auth_method") != "keyfile":
                        channel.send(f"{self.config['manager']['password']}\n")
                    time.sleep(3)
                
                ssh.close()
                return True
            except Exception as e:
                print(f"Error cleaning up remote manager: {e}")
                # return Falsename']}")
                if self.config["manager"].get("auth_method") != "keyfile":
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
                if self.config["manager"].get("auth_method") != "keyfile":
                    channel.send(f"{self.config['manager']['password']}\n")
                time.sleep(3)
                
                # Leave swarm
                channel = ssh.get_transport().open_session()
                channel.get_pty()
                print("Leaving swarm and removing all swarm data...")
                channel.exec_command("sudo docker swarm leave --force")
                if self.config["manager"].get("auth_method") != "keyfile":
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
                self._connect_ssh(ssh, worker)
                
                # Leave swarm
                channel = ssh.get_transport().open_session()
                channel.get_pty()
                channel.exec_command("sudo docker swarm leave --force")
                if worker.get("auth_method") != "keyfile":
                    channel.send(f"{worker['password']}\n")
                time.sleep(3)
                
                # Verify swarm is left
                channel = ssh.get_transport().open_session()
                channel.get_pty()
                channel.exec_command("sudo docker info | grep Swarm")
                if worker.get("auth_method") != "keyfile":
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
        (deployer.setup_registry, "Setting up Docker registry"),
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
