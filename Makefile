.PHONY: dev setup

dev:
	docker-compose down && ./start.sh
	
setup:
	rm influx/influxd.bolt && docker-compose down && ./start.sh