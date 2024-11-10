# Monitor

Simple monitoring tool for servers and applications.

## Install

```shell script
git clone git@github.com:sondreod/monitor.git
cd monitor

# Add your servers in the make_inventory function in main.py
# Enable the collectors you need and/or make your own.
```


### Grafana and csv-source plugin
```shell script
#install grafana deb package
/usr/share/grafana/bin/grafana cli plugins install yesoreyeram-infinity-datasource
sudo systemctl restart grafana-server
sudo systemctl enable grafana-server
```