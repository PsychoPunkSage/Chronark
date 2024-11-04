build:
	sudo docker compose -f docker-compose-test.yml build

run:
	sudo docker compose -f docker-compose-test.yml up

stop:
	sudo docker compose -f docker-compose-test.yml down