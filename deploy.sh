#!/bin/bash
source ../bin/activate
python manage.py test
fab prod deploy_full
fab all restart_web
