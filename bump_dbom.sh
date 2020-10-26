#!/bin/bash
pip freeze > requirements.txt
git add --all
git commit -am "bump dbom"
git push
./deploy.sh