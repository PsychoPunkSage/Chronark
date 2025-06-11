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

# load-load:
# #  usage: make load-load L=10 IP=192.168.1.100
# #  or:    make load-load L=10  # uses TARGET_IP
# 	@if [ -z "$(L)" ]; then \
# 		echo "Error: L is not set. Please provide a number using 'make load-test L=<number>'."; \
# 		echo "Usage: make load-test L=<number> [IP=<manager_ip>]"; \
# 		echo "Example: make load-test L=5 IP=192.168.1.100"; \
# 		exit 1; \
# 	fi
	
# 	@if [ -n "$(IP)" ]; then \
# 		scripts/load_test/load.sh --ip $(IP) --load $(L); \
# 	else \
# 		scripts/load_test/load.sh --ip $(TARGET_IP) --load $(L); \
# 	fi

# load-connectivity:
# #  usage: make load-connectivity IP=192.168.1.100
# 	@if [ -n "$(IP)" ]; then \
# 		scripts/load_test/load.sh --ip $(IP) --test; \
# 	else \
# 		scripts/load_test/load.sh --ip $(TARGET_IP) --test; \
# 	fi

# load-cleanup:
# #  usage: make load-cleanup L=10 IP=192.168.1.100
# #  usage: make load-cleanup L=10 # uses TARGET_IP
# 	@if [ -z "$(L)" ]; then \
# 		echo "Error: L must be set."; \
# 		echo "Usage: make load-cleanup L=<load> [IP=<manager_ip>]"; \
# 		echo "Example: make load-cleanup L=11 IP=192.168.1.100"; \
# 		exit 1; \
# 	fi
# 	@if [ -n "$(IP)" ]; then \
# 		scripts/load_test/load.sh --ip $(IP) --refresh $(L); \
# 	else \
# 		scripts/load_test/load.sh --ip $(TARGET_IP) --refresh $(L); \
# 	fi


load-load:
#  usage: make load-load L=10 IP=192.168.1.100 [C=50]
#  or:    make load-load L=10  # uses TARGET_IP
#  or:    make load-load L=1000 C=100  # with custom concurrency
	@if [ -z "$(L)" ]; then \
		echo "Error: L is not set. Please provide a number using 'make load-load L=<number>'."; \
		echo "Usage: make load-load L=<number> [IP=<manager_ip>] [C=<concurrency>]"; \
		echo "Example: make load-load L=1000 IP=192.168.1.100"; \
		echo "Example: make load-load L=5000 C=100  # with custom concurrency"; \
		exit 1; \
	fi
	
	@LOAD_CMD="python scripts/load_test/load.py --load $(L)"; \
	if [ -n "$(IP)" ]; then \
		LOAD_CMD="$$LOAD_CMD --ip $(IP)"; \
	else \
		LOAD_CMD="$$LOAD_CMD --ip $(TARGET_IP)"; \
	fi; \
	if [ -n "$(C)" ]; then \
		LOAD_CMD="$$LOAD_CMD --concurrency $(C)"; \
	fi; \
	echo "🚀 Executing: $$LOAD_CMD"; \
	$$LOAD_CMD

load-connectivity:
#  usage: make load-connectivity IP=192.168.1.100
#  or:    make load-connectivity  # uses TARGET_IP
	@if [ -n "$(IP)" ]; then \
		python scripts/load_test/load.py --ip $(IP) --test; \
	else \
		python scripts/load_test/load.py --ip $(TARGET_IP) --test; \
	fi

load-cleanup:
#  usage: make load-cleanup L=10 IP=192.168.1.100
#  or:    make load-cleanup L=10  # uses TARGET_IP
	@if [ -z "$(L)" ]; then \
		echo "Error: L must be set."; \
		echo "Usage: make load-cleanup L=<load> [IP=<manager_ip>]"; \
		echo "Example: make load-cleanup L=1000 IP=192.168.1.100"; \
		exit 1; \
	fi
	@if [ -n "$(IP)" ]; then \
		python scripts/load_test/load.py --ip $(IP) --cleanup $(L); \
	else \
		python scripts/load_test/load.py --ip $(TARGET_IP) --cleanup $(L); \
	fi

load-logout:
#  usage: make load-logout IP=192.168.1.100
#  or:    make load-logout  # uses TARGET_IP
	@if [ -n "$(IP)" ]; then \
		python scripts/load_test/load.py --ip $(IP) --logout; \
	else \
		python scripts/load_test/load.py --ip $(TARGET_IP) --logout; \
	fi

# Benchmark commands for different scales
load-benchmark-1k:
#  usage: make load-benchmark-1k [IP=192.168.1.100]
	@echo "🔥 Starting 1000 user benchmark..."
	@if [ -n "$(IP)" ]; then \
		python scripts/load_test/load.py --ip $(IP) --load 1000 --concurrency 50; \
	else \
		python scripts/load_test/load.py --ip $(TARGET_IP) --load 1000 --concurrency 50; \
	fi

load-benchmark-2k:
#  usage: make load-benchmark-2k [IP=192.168.1.100]
	@echo "🔥 Starting 2000 user benchmark..."
	@if [ -n "$(IP)" ]; then \
		python scripts/load_test/load.py --ip $(IP) --load 2000 --concurrency 75; \
	else \
		python scripts/load_test/load.py --ip $(TARGET_IP) --load 2000 --concurrency 75; \
	fi

load-benchmark-3k:
#  usage: make load-benchmark-3k [IP=192.168.1.100]
	@echo "🔥 Starting 3000 user benchmark..."
	@if [ -n "$(IP)" ]; then \
		python scripts/load_test/load.py --ip $(IP) --load 3000 --concurrency 100; \
	else \
		python scripts/load_test/load.py --ip $(TARGET_IP) --load 3000 --concurrency 100; \
	fi

load-benchmark-4k:
#  usage: make load-benchmark-4k [IP=192.168.1.100]
	@echo "🔥 Starting 4000 user benchmark..."
	@if [ -n "$(IP)" ]; then \
		python scripts/load_test/load.py --ip $(IP) --load 4000 --concurrency 125; \
	else \
		python scripts/load_test/load.py --ip $(TARGET_IP) --load 4000 --concurrency 125; \
	fi

load-benchmark-5k:
#  usage: make load-benchmark-5k [IP=192.168.1.100]
	@echo "🔥 Starting 5000 user benchmark..."
	@if [ -n "$(IP)" ]; then \
		python scripts/load_test/load.py --ip $(IP) --load 5000 --concurrency 150; \
	else \
		python scripts/load_test/load.py --ip $(TARGET_IP) --load 5000 --concurrency 150; \
	fi

# Full benchmark suite
load-benchmark-all:
#  usage: make load-benchmark-all [IP=192.168.1.100]
	@echo "🚀 Starting complete benchmark suite (1k-5k users)..."
	@echo "⚠️  This will take significant time. Press Ctrl+C to cancel."
	@sleep 5
	@$(MAKE) load-benchmark-1k $(if $(IP),IP=$(IP))
	@echo "📊 1k benchmark completed. Cleaning up..."
	@$(MAKE) load-cleanup L=1000 $(if $(IP),IP=$(IP))
	@sleep 10
	@$(MAKE) load-benchmark-2k $(if $(IP),IP=$(IP))
	@echo "📊 2k benchmark completed. Cleaning up..."
	@$(MAKE) load-cleanup L=2000 $(if $(IP),IP=$(IP))
	@sleep 10
	@$(MAKE) load-benchmark-3k $(if $(IP),IP=$(IP))
	@echo "📊 3k benchmark completed. Cleaning up..."
	@$(MAKE) load-cleanup L=3000 $(if $(IP),IP=$(IP))
	@sleep 10
	@$(MAKE) load-benchmark-4k $(if $(IP),IP=$(IP))
	@echo "📊 4k benchmark completed. Cleaning up..."
	@$(MAKE) load-cleanup L=4000 $(if $(IP),IP=$(IP))
	@sleep 10
	@$(MAKE) load-benchmark-5k $(if $(IP),IP=$(IP))
	@echo "📊 5k benchmark completed. Cleaning up..."
	@$(MAKE) load-cleanup L=5000 $(if $(IP),IP=$(IP))
	@echo "🎉 All benchmarks completed!"

# load-login:
# #  usage: make load-login USER=user11 PASS=user11 IP=192.168.1.100
# 	@if [ -z "$(USER)" ] || [ -z "$(PASS)" ]; then \
# 		echo "Error: USER and PASS must be set."; \
# 		echo "Usage: make load-login USER=<username> PASS=<password> [IP=<manager_ip>]"; \
# 		echo "Example: make load-login USER=user11 PASS=user11 IP=192.168.1.100"; \
# 		exit 1; \
# 	fi
# 	@if [ -n "$(IP)" ]; then \
# 		scripts/load_test/load.sh --ip $(IP) --login $(USER) $(PASS); \
# 	else \
# 		scripts/load_test/load.sh --ip $(MANAGER_IP) --login $(USER) $(PASS); \
# 	fi

# load-logout:
# #  usage: make load-logout USER=user11 IP=192.168.1.100
# 	@if [ -z "$(USER)" ]; then \
# 		echo "Error: USER must be set."; \
# 		echo "Usage: make load-logout USER=<username> [IP=<manager_ip>]"; \
# 		echo "Example: make load-logout USER=user11 IP=192.168.1.100"; \
# 		exit 1; \
# 	fi
# 	@if [ -n "$(IP)" ]; then \
# 		scripts/load_test/load.sh --ip $(IP) --logout $(USER); \
# 	else \
# 		scripts/load_test/load.sh --ip $(MANAGER_IP) --logout $(USER); \
# 	fi

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
