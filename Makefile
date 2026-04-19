COMPOSE := docker compose

.PHONY: all build up down clean re

all: build up

build:
	$(COMPOSE) build

up:
	$(COMPOSE) up -d

down:
	$(COMPOSE) down

clean:
	$(COMPOSE) down --rmi local --volumes --remove-orphans

re: clean all
