#!/bin/bash
pip install -r requirements.txt
cd fitstock
python manage.py migrate
python manage.py collectstatic --noinput