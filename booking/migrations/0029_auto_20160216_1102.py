# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import datetime
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0028_auto_20160211_0915'),
    ]

    operations = [
        migrations.AddField(
            model_name='booking',
            name='comments',
            field=models.TextField(default=b'', verbose_name='Interne kommentarer', blank=True),
        ),
        migrations.AlterField(
            model_name='emailtemplate',
            name='key',
            field=models.IntegerField(default=1, verbose_name='Key', choices=[(1, 'Booking created'), (2, 'Message to bookers of a visit'), (3, 'Message to hosts of a visit')]),
        ),
        migrations.AlterField(
            model_name='kuemailmessage',
            name='created',
            field=models.DateTimeField(default=datetime.datetime(2016, 2, 16, 10, 2, 33, 265772, tzinfo=utc)),
        ),
    ]
