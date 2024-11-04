build:
	sudo docker compose -f docker-compose-test.yml build

up:
	sudo docker compose -f docker-compose-test.yml up -d
	./setup.sh

down:
	sudo docker compose -f docker-compose-test.yml down

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