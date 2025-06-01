##########
# Docker #
##########
build:
	sudo docker compose build

upd:
	sudo docker compose up -d
# ./setup.sh

up:
	sudo docker compose up

up-load:
	./setup.sh

down:
	sudo docker compose down

############
# Pen Test #
############

# TARGET_IP ?= 35.200.163.35
TARGET_IP ?= 35.200.204.177
# TARGET_IP ?= 34.93.68.169

load-load:
#  usage: make load-load L=10 IP=192.168.1.100
#  or:    make load-load L=10  # uses TARGET_IP
	@if [ -z "$(L)" ]; then \
		echo "Error: L is not set. Please provide a number using 'make load-test L=<number>'."; \
		echo "Usage: make load-test L=<number> [IP=<manager_ip>]"; \
		echo "Example: make load-test L=5 IP=192.168.1.100"; \
		exit 1; \
	fi
	
	@if [ -n "$(IP)" ]; then \
		scripts/load_test/load.sh --ip $(IP) --load $(L); \
	else \
		scripts/load_test/load.sh --ip $(TARGET_IP) --load $(L); \
	fi

load-connectivity:
#  usage: make load-connectivity IP=192.168.1.100
	@if [ -n "$(IP)" ]; then \
		scripts/load_test/load.sh --ip $(IP) --test; \
	else \
		scripts/load_test/load.sh --ip $(TARGET_IP) --test; \
	fi

load-cleanup:
#  usage: make load-cleanup L=10 IP=192.168.1.100
#  usage: make load-cleanup L=10 # uses TARGET_IP
	@if [ -z "$(L)" ]; then \
		echo "Error: L must be set."; \
		echo "Usage: make load-cleanup L=<load> [IP=<manager_ip>]"; \
		echo "Example: make load-cleanup L=11 IP=192.168.1.100"; \
		exit 1; \
	fi
	@if [ -n "$(IP)" ]; then \
		scripts/load_test/load.sh --ip $(IP) --refresh $(L); \
	else \
		scripts/load_test/load.sh --ip $(TARGET_IP) --refresh $(L); \
	fi

load-login:
#  usage: make load-login USER=user11 PASS=user11 IP=192.168.1.100
	@if [ -z "$(USER)" ] || [ -z "$(PASS)" ]; then \
		echo "Error: USER and PASS must be set."; \
		echo "Usage: make load-login USER=<username> PASS=<password> [IP=<manager_ip>]"; \
		echo "Example: make load-login USER=user11 PASS=user11 IP=192.168.1.100"; \
		exit 1; \
	fi
	@if [ -n "$(IP)" ]; then \
		scripts/load_test/load.sh --ip $(IP) --login $(USER) $(PASS); \
	else \
		scripts/load_test/load.sh --ip $(MANAGER_IP) --login $(USER) $(PASS); \
	fi

load-logout:
#  usage: make load-logout USER=user11 IP=192.168.1.100
	@if [ -z "$(USER)" ]; then \
		echo "Error: USER must be set."; \
		echo "Usage: make load-logout USER=<username> [IP=<manager_ip>]"; \
		echo "Example: make load-logout USER=user11 IP=192.168.1.100"; \
		exit 1; \
	fi
	@if [ -n "$(IP)" ]; then \
		scripts/load_test/load.sh --ip $(IP) --logout $(USER); \
	else \
		scripts/load_test/load.sh --ip $(MANAGER_IP) --logout $(USER); \
	fi

#######
# CVE #
#######

cve-2020-7921:
	python scripts/Mongodb/CVE-2020-7921/attack.py

cve-2022-24834:
	python scripts/Redis/CVE-2022-24834/redis_cve-2022-24834.py

cve-2024-27983:
	@echo "cd ./src/contact/app.js"
	@echo "  > Comment-OUT: <const server = createHttp2ExpressAdapter(); // non-vulnerable>"
	@echo "  > UnComment  : <const server = http2.createServer(); // vulnerable>"
	@echo "cd ./scripts/nodejs/CVE-2024-27983/"
	@echo "go run test.go -address :5003"
	@echo "=========RESULT========="
	@echo "sudo docker ps -a | grep contact"

###################
# Data Collection #
###################

cAd-collectdata:
	rm -rf monitoring_data/
	python scripts/cAdvisor/data_collector.py
	echo ""
	echo "==================================="
	echo "| visit ./monitoring_data/ folder |"
	ehco "==================================="

##############
# DEPLOYEMNT #
##############

aws-deploy:
	python aws-deploy.py
