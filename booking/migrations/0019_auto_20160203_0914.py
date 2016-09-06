# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import recurrence.fields


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0018_auto_20160202_1418'),
    ]

    operations = [
        migrations.AddField(
            model_name='resource',
            name='class_level_max',
            field=models.IntegerField(default=10, null=True, verbose_name='Klassetrin til', blank=True, choices=[(0, '0'), (1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5'), (6, '6'), (7, '7'), (8, '8'), (9, '9'), (10, '10')]),
        ),
        migrations.AddField(
            model_name='resource',
            name='class_level_min',
            field=models.IntegerField(default=0, null=True, verbose_name='Klassetrin fra', blank=True, choices=[(0, '0'), (1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5'), (6, '6'), (7, '7'), (8, '8'), (9, '9'), (10, '10')]),
        ),
        migrations.AddField(
            model_name='resource',
            name='level',
            field=models.IntegerField(blank=True, null=True, verbose_name='Niveau', choices=[(0, 'A'), (1, 'B'), (2, 'C')]),
        ),
        migrations.AddField(
            model_name='resource',
            name='subjects',
            field=models.ManyToManyField(to='booking.Subject', verbose_name='Fag', blank=True),
        ),
        migrations.AddField(
            model_name='visit',
            name='tour_available',
            field=models.BooleanField(default=False, verbose_name='Mulighed for rundvisning'),
        ),
        migrations.AlterField(
            model_name='visit',
            name='preparation_time',
            field=models.IntegerField(default=0, null=True, verbose_name='Forberedelsestid (i timer)'),
        ),
        migrations.AlterField(
            model_name='visit',
            name='price',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10, blank=True, null=True, verbose_name='Pris'),
        ),
        migrations.AlterField(
            model_name='visit',
            name='recurrences',
            field=recurrence.fields.RecurrenceField(null=True, verbose_name='Gentagelser', blank=True),
        ),
        migrations.AlterField(
            model_name='visit',
            name='rooms_assignment',
            field=models.IntegerField(default=0, null=True, verbose_name='Tildeling af lokale(r)', blank=True, choices=[(0, 'Lokaler tildeles p\xe5 forh\xe5nd'), (1, 'Lokaler tildeles ved booking')]),
        ),
    ]
