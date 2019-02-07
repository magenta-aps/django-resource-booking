Django Resource Booking - KUBooking
-----------------------------------

# Quick start

## Clone the project
```bash
	git clone git@github.com:magenta-aps/django-resource-booking.git
```
## Run install.sh in the root folder of the project
```bash
	./install.sh
```

## Setup local database in psql (sudo -u postgres psql)
```sql
create database resource_booking;
create user resource_booking with password 'resource_booking';
grant all privileges on database resource_booking to resource_booking;
```

## Setup frontend
```bash
	cd thirdparty && npm install && cd ..
	python manage.py collectstatic
```

## Create your user
```bash
python manage.py createsuperuser
```

## Open the django shell
```bash
python manage.py shell
```

## In the django shell run the following for your newly created user
```python
from booking.models import *
from profiles.models import *
from django.contrib.auth import User
from profile.constants import ADMINISTRATOR

user = User.objects.first()
user_role = UserRole.objects.create(role=ADMINISTRATOR)
UserProfile.objects.create(user=user, user_role=user_role)
```

## Run the following which generates the preliminary data for our models
```python
from booking.models import *
from profiles.models import *

Region.create_defaults()
PostCode.create_defaults()
Municipality.create_defaults()
School.create_defaults()
GrundskoleLevel.create_defaults()
EmailTemplateType.set_defaults()
```
