#!/bin/bash
source ../bin/activate
python manage.py test
fab prod deploy
fab prod migrate
fab all restart_web