#!/bin/bash
source ../bin/activate
python manage.py test
fab prod deploy_all
fab all restart_web
