from django.contrib import admin

from booking.models import Visit, Person, Unit, UnitType

# Register your models here.

admin.site.register(Visit)
admin.site.register(Person)
admin.site.register(Unit)
admin.site.register(UnitType)
