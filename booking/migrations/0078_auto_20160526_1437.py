# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0077_visitoccurrence_last_workflow_update'),
    ]

    operations = [
        migrations.CreateModel(
            name='WaitingList',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('closing_time', models.DateTimeField(null=True, blank=True)),
            ],
        ),
        migrations.AddField(
            model_name='booking',
            name='waitinglist_spot',
            field=models.IntegerField(default=0, verbose_name='Ventelisteposition'),
        ),
        migrations.AddField(
            model_name='visit',
            name='waiting_list_deadline_days',
            field=models.IntegerField(null=True, verbose_name='Lukning af venteliste (dage inden bes\xf8g)', blank=True),
        ),
        migrations.AddField(
            model_name='visit',
            name='waiting_list_deadline_hours',
            field=models.IntegerField(null=True, verbose_name='Lukning af venteliste (timer inden bes\xf8g)', blank=True),
        ),
        migrations.AddField(
            model_name='visit',
            name='waiting_list_length',
            field=models.IntegerField(null=True, verbose_name='Antal pladser', blank=True),
        ),
        migrations.AlterField(
            model_name='visit',
            name='do_create_waiting_list',
            field=models.BooleanField(default=False, verbose_name='Ventelister'),
        ),
        migrations.AddField(
            model_name='waitinglist',
            name='guests',
            field=models.ManyToManyField(to='booking.Booking', verbose_name='Tilmeldinger'),
        ),
    ]
