# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0069_auto_20160519_1314'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='locality',
            options={'ordering': ['name'], 'verbose_name': 'lokalitet', 'verbose_name_plural': 'lokaliteter'},
        ),
        migrations.AlterModelOptions(
            name='person',
            options={'ordering': ['name'], 'verbose_name': 'kontaktperson', 'verbose_name_plural': 'kontaktpersoner'},
        ),
    ]
