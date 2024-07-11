#!/bin/bash
set -e

echo "Deployment started ..." 

# Pull the latest version of the app
echo "Pulling the latest changes from the main branch..."
git pull origin main --no-rebase 
echo "New changes copied to the server!"

# Activate Virtual Env
echo "Activating virtual environment 'myenv'..."
source /home/eatc/myenv/bin/activate 

# Move to the project directory
cd /home/eatc/eatc_ranoo/

# Install dependencies
echo "Installing Dependencies..."
pip install -r requirements.txt --no-input

# Serve Static Files
echo "Serving Static Files..."
python manage.py collectstatic --noinput

# Run Database migration
echo "Running Database migration..."
python manage.py makemigrations
python manage.py migrate 

# Deactivate Virtual Env
echo "Deactivating virtual environment 'myenv'..."
deactivate

echo "Deployment Finished!"

cd /home/eatc/eatc_ranoo/
celery -A Tasks worker --pool=solo -l info -E
