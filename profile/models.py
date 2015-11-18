from django.db import models
from django.contrib.auth.models import User


# TODO Insert the right values for this
SUPER_ADMIN = 0
UNIT_ADMIN = 1
PROFESSOR = 2
OTHER = 3

user_role_choices = (
    (SUPER_ADMIN, "Superadministrator"),
    (UNIT_ADMIN, "Site admin"),
    (PROFESSOR, "Underviser"),
    # XXX: COMPLETE THIS !!!
    (OTHER, "Hvad har vi")
)


class UserRole(models.Model):
    """"Superadmin, administrator, teacher, etc."""
    code = models.IntegerField(
        null=False,
        unique=True,
        choices=user_role_choices
    )
    name = models.CharField(max_length=256)
    description = models.TextField()


class UserProfile(models.Model):
    user = models.OneToOneField(User)
    user_role = models.ForeignKey(UserRole)
