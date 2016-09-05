# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('profile', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userrole',
            name='role',
            field=models.IntegerField(default=0, choices=[(0, 'Underviser'), (1, 'V\xe6rt'), (2, 'Koordinator'), (3, 'Administrator')]),
        ),
    ]
