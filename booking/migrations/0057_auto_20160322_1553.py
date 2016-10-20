# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0056_auto_20160322_1159'),
    ]

    operations = [
        migrations.CreateModel(
            name='ObjectStatistics',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created_time', models.DateTimeField(auto_now_add=True)),
                ('updated_time', models.DateTimeField(default=datetime.datetime(2016, 3, 22, 15, 53, 9, 115121))),
                ('visited_time', models.DateTimeField(null=True, blank=True)),
                ('display_counter', models.IntegerField(default=0)),
            ],
        ),
        migrations.RemoveField(
            model_name='booking',
            name='created_time',
        ),
        migrations.AddField(
            model_name='visitoccurrence',
            name='end_datetime',
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='booking',
            name='statistics',
            field=models.ForeignKey(to='booking.ObjectStatistics', null=True),
        ),
        migrations.AddField(
            model_name='resource',
            name='statistics',
            field=models.ForeignKey(to='booking.ObjectStatistics', null=True),
        ),
        migrations.AddField(
            model_name='visitoccurrence',
            name='statistics',
            field=models.ForeignKey(to='booking.ObjectStatistics', null=True),
        ),
    ]
