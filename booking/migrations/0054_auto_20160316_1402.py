# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0053_remove_resource_enabled'),
    ]

    operations = [
        migrations.AlterField(
            model_name='booking',
            name='visitoccurrence',
            field=models.ForeignKey(related_name='bookings', verbose_name='Tidspunkt', blank=True, to='booking.VisitOccurrence', null=True),
        ),
    ]
