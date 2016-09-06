# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0058_auto_20160331_1152'),
    ]

    operations = [
        migrations.AlterField(
            model_name='objectstatistics',
            name='updated_time',
            field=models.DateTimeField(default=datetime.datetime(2016, 4, 1, 10, 31, 17, 780940)),
        ),
    ]
