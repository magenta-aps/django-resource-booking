# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('profile', '0011_auto_20160905_1651'),
        ('booking', '0093_merge_resource_to_product'),
    ]

    operations = [
        migrations.DeleteModel(
            name='Resource',
        ),
    ]
