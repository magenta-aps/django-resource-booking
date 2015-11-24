from django.contrib import admin

from .models import Resource, Visit, Person, Unit, UnitType
from .models import Link, Subject, Tag, Topic

# Register your models here.

admin.site.register(Resource)
admin.site.register(Visit)
admin.site.register(Person)
admin.site.register(Unit)
admin.site.register(UnitType)
admin.site.register(Link)
admin.site.register(Subject)
admin.site.register(Tag)
admin.site.register(Topic)
