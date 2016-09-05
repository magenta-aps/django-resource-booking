# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0047_auto_20160310_1059'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='otherresource',
            options={},
        ),
        migrations.AlterModelOptions(
            name='visit',
            options={'verbose_name': 'tilbud', 'verbose_name_plural': 'tilbud'},
        ),
    ]
