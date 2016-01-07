from django.contrib import admin

from .models import OtherResource, Visit, Person, Unit, UnitType
from .models import Link, Subject, Tag, Topic, AdditionalService
from .models import SpecialRequirement, StudyMaterial, Locality

# Register your models here.

admin.site.register(OtherResource)
admin.site.register(Visit)
admin.site.register(Person)
admin.site.register(Unit)
admin.site.register(UnitType)
admin.site.register(Link)
admin.site.register(Subject)
admin.site.register(Tag)
admin.site.register(Topic)
admin.site.register(AdditionalService)
admin.site.register(SpecialRequirement)
admin.site.register(StudyMaterial)
admin.site.register(Locality)
