# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0052_auto_20160316_1252'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='resource',
            name='enabled',
        ),
    ]
