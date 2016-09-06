# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import recurrence.fields


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0042_auto_20160309_1311'),
    ]

    operations = [
        migrations.AddField(
            model_name='resource',
            name='contact_persons_migrate',
            field=models.ManyToManyField(to='booking.Person', verbose_name='Kontaktpersoner', blank=True),
        ),
        migrations.AddField(
            model_name='resource',
            name='locality_migrate',
            field=models.ForeignKey(verbose_name='Lokalitet', blank=True, to='booking.Locality', null=True),
        ),
        migrations.AddField(
            model_name='resource',
            name='preparation_time_migrate',
            field=models.IntegerField(default=0, null=True, verbose_name='Forberedelsestid (i timer)'),
        ),
        migrations.AddField(
            model_name='resource',
            name='price_migrate',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10, blank=True, null=True, verbose_name='Pris'),
        ),
        migrations.AddField(
            model_name='resource',
            name='recurrences_migrate',
            field=recurrence.fields.RecurrenceField(null=True, verbose_name='Gentagelser', blank=True),
        ),
        migrations.AddField(
            model_name='studymaterial',
            name='resource',
            field=models.ForeignKey(related_name='material', to='booking.Resource', null=True),
        ),
    ]
