# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from booking.models import OrganizationalUnit
from django.db import migrations, models
import datetime
import django.utils.timezone
from django.conf import settings
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('booking', '0091_refactor_changes'),
        ('profile', '0009_auto_20160601_1309'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='EmailLoginEntry',
            new_name='EmailLoginURL',
        ),
        migrations.AlterField(
            model_name='UserProfile',
            name='unit',
            field=models.ForeignKey(
                OrganizationalUnit,
                null=True,
                blank=True
            )
        ),
        migrations.RenameField(
            model_name='UserProfile',
            old_name='unit',
            new_name='organizationalunit',
        ),
    ]
