# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0043_auto_20160310_0908'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='studymaterial',
            name='resource',
        ),
    ]
