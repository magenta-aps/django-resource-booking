# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0065_auto_20160407_0905'),
    ]

    operations = [
        migrations.AddField(
            model_name='visitoccurrence',
            name='evaluation_link',
            field=models.CharField(default=b'', max_length=1024, verbose_name='Link til evaluering', blank=True),
        ),
    ]
