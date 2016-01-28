from django.contrib import admin

from .models import OtherResource, Visit, Person, Unit, UnitType, \
    VisitOccurrence
from .models import Link, Subject, Tag, Topic, AdditionalService
from .models import SpecialRequirement, StudyMaterial, Locality
from .models import GymnasieLevel, ResourceGymnasieFag, ResourceGrundskoleFag
from .models import School, PostCode, Region, Booker, Booking
from .models import GymnasieLevel

# Register your models here.

admin.site.register(OtherResource)
admin.site.register(Visit)
admin.site.register(VisitOccurrence)
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
admin.site.register(GymnasieLevel)
admin.site.register(ResourceGymnasieFag)
admin.site.register(ResourceGrundskoleFag)
admin.site.register(PostCode)
admin.site.register(Region)
admin.site.register(School)
admin.site.register(Booker)
admin.site.register(Booking)
