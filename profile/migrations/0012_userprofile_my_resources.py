# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0094_delete_resource'),
        ('profile', '0011_auto_20160905_1651'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='my_resources',
            field=models.ManyToManyField(to='booking.Product', verbose_name='Mine tilbud', blank=True),
        ),
    ]
