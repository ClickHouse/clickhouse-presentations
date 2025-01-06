#!/bin/bash

git mv $1 $2
mkdir $1
touch $1/index.html
echo "<html><head><meta http-equiv='refresh' content='0; URL=https://presentations.clickhouse.com/?path=$2'></head><body></body><html>" >> $1/index.html
git add $1
