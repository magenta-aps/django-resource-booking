# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from booking.models import OrganizationalUnit
from django.contrib.auth.models import User
from django.db import migrations, models
from django.utils.translation import ugettext_lazy as _
import datetime
import djorm_pgfulltext.fields
import django.utils.timezone
import django.core.validators
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0090_auto_20160804_1017'),
    ]

    operations = [
        migrations.DeleteModel(
            name='Person'
        ),
        migrations.DeleteModel(
            name='UserPerson'
        ),
        migrations.DeleteModel(
            name='AdditionalService'
        ),
        migrations.DeleteModel(
            name='SpecialRequirement'
        ),
        migrations.DeleteModel(
            name='OtherResource'
        ),
        migrations.RenameModel(
            old_name='LokaleAnsvarlig',
            new_name='RoomResponsible',
        ),
        migrations.RenameModel(
            old_name='UnitType',
            new_name='OrganizationalUnitType',
        ),
        migrations.RenameModel(
            old_name='Unit',
            new_name='OrganizationalUnit',
        ),
        migrations.RemoveField(
            model_name='Visit',
            name='additional_services'
        ),
        migrations.RemoveField(
            model_name='Visit',
            name='special_requirements'
        ),
        migrations.RenameModel(
            old_name='Visit',
            new_name='Product',
        ),
        migrations.RenameModel(
            old_name='VisitOccurrence',
            new_name='Visit',
        ),
        migrations.RenameModel(
            old_name='VisitOccurrenceComment',
            new_name='VisitComment',
        ),
        migrations.RenameModel(
            old_name='VisitAutosend',
            new_name='ProductAutosend',
        ),
        migrations.RenameModel(
            old_name='VisitOccurrenceAutosend',
            new_name='VisitAutosend',
        ),
        migrations.RenameModel(
            old_name='Booker',
            new_name='Guest',
        ),
        migrations.RenameModel(
            old_name='EmailBookerEntry',
            new_name='BookerResponseNonce',
        ),
        migrations.AlterField(
            model_name='OrganizationalUnit',
            name='contact',
            field=models.ForeignKey(
                User, null=True, blank=True,
                verbose_name=_(u'Kontaktperson'),
                related_name="contactperson_for_units",
                on_delete=models.SET_NULL,
            )
        ),
    ]
