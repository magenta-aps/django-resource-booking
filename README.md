Django Resource Booking - KUBooking
-----------------------------------

# Quick start

## Clone the project
	git clone git@github.com:magenta-aps/django-resource-booking.git

## Run install.sh in the root folder of the project
	./install.sh

## Setup frontend
	cd thirdparty && npm install && cd ..
	python manage.py collectstatic

## Create your user
	manage.py createsuperuser

## Open the django shell
	python manage.py shell

## In the django shell run the following for your newly created user
	from booking.models import *
	from profiles.models import *
	from django.contrib.auth import User
	from profile.constants import ADMINISTRATOR

	user = User.objects.first()
	user_role = UserRole.objects.create(role=ADMINISTRATOR)
	UserProfile.objects.create(user=user, user_role=user_role)

## Run the following which generates the data for our models
	from booking.models import *
	from profiles.models import *

	Region.create_defaults()
	PostCode.create_defaults()
	Municipality.create_defaults()
	School.create_defaults()
	GrundskoleLevel.create_defaults()
	EmailTemplateType.set_defaults()