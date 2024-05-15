#!/bin/sh

# install python pip
sudo wget https://bootstrap.pypa.io/get-pip.py
sudo python3 ./get-pip.py

# install cron
sudo dnf install cronie cronie-anacron
sudo systemctl enable crond.service
sudo systemctl start crond.service

mkdir ~/tmp
# cd /algo-trading/code
sudo TMPDIR=~/tmp/ python3 -m pip install -r pandas, pyarrow, numpy, tabulate --no-cache-dir