# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0051_resource_created_by'),
        ('profile', '0006_auto_20160315_1331'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='my_resources',
            field=models.ManyToManyField(to='booking.Resource', verbose_name='Mine tilbud', blank=True),
        ),
    ]
