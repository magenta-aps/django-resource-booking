# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('profile', '0008_userprofile_teacher_availability_text'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='userprofile',
            name='teacher_availability_text',
        ),
        migrations.AddField(
            model_name='userprofile',
            name='additional_information',
            field=models.TextField(default=b'', verbose_name='Yderligere information', blank=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='availability_text',
            field=models.TextField(default=b'', verbose_name='Mulige tidspunkter for v\xe6rt/underviser', blank=True),
        ),
    ]
