# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('profile', '0010_refactor_changes'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='userprofile',
            name='my_resources',
        ),
        # migrations.AddField(
        #     model_name='userprofile',
        #     name='my_resources',
        #     field=models.ManyToManyField(to='booking.Product', verbose_name='Mine tilbud', blank=True),
        # ),
    ]
