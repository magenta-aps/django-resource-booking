# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0002_auto_20151118_0845'),
        ('profile', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='userrole',
            name='code',
        ),
        migrations.AddField(
            model_name='userprofile',
            name='unit',
            field=models.ForeignKey(blank=True, to='booking.Unit', null=True),
        ),
        migrations.AddField(
            model_name='userrole',
            name='role',
            field=models.IntegerField(default=0, unique=True, choices=[(0, 'Underviser'), (1, 'V\xe6rt'), (2, 'Koordinator'), (3, 'Underviser')]),
        ),
        migrations.AlterField(
            model_name='userrole',
            name='name',
            field=models.CharField(max_length=256, blank=True),
        ),
    ]
