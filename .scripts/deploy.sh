#!/bin/bash
set -e

echo "Deployment started ..."

# Pull the latest version of the app
git pull origin main
echo "New changes copied to server !"

# Activate Virtual Env
source /home/eatc/myenv/bin/activate 
echo "Virtual env 'myenv' Activated !"

echo "Installing Dependencies..."
cd /home/eatc/eatc_ranoo/
pip install -r requirements.txt --no-input

echo "Serving Static Files..."
python manage.py collectstatic --noinput

echo "Running Database migration"
python manage.py makemigrations
python manage.py migrate
 
# Deactivate Virtual Env
deactivate
echo "Virtual env 'myenv' Deactivated !"

echo "Deployment Finished!"
