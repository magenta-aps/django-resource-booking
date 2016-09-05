# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0076_visitoccurrencecomment'),
    ]

    operations = [
        migrations.AddField(
            model_name='visitoccurrence',
            name='last_workflow_update',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
    ]
