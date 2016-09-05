# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0059_auto_20160401_1031'),
    ]

    operations = [
        migrations.AlterField(
            model_name='objectstatistics',
            name='updated_time',
            field=models.DateTimeField(default=datetime.datetime(2016, 4, 1, 10, 32, 28, 10998)),
        ),
    ]
