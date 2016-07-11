#!/usr/bin/env bash

source python-env/bin/activate
export DJANGO_SETTINGS_MODULE=resource_booking.settings
echo "Starting import..."
python import_templates.py
echo "Done."
deactivate