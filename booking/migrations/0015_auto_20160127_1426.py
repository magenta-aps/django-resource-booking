# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0014_auto_20160126_1318'),
    ]

    operations = [
        migrations.CreateModel(
            name='BookingSubjectLevel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('booking', models.ForeignKey(to='booking.Booking')),
            ],
        ),
        migrations.CreateModel(
            name='GymnasieLevel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('level', models.IntegerField(blank=True, null=True, verbose_name='Gymnasieniveau', choices=[(0, 'A'), (1, 'B'), (2, 'C')])),
            ],
        ),
        migrations.AddField(
            model_name='bookingsubjectlevel',
            name='level',
            field=models.ForeignKey(to='booking.GymnasieLevel'),
        ),
        migrations.AddField(
            model_name='bookingsubjectlevel',
            name='subject',
            field=models.ForeignKey(to='booking.Subject'),
        ),
    ]
