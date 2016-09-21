# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0094_delete_resource'),
    ]

    operations = [
        migrations.RenameField(
            model_name='visit',
            old_name='bookable',
            new_name='deprecated_bookable',
        ),
        migrations.RenameField(
            model_name='visit',
            old_name='end_datetime',
            new_name='deprecated_end_datetime',
        ),
        migrations.RenameField(
            model_name='visit',
            old_name='start_datetime',
            new_name='deprecated_start_datetime',
        ),
        migrations.RenameField(
            model_name='visit',
            old_name='product',
            new_name='deprecated_product',
        ),
    ]
