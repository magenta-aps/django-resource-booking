# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0036_auto_20160225_1022'),
    ]

    operations = [
        migrations.AddField(
            model_name='unit',
            name='url',
            field=models.URLField(null=True, verbose_name='Hjemmeside', blank=True),
        ),
    ]
