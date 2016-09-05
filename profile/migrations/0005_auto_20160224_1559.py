# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('profile', '0004_emailloginentry'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='userrole',
            options={'verbose_name': 'brugerrolle', 'verbose_name_plural': 'brugerroller'},
        ),
    ]
