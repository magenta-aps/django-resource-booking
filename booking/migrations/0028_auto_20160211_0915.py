# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import datetime
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0027_auto_20160210_1647'),
    ]

    operations = [
        migrations.AlterField(
            model_name='kuemailmessage',
            name='created',
            field=models.DateTimeField(default=datetime.datetime(2016, 2, 11, 8, 15, 51, 443800, tzinfo=utc)),
        ),
    ]
