# Execute applications
# https://medium.com/geekculture/deploying-influxdb-2-0-using-docker-6334ced65b6c

USERNAME_TO_QUERY="root"
INFLUX_CONTAINER_NAME="influxdb"

docker-compose up -d
echo "waiting for influxDB..."

while [ ! -f influx/influxd.bolt ]; 
do sleep 1; 
done

sleep 6

echo "setting influxDB node token"

KEY=$(docker exec $INFLUX_CONTAINER_NAME influx auth list | grep $USERNAME_TO_QUERY | awk '{print $4}')

echo "KEY pulld: \"$KEY\""

sed -i '' "s/INFLUX_NODE_KEY=.*/INFLUX_NODE_KEY=\"$KEY\"/g" .env