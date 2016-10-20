# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0020_school_type'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='resource',
            name='class_level_max',
        ),
        migrations.RemoveField(
            model_name='resource',
            name='class_level_min',
        ),
        migrations.RemoveField(
            model_name='resource',
            name='level',
        ),
        migrations.RemoveField(
            model_name='resource',
            name='subjects',
        ),
    ]
