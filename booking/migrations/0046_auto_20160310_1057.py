# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0045_studymaterial_migrate'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='studymaterial',
            name='visit',
        ),
        migrations.RenameField(
            model_name='resource',
            old_name='contact_persons_migrate',
            new_name='contact_persons',
        ),
        migrations.RenameField(
            model_name='resource',
            old_name='locality_migrate',
            new_name='locality',
        ),
        migrations.RenameField(
            model_name='resource',
            old_name='preparation_time_migrate',
            new_name='preparation_time',
        ),
        migrations.RenameField(
            model_name='resource',
            old_name='price_migrate',
            new_name='price',
        ),
        migrations.RenameField(
            model_name='resource',
            old_name='recurrences_migrate',
            new_name='recurrences',
        ),
        migrations.RemoveField(
            model_name='visit',
            name='contact_persons',
        ),
        migrations.RemoveField(
            model_name='visit',
            name='locality',
        ),
        migrations.RemoveField(
            model_name='visit',
            name='preparation_time',
        ),
        migrations.RemoveField(
            model_name='visit',
            name='price',
        ),
        migrations.RemoveField(
            model_name='visit',
            name='recurrences',
        ),
        migrations.DeleteModel(
            name='StudyMaterial',
        ),
    ]
