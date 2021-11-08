# watchdog-docker-pi
Watch status of network services on systems and restart/reboot when necessary

## RancherOS

The container-cron service needs to be enabled on RancherOS. However, rancher seems to pull a non-arm64 image for the container-cron service by default.

```
system-docker tag niusmallnan/container-crontab:v0.4.0_arm64 rancher/container-crontab:v0.4.0
ros service enable container-cron
ros service up container-cron
```
