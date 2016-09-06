# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0033_auto_20160218_1634'),
    ]

    operations = [
        migrations.AlterField(
            model_name='kuemailmessage',
            name='created',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
    ]
