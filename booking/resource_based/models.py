# encoding: utf-8
from django.db import models
from django.contrib.auth import models as auth_models
from django.utils.translation import ugettext_lazy as _
from recurrence.fields import RecurrenceField
from booking.models import Room
from profile.constants import TEACHER


class EventTime(models.Model):
    product = models.ForeignKey("Product")
    visit = models.ForeignKey(
        "Visit",
        null=True,
        blank=True
    )
    start = models.DateTimeField(
        verbose_name=_(u"Starttidspunkt")
    )
    end = models.DateTimeField(
        verbose_name=_(u"Sluttidspunkt"),
        blank=True
    )
    has_specific_time = models.BooleanField(
        default=False,
        verbose_name=_(u"Har fastsat tidspunkt")
    )
    notes = models.TextField(
        blank=True,
        default='',
        verbose_name=_(u'Interne kommentarer')
    )


class Calendar(models.Model):
    available_list = RecurrenceField(
        verbose_name=_(u"Tilgængelige tider")
    )
    unavailable_list = RecurrenceField(
        verbose_name=_(u"Utilgængelige tider")
    )


class ResourceType(models.Model):
    RESOURCE_TYPE_ITEM = 1
    RESOURCE_TYPE_VEHICLE = 2
    RESOURCE_TYPE_TEACHER = 3
    RESOURCE_TYPE_ROOM = 4

    default_resource_names = {
        RESOURCE_TYPE_ITEM: _(u"Materiale"),
        RESOURCE_TYPE_VEHICLE: _(u"Transportmiddel"),
        RESOURCE_TYPE_TEACHER: _(u"Underviser"),
        RESOURCE_TYPE_ROOM: _(u"Lokale"),
    }

    def __init__(self, *args, **kwargs):
        super(ResourceType, self).__init__(*args, **kwargs)
        if self.id == ResourceType.RESOURCE_TYPE_ITEM:
            self.resource_class = ItemResource
        elif self.id == ResourceType.RESOURCE_TYPE_VEHICLE:
            self.resource_class = VehicleResource
        elif self.id == ResourceType.RESOURCE_TYPE_TEACHER:
            self.resource_class = TeacherResource
        elif self.id == ResourceType.RESOURCE_TYPE_ROOM:
            self.resource_class = RoomResource
        else:
            self.resource_class = CustomResource

    name = models.CharField(
        max_length=30
    )

    @classmethod
    def create_defaults(cls):
        raise NotImplementedError()

    def __unicode__(self):
        return self.name


class Resource(models.Model):
    resource_type = models.ForeignKey(ResourceType)
    organizationalunit = models.ForeignKey(
        "OrganizationalUnit",
        verbose_name=_(u"Ressourcens enhed")
    )
    calendar = models.ForeignKey(
        Calendar,
        blank=True,
        null=True,
        verbose_name=_(u"Ressourcens kalender")
    )

    def get_name(self):
        return "Resource"

    def can_delete(self):
        return True

    @classmethod
    def subclasses(cls):
        subs = set()
        for subclass in cls.__subclasses__():
            subs.add(subclass)
            subs.update(subclass.subclasses())
        return subs

    @classmethod
    def get_subclass_instance(cls, pk):
        for typeclass in cls.subclasses():
            if not typeclass._meta.abstract:
                try:
                    return typeclass.objects.get(id=pk)
                except typeclass.DoesNotExist:
                    pass
        raise Resource.DoesNotExist

    @classmethod
    def create_subclass_instance(cls, type):
        if not isinstance(type, ResourceType):
            type = ResourceType.objects.get(id=type)
        cls = type.resource_class
        return cls()


class TeacherResource(Resource):
    # TODO: Begræns til brugertype og enhed
    user = models.ForeignKey(
        auth_models.User,
        verbose_name=_(u"Underviser")
    )

    def __init__(self, *args, **kwargs):
        super(TeacherResource, self).__init__(*args, **kwargs)
        self.resource_type = ResourceType.objects.get(
            id=ResourceType.RESOURCE_TYPE_TEACHER
        )

    def get_name(self):
        return self.user.get_full_name()

    def can_delete(self):
        return False

    @staticmethod
    def create_missing():
        known_teachers = list([
            teacher.id
            for teacher in auth_models.User.objects.filter(
                userprofile__user_role__role=TEACHER
            )
        ])
        missing_teachers = auth_models.User.objects.exclude(
            id__in=known_teachers
        )
        for teacher in missing_teachers:
            try:
                teacher_resource = TeacherResource(
                    user=teacher,
                    organizationalunit=teacher.userprofile.organizationalunit
                )
                teacher_resource.save()
            except Exception as e:
                print e
                pass


class RoomResource(Resource):
    # TODO: Begræns ud fra enhed
    room = models.ForeignKey(
        "Room",
        verbose_name=_(u"Lokale")
    )

    def __init__(self, *args, **kwargs):
        super(RoomResource, self).__init__(*args, **kwargs)
        self.resource_type = ResourceType.objects.get(
            id=ResourceType.RESOURCE_TYPE_ROOM
        )

    def get_name(self):
        return self.room.name

    def can_delete(self):
        return False

    @staticmethod
    def create_missing():
        known_rooms = list([
            roomresource.room.id
            for roomresource in RoomResource.objects.all()
        ])
        missing_rooms = Room.objects.exclude(id__in=known_rooms)
        for room in missing_rooms:
            try:
                room_resource = RoomResource(
                    room=room,
                    organizationalunit=room.locality.organizationalunit
                )
                room_resource.save()
            except:
                pass


class NamedResource(Resource):
    class Meta:
        abstract = True
    name = models.CharField(
        max_length=1024
    )

    def get_name(self):
        return self.name


class ItemResource(NamedResource):
    locality = models.ForeignKey(
        "Locality",
        null=True,
        blank=True
    )

    def __init__(self, *args, **kwargs):
        super(ItemResource, self).__init__(*args, **kwargs)
        self.resource_type = ResourceType.objects.get(
            id=ResourceType.RESOURCE_TYPE_ITEM
        )


class VehicleResource(NamedResource):
    locality = models.ForeignKey(
        "Locality",
        null=True,
        blank=True
    )

    def __init__(self, *args, **kwargs):
        super(VehicleResource, self).__init__(*args, **kwargs)
        self.resource_type = ResourceType.objects.get(
            id=ResourceType.RESOURCE_TYPE_VEHICLE
        )


class CustomResource(NamedResource):
    pass


class ResourcePool(models.Model):
    resource_type = models.ForeignKey(ResourceType)
    name = models.CharField(
        max_length=1024
    )
    organizationalunit = models.ForeignKey(
        "OrganizationalUnit",
        verbose_name=_(u"Ressourcens enhed")
    )
    # TODO: Begrænse på enhed, resource_type
    resources = models.ManyToManyField(
        Resource,
        verbose_name=_(u"Ressourcer")
    )


class ResourceRequirement(models.Model):
    product = models.ForeignKey("Product")
    resource_pool = models.ForeignKey(
        ResourcePool,
        verbose_name=_(u"Ressourcepulje")
    )
    required_amount = models.IntegerField(
        verbose_name=_(u"Påkrævet antal")
    )
