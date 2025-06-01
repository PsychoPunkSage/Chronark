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

load-load:
#  usage :> make load-load L=10
	@if [ -z "$(L)" ]; then \
		echo "Error: L is not set. Please provide a number using 'make load-load L=<number>'."; \
		exit 1; \
	fi
	scripts/load_test/load.sh --load $(L)

load-cleanup:
#  usage :> make load-cleanup L=10
	scripts/load_test/load.sh --refresh 11 $$(($(L) + 11))

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
