# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0016_auto_20160201_1137'),
    ]

    operations = [
        migrations.AlterField(
            model_name='booker',
            name='attendee_count',
            field=models.IntegerField(null=True, verbose_name='Antal deltagere', blank=True),
        ),
    ]
