# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('profile', '0007_userprofile_my_resources'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='teacher_availability_text',
            field=models.TextField(default=b'', verbose_name='Mulige undervisningstidspunkter', blank=True),
        ),
    ]
