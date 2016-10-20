# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0074_auto_20160524_1047'),
    ]

    operations = [
        migrations.AlterField(
            model_name='resource',
            name='preparation_time',
            field=models.CharField(max_length=200, null=True, verbose_name='Forberedelsestid', blank=True),
        ),
    ]
