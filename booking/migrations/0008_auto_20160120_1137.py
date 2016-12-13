# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0007_auto_20160112_1006'),
    ]

    operations = [
        migrations.AlterField(
            model_name='resource',
            name='level',
            field=models.IntegerField(blank=True, null=True, verbose_name='Niveau', choices=[(0, 'A'), (1, 'B'), (2, 'C')]),
        ),
    ]
