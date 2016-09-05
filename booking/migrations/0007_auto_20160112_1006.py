# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import recurrence.fields


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0006_auto_20160106_1324'),
    ]

    operations = [
        migrations.CreateModel(
            name='VisitOccurrence',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('start_datetime', models.DateTimeField(verbose_name='Starttidspunkt')),
                ('end_datetime1', models.DateTimeField(verbose_name='Sluttidspunkt')),
                ('end_datetime2', models.DateTimeField(null=True, verbose_name='Alternativt sluttidspunkt', blank=True)),
            ],
        ),
        migrations.RemoveField(
            model_name='visit',
            name='time',
        ),
        migrations.AddField(
            model_name='visit',
            name='recurrences',
            field=recurrence.fields.RecurrenceField(null=True, verbose_name='Gentagelser'),
        ),
        migrations.AlterField(
            model_name='visit',
            name='duration',
            field=models.CharField(max_length=8, null=True, verbose_name='Varighed', blank=True),
        ),
        migrations.AddField(
            model_name='visitoccurrence',
            name='visit',
            field=models.ForeignKey(to='booking.Visit'),
        ),
    ]
