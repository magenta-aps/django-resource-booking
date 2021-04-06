#!/usr/bin/env bash

source env/bin/activate
export DJANGO_SETTINGS_MODULE=resource_booking.settings
echo "Starting export..."
python export_templates.py
echo "Done."
deactivate