# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import datetime
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0026_auto_20160210_1643'),
    ]

    operations = [
        migrations.AddField(
            model_name='classbooking',
            name='time',
            field=models.ForeignKey(verbose_name='Tidspunkt', blank=True, to='booking.VisitOccurrence', null=True),
        ),
        migrations.AlterField(
            model_name='kuemailmessage',
            name='created',
            field=models.DateTimeField(default=datetime.datetime(2016, 2, 10, 15, 47, 0, 611342, tzinfo=utc)),
        ),
    ]
