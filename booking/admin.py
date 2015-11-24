from django.contrib import admin

from booking.models import Visit, Unit, UnitType

# Register your models here.

admin.site.register(Visit)
admin.site.register(Unit)
admin.site.register(UnitType)
