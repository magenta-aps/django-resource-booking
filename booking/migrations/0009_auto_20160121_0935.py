# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0008_auto_20160120_1137'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='subject',
            name='line',
        ),
        migrations.AddField(
            model_name='subject',
            name='subject_type',
            field=models.IntegerField(default=1, verbose_name='Skoleniveau', choices=[(1, 'Gymnasie'), (2, 'Grundskole'), (3, 'Begge')]),
        ),
        migrations.AlterField(
            model_name='resource',
            name='institution_level',
            field=models.IntegerField(default=1, verbose_name='Institution', choices=[(1, 'Gymnasie'), (2, 'Grundskole'), (3, 'Begge')]),
        ),
    ]
