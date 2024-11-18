# Monitor (WIP)

Simple monitoring tool for servers and applications. This is a work in progress, not ready, not stable.

## Install

```shell script
git clone git@github.com:sondreod/monitor.git
cd monitor

# Add your servers in the make_inventory function in main.py
# Enable the collectors you need and/or make your own.
```


### Grafana
Monitor is compliant with a small subset of the Prometeus protocol. So use the Prometeus source in Grafana to connect.
```shell script
#install grafana deb package
sudo systemctl restart grafana-server
sudo systemctl enable grafana-server
```