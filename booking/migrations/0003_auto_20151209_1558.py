# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import booking.fields


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0002_sprint2_resource_inheritance'),
    ]

    operations = [
        migrations.AddField(
            model_name='resource',
            name='state',
            field=models.IntegerField(default=0, verbose_name='Tilstand', choices=[(0, 'Oprettet'), (1, 'Aktivt'), (2, 'Oph\xf8rt')]),
        ),
        migrations.AlterField(
            model_name='locality',
            name='unit',
            field=models.ForeignKey(verbose_name='Enhed', blank=True, to='booking.Unit', null=True),
        ),
        migrations.AlterField(
            model_name='visit',
            name='duration',
            field=booking.fields.DurationField(null=True, verbose_name='Varighed', blank=True),
        ),
    ]
