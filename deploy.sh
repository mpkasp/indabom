#!/bin/bash
activate_indabom
python manage.py test
fab prod deploy_full
fab all restart_web
