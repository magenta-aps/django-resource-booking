# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0009_auto_20151124_1458'),
    ]

    operations = [
        migrations.AddField(
            model_name='studymaterial',
            name='type',
            field=models.IntegerField(default=0, choices=[(0, 'URL'), (1, 'Vedh\xe6ftet fil')]),
        ),
        migrations.AlterField(
            model_name='resource',
            name='class_level_max',
            field=models.IntegerField(default=10, choices=[(0, '0'), (1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5'), (6, '6'), (7, '7'), (8, '8'), (9, '9'), (10, '10')]),
        ),
        migrations.AlterField(
            model_name='resource',
            name='level',
            field=models.IntegerField(blank=True, null=True, verbose_name='Niveau', choices=[(0, 'A'), (0, 'B'), (0, 'C')]),
        ),
        migrations.AlterField(
            model_name='resource',
            name='links',
            field=models.ManyToManyField(to='booking.Link', blank=True),
        ),
        migrations.AlterField(
            model_name='resource',
            name='subjects',
            field=models.ManyToManyField(to='booking.Subject', blank=True),
        ),
        migrations.AlterField(
            model_name='resource',
            name='tags',
            field=models.ManyToManyField(to='booking.Tag', blank=True),
        ),
        migrations.AlterField(
            model_name='resource',
            name='topics',
            field=models.ManyToManyField(to='booking.Topic', blank=True),
        ),
    ]
