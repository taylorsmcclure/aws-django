#!/bin/bash
## Author: Taylor McClure
## Source: https://github.com/taylorsmcclure/aws-django

apt-get update && \
apt-get install -y python3 python3-pip git && \
pip3 install --upgrade pip && \
useradd -m -U --shell /bin/bash django && \
pip3 install virtualenv && \
virtualenv --python=python3 /home/django/django-site && \
source /home/django/django-site/bin/activate && \
pip install django && \
django-admin startproject mysite /home/django/django-site/ && \
sed -i "s/ALLOWED_HOSTS = \[\]/ALLOWED_HOSTS = \[\'\*\'\]/" /home/django/django-site/mysite/settings.py &&\
nohup /home/django/django-site/manage.py runserver 0.0.0.0:80 &
