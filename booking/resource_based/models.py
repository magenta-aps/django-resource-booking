# encoding: utf-8
from django.db import models
from django.contrib.auth import models as auth_models
from django.utils.translation import ugettext_lazy as _
from recurrence.fields import RecurrenceField
from booking.models import Room
from profile.constants import TEACHER, HOST, NONE


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
    RESOURCE_TYPE_HOST = 5

    default_resource_names = {
        RESOURCE_TYPE_ITEM: _(u"Materiale"),
        RESOURCE_TYPE_VEHICLE: _(u"Transportmiddel"),
        RESOURCE_TYPE_TEACHER: _(u"Underviser"),
        RESOURCE_TYPE_ROOM: _(u"Lokale"),
        RESOURCE_TYPE_HOST: _(u"Vært"),
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
        elif self.id == ResourceType.RESOURCE_TYPE_HOST:
            self.resource_class = HostResource
        else:
            self.resource_class = CustomResource

    name = models.CharField(
        max_length=30
    )

    @classmethod
    def create_defaults(cls):
        for id, name in cls.default_resource_names.iteritems():
            try:
                item = ResourceType.objects.get(id=id)
                if item.name != name:  # WTF!
                    raise Exception(
                        u"ResourceType(id=%d) already exists, but has "
                        u"name %s instead of %s" % (id, item.name, name)
                    )
                else:
                    pass  # Item already exists; all is well
            except ResourceType.DoesNotExist:
                item = ResourceType(id=id, name=name)
                item.save()
                print "Created new ResourceType %d=%s" % (id, name)

    def __unicode__(self):
        return self.name


class Resource(models.Model):
    resource_type = models.ForeignKey(
        ResourceType,
        verbose_name=_(u'Type')
    )
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

    def __unicode__(self):
        return "%s (%s)" % (
            unicode(self.get_name()),
            unicode(self.resource_type)
        )

    @property
    def subclass_instance(self):
        return Resource.get_subclass_instance(self.pk)

    def group_preview(self, maxchars=50):
        display_groups = []
        chars = 0
        for group in self.resourcepool_set.all():
            display_groups.append({'name': group.name, 'group': group})
            chars += len(group.name)
            if maxchars is not None and chars >= maxchars:
                break
        if maxchars is not None and \
                len(display_groups) > 0 and \
                chars > maxchars:
            lastgroup = display_groups[-1]
            lastgroup['name'] = lastgroup['name'][0:(maxchars - chars)] + "..."
        return display_groups


class UserResource(Resource):
    class Meta:
        abstract = True

    role = NONE
    resource_type_id = 0

    user = models.ForeignKey(
        auth_models.User,
        verbose_name=_(u"Underviser")
    )

    def __init__(self, *args, **kwargs):
        super(UserResource, self).__init__(*args, **kwargs)
        self.resource_type = ResourceType.objects.get(
            id=self.__class__.resource_type_id
        )

    def get_name(self):
        return unicode(self.user.get_full_name())

    def can_delete(self):
        return False

    @classmethod
    def create_missing(cls):
        known_users = list([
            userresource.user.id
            for userresource in cls.objects.filter(
                user__userprofile__user_role__role=cls.role
            )
        ])
        print "We already have resources for %d users" % len(known_users)
        missing_users = auth_models.User.objects.filter(
            userprofile__user_role__role=cls.role
        ).exclude(
            pk__in=known_users
        )
        print "We are missing resources for %d users" % len(missing_users)
        if len(missing_users) > 0:
            created = 0
            skipped = 0
            for user in missing_users:
                try:
                    profile = user.userprofile
                    if profile.organizationalunit is not None:
                        user_resource = cls(
                            user=user,
                            organizationalunit=profile.organizationalunit
                        )
                        user_resource.save()
                        created += 1
                    else:
                        skipped += 1
                except Exception as e:
                    print e
            print "Created %d %s objects" % (created, cls.__name__)
            if skipped > 0:
                print "Skipped creating resources for %d objects " \
                      "that had no unit" % skipped

    @classmethod
    def create(cls, user, unit=None):
        if user.userprofile.get_role() == cls.role:
            if unit is None:
                unit = user.userprofile.organizationalunit
            user_resource = cls(
                user=user,
                organizationalunit=unit
            )
            user_resource.save()


class TeacherResource(UserResource):
    role = TEACHER
    resource_type_id = ResourceType.RESOURCE_TYPE_TEACHER


class HostResource(UserResource):
    role = HOST
    resource_type_id = ResourceType.RESOURCE_TYPE_HOST


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
                RoomResource.create(room)
            except:
                pass

    @staticmethod
    def create(room, unit=None):
        if unit is None:
            unit = room.locality.organizationalunit
        room_resource = RoomResource(room=room, organizationalunit=unit)
        room_resource.save()


class NamedResource(Resource):
    class Meta:
        abstract = True
    name = models.CharField(
        max_length=1024,
        verbose_name=_(u'Navn')
    )

    def get_name(self):
        return self.name


class ItemResource(NamedResource):
    locality = models.ForeignKey(
        "Locality",
        null=True,
        blank=True,
        verbose_name=_(u'Lokalitet')
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
        blank=True,
        verbose_name=_(u'Lokalitet')
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
        max_length=1024,
        verbose_name=_(u'Navn')
    )
    organizationalunit = models.ForeignKey(
        "OrganizationalUnit",
        verbose_name=_(u"Ressourcens enhed")
    )
    # TODO: Begrænse på enhed, resource_type
    resources = models.ManyToManyField(
        Resource,
        verbose_name=_(u"Ressourcer"),
        blank=True
    )

    def can_delete(self):
        return True

    def __unicode__(self):
        return "%s (%s)" % (self.name, _("Gruppe af %s") % self.resource_type)

    @property
    def specific_resources(self):
        return [
            resource.subclass_instance
            for resource in self.resources.all()
        ]


class ResourceRequirement(models.Model):
    product = models.ForeignKey("Product")
    resource_pool = models.ForeignKey(
        ResourcePool,
        verbose_name=_(u"Ressourcepulje")
    )
    required_amount = models.IntegerField(
        verbose_name=_(u"Påkrævet antal")
    )

    def can_delete(self):
        return True
