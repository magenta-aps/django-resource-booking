# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0012_auto_20160121_1649'),
    ]

    operations = [
        migrations.AlterField(
            model_name='resource',
            name='teaser',
            field=models.TextField(max_length=210, verbose_name='Teaser', blank=True),
        ),
        migrations.AlterField(
            model_name='resource',
            name='title',
            field=models.CharField(max_length=60, verbose_name='Titel'),
        ),
    ]
