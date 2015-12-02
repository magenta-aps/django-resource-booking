from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User as AuthUser
from django.utils.translation import ugettext_lazy as _

from .models import UserRole, UserProfile, User


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = _(u"brugerprofil")


class UserAdmin(UserAdmin):
    inlines = (UserProfileInline, )


admin.site.unregister(AuthUser)
admin.site.register(User, UserAdmin)
admin.site.register(UserRole)
