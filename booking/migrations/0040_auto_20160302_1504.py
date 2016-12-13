# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0039_auto_20160302_1149'),
    ]

    operations = [
        migrations.AddField(
            model_name='region',
            name='name_en',
            field=models.CharField(max_length=16, null=True, verbose_name='Engelsk navn'),
        ),
        migrations.AlterField(
            model_name='region',
            name='name',
            field=models.CharField(max_length=16, verbose_name='Navn'),
        ),
    ]
