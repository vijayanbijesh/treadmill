#!/bin/bash -e
cd /home/centos/treadmill
source env/bin/activate

nohup treadmill sproc scheduler /tmp > scheduler.out &
nohup treadmill sproc service --root-dir /tmp/treadmill/ localdisk --reserve 20G --img-location /tmp/treadmill --default-read-bps 100M --default-write-bps 100M --default-read-iops 300 --default-write-iops 300 > local_disk_service.out &
nohup treadmill sproc service --root-dir /tmp/treadmill/ network > network_service.out &
nohup treadmill sproc service --root-dir /tmp/treadmill/ cgroup > cgroup_service.out &
nohup treadmill sproc init --approot /tmp/treadmill/ > node.out &
