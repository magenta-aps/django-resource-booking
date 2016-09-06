# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import datetime
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0032_auto_20160218_1532'),
    ]

    operations = [
        migrations.AddField(
            model_name='visit',
            name='needed_hosts',
            field=models.IntegerField(default=0, verbose_name='N\xf8dvendigt antal v\xe6rter'),
        ),
        migrations.AddField(
            model_name='visit',
            name='needed_hosts_text',
            field=models.CharField(max_length=255, verbose_name='Formular for beregning af antal v\xe6rter', blank=True),
        ),
        migrations.AddField(
            model_name='visit',
            name='needed_teachers',
            field=models.IntegerField(default=0, verbose_name='N\xf8dvendigt antal undervisere'),
        ),
        migrations.AddField(
            model_name='visit',
            name='needed_teachers_text',
            field=models.CharField(max_length=255, verbose_name='Formular for beregning af antal undervisere', blank=True),
        ),
        migrations.AlterField(
            model_name='kuemailmessage',
            name='created',
            field=models.DateTimeField(default=datetime.datetime(2016, 2, 18, 15, 34, 49, 698053, tzinfo=utc)),
        ),
    ]
