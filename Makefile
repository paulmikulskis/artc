.PHONY: dev setup

dev:
	docker-compose down && ./start.sh
	
setup:
	rm  -fr influx/influxd.bolt 2> /dev/null && docker-compose down && ./start.sh

stats:
	python nodes/client/control_client.py sungbean.com:6667 main pilisten