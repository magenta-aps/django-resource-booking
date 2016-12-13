# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('booking', '0055_auto_20160317_1605'),
    ]

    operations = [
        migrations.AddField(
            model_name='kuemailmessage',
            name='content_type',
            field=models.ForeignKey(default=None, to='contenttypes.ContentType', null=True),
        ),
        migrations.AddField(
            model_name='kuemailmessage',
            name='object_id',
            field=models.PositiveIntegerField(default=None, null=True),
        ),
    ]
