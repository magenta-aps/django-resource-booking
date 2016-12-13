# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0071_resource_contacts'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='userperson',
            options={'ordering': ['person__name', 'user__first_name', 'user__username'], 'verbose_name': 'Lokaleanvarlig', 'verbose_name_plural': 'Lokaleanvarlige'},
        ),
    ]
