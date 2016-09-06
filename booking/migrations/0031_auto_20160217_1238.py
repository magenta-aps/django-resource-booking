# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import datetime
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0030_auto_20160216_1638'),
    ]

    operations = [
        migrations.AlterField(
            model_name='emailtemplate',
            name='key',
            field=models.IntegerField(default=1, verbose_name='Key', choices=[(1, 'Booking created'), (2, 'Message to bookers of a visit'), (3, 'Message to hosts of a visit'), (4, 'Message to a booker')]),
        ),
        migrations.AlterField(
            model_name='kuemailmessage',
            name='created',
            field=models.DateTimeField(default=datetime.datetime(2016, 2, 17, 11, 38, 35, 562932, tzinfo=utc)),
        ),
    ]
