#!/bin/bash -e

yum -y install git
git clone https://github.com/Morgan-Stanley/treadmill.git
git clone https://github.com/Morgan-Stanley/treadmill-pid1.git

########################################## AWS ##########################


yum -y update
yum -y install java wget

#
wget http://apache.claz.org/zookeeper/stable/zookeeper-3.4.9.tar.gz
tar -xvzf zookeeper-3.4.9.tar.gz
cp zookeeper-3.4.9/conf/zoo_sample.cfg zookeeper-3.4.9/conf/zoo.cfg
zookeeper-3.4.9/bin/zkServer.sh start


########################################## TreadMill Code Build ##########################

curl "https://bootstrap.pypa.io/get-pip.py" -o "get-pip.py"
python get-pip.py
sudo yum -y group install "Development Tools"
echo `whereis gcc`
sudo yum -y install python-devel libkrb5-dev ntp krb5-server krb5-libs krb5-devel
sudo pip install virtualenv
virtualenv env
source env/bin/activate
git checkout remotes/origin/standard_setup
pip install --upgrade -r requirements.txt
python setup.py install
treadmill --help

sudo mount --make-rprivate /
######################################## logging
mkdir -p /home/centos/treadmill/env/lib/python2.7/etc/logging/
touch /home/centos/treadmill/env/lib/python2.7/etc/logging/daemon.yml
touch /home/centos/treadmill/env/lib/python2.7/etc/logging/cli.yml
cp /home/centos/treadmill/env/lib/python2.7/etc/logging/{cli,admin}.yml

######################################### Scheduler
sudo su - && cd /home/centos/treadmill && source env/bin/activate

treadmill sproc scheduler /tmp

########################################## Zookeper

# create /scheduled/centos.bar#123 {"memory":"100M","cpu":"10%","disk":"500M","proid":"centos","affinity":"centos.bar","services":[{"name":"sleep","command":"/bin/top","restart":{"limit":5,"interval":60}}]}

# create /servers/$(hostname -f) -- create /servers/ip-172-31-59-100.ec2.internal {"parent":"all:unknown","features":[],"traits":[],"label":null,"valid_until":1488573090.0}
# create /cell/all:unknown {}
# create /buckets/all:unknown {"parent":null,"traits":0}

################################## ENV vars -- currently in /home/centos/prestine.sh -- loaded by bashrc on ec2

echo 'export TREADMILL_ZOOKEEPER=zookeeper://foo@127.0.0.1:2181' >> ~/.bash_profile
echo 'export TREADMILL_EXE_WHITELIST=/home/centos/treadmill/etc/linux.exe.config' >> ~/.bash_profile
echo 'export TREADMILL_CELL=ec2-34-198-157-255.compute-1.amazonaws.com' >> ~/.bash_profile
echo 'export TREADMILL_APPROOT=/tmp/treadmill' >> ~/.bash_profile
#export TREADMILL_DNS_DOMAIN=treadmill.com
#export TREADMILL_LDAP_SEARCH_BASE=foo
alias z=/usr/lib/zookeeper/bin/zkCli.sh

######################################## Services

sudo su -
cd /home/centos/treadmill
source env/bin/activate

mkdir -p /tmp/treadmill/etc
cp /etc/resolv.conf /tmp/treadmill/etc/
sudo yum -y install ipset iptables bridge-utils libcgroup-tools lvm2*
# change path of lssubsys in linux.exe.config if need be

dd if=/dev/zero of=/tmp/treadmill/treadmill.img seek=$((1024*1024*20)) count=1

treadmill sproc service --root-dir /tmp/treadmill/ localdisk --reserve 20G --img-location /tmp/treadmill --default-read-bps 100M --default-write-bps 100M --default-read-iops 300 --default-write-iops 300
treadmill sproc service --root-dir /tmp/treadmill/ network
treadmill sproc service --root-dir /tmp/treadmill/ cgroup


####################################### Node Server init
sudo su -
cd /home/centos/treadmill
source env/bin/activate

cd /sys/fs/cgroup
for i in *; do mkdir -p $i/treadmill/apps $i/treadmill/core $i/system ; done #why again?
cd -
treadmill sproc init --approot /tmp/treadmill/

############################################ python code fix
# fs.py --> plugings
# appmgr/configure.py --> TREADMILL -- treadmill path
# netdev.py --> dev_stat -- lowerlayerdown

############################################ s6

git clone git://git.skarnet.org/skalibs
cd skalibs && ./configure && make && sudo make install && cd -

git clone git://git.skarnet.org/execline 
cd execline && ./configure && make && sudo make install && cd -

git clone https://github.com/skarnet/s6.git
cd s6 && ./configure && make && sudo make install && cd -

# update s6 paths in treadmill/etc/linux.exe.config -- s6 variable takes s6 path /usr/bin/s6

cd /tmp/treadmill/running && s6-svscan && cd -


######################################### treadmill-pid1
#git clone git@github.com:Morgan-Stanley/treadmill-pid1.git
cd treadmill-pid1 && make && cd -

# udpate pid1 path in treadmill/etc/linux.exe.config

######################################### admin
treadmill --debug admin scheduler --zookeeper $TREADMILL_ZOOKEEPER view servers
treadmill --debug admin scheduler --zookeeper $TREADMILL_ZOOKEEPER view apps

######################################### eventd and appcfgmgr
treadmill sproc eventdaemon
treadmill sproc appcfgmgr

#########################################Server setup
# server needs to have parent
# for admin -- env variables are ignored
