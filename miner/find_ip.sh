# finds the IP address of a given miner

arp -a | grep -v 'incomplete' | grep ethernet | grep -i antminer

