# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0004_auto_20151124_1008'),
    ]

    operations = [
        migrations.AddField(
            model_name='person',
            name='email',
            field=models.EmailField(max_length=64, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='person',
            name='phone',
            field=models.CharField(max_length=14, null=True, blank=True),
        ),
    ]
