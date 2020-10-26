#!/bin/bash
pip freeze > requirements.txt
git add --all
git commit -am "bump dbom"
git status
git show HEAD
read -p "Continue? " -n 1 -r
if [[ $REPLY =~ ^[Yy]$ ]]
then
  git push
  ./deploy.sh
fi