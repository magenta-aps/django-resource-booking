# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0057_auto_20160322_1553'),
    ]

    operations = [
        migrations.AlterField(
            model_name='objectstatistics',
            name='updated_time',
            field=models.DateTimeField(default=datetime.datetime(2016, 3, 31, 11, 52, 53, 573234)),
        ),
    ]
