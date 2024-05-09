# -*- mode: ruby -*-
# vi: set ft=ruby :

$install_docker_script = <<-SCRIPT
echo "Installing dependencies ..."
sudo apt-get update
echo "Installing Docker..."
curl -sSL https://get.docker.com/ | sh
sudo usermod -aG docker vagrant
SCRIPT

BOX_NAME = "ubuntu/jammy64"
MEMORY = "2048"
CPUS = 2
MANAGERS = 1
MANAGER_IP = "192.168.56.1"
WORKERS = 2
WORKER_IP = "192.168.56.10"
VAGRANTFILE_API_VERSION = "2"

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|
    # Common setup
    config.vm.box = BOX_NAME
    config.vm.synced_folder ".", "/vagrant"
    config.vm.provision "shell", inline: $install_docker_script, privileged: true
    config.vm.provider "virtualbox" do |vb|
      vb.memory = MEMORY
      vb.cpus = CPUS
    end

    # Setup Manager Nodes
    (1..MANAGERS).each do |i|
        config.vm.define "manager0#{i}" do |manager|
            manager.vm.network "private_network", ip: "#{MANAGER_IP}#{i}"
            manager.vm.hostname = "manager0#{i}"
            if i == 1
                # Only configure port to host for first Manager VM
                manager.vm.network "forwarded_port", guest: 8086, host: 8086 # XLP Collector Server Port

                manager.vm.network "forwarded_port", guest: 8080, host: 8080 # Web Server Port
                manager.vm.network "forwarded_port", guest: 8081, host: 8081 # Apache Server Port
                manager.vm.network "forwarded_port", guest: 8082, host: 8082 # PHP Server Port
                manager.vm.network "forwarded_port", guest: 8083, host: 8083 # Flask Server Port

                manager.vm.network "forwarded_port", guest: 8338, host: 8338 # Maltrail Console Port

                manager.vm.network "forwarded_port", guest: 7077, host: 7077 # Apache Spark Master Port
                manager.vm.network "forwarded_port", guest: 9090, host: 9090 # Apache Spark UI Port
                
                manager.vm.network "forwarded_port", guest: 2003, host: 2003 # Graphite Port - Telegraf
                manager.vm.network "forwarded_port", guest: 8428, host: 8428 # Graphite Port - Victoriametrics
                manager.vm.network "forwarded_port", guest: 3000, host: 3000 # Grafana Port
            end
        end
    end

    # Setup Woker Nodes
    (1..WORKERS).each do |i|
        config.vm.define "worker0#{i}" do |worker|
            worker.vm.network "private_network", ip: "#{WORKER_IP}#{i}"
            worker.vm.hostname = "worker0#{i}"
            # Configure one port each for the worker nodes
            worker.vm.network "forwarded_port", guest: "8000", host: "809#{i}" # Application Port
            worker.vm.network "forwarded_port", guest: "8338", host: "83#{3+i}8" # Maltrail Console Port
        end
    end
end
