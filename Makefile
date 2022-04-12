.PHONY: dev setup http

dev:
	docker-compose down && ./start.sh
	
setup:
	rm  -fr influx/influxd.bolt 2> /dev/null && docker-compose down && ./start.sh

stats:
	python nodes/control.py sungbean.com:6667 main pilisten

# background stats
bstats:
	nohup python -u nodes/control.py sungbean.com:6667 main pilisten > control.log


http:
	python nodes/client/http_client_proxy.py sungbean.com jumba_bot,pibot http_bot