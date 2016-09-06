# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0080_auto_20160530_1026'),
    ]

    operations = [
        migrations.AddField(
            model_name='school',
            name='address',
            field=models.CharField(max_length=128, null=True, verbose_name='Adresse'),
        ),
        migrations.AddField(
            model_name='school',
            name='cvr',
            field=models.IntegerField(null=True, verbose_name='CVR-nummer'),
        ),
        migrations.AddField(
            model_name='school',
            name='ean',
            field=models.BigIntegerField(null=True, verbose_name='EAN-nummer'),
        ),
    ]
