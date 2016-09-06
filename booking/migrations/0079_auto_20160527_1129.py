# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0078_auto_20160526_1437'),
    ]

    operations = [
        migrations.CreateModel(
            name='BookingGrundskoleSubjectLevel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('booking', models.ForeignKey(to='booking.Booking')),
            ],
            options={
                'verbose_name': 'klasseniveau for booking (grundskole)',
                'verbose_name_plural': 'klasseniveauer for bookinger(grundskole)',
            },
        ),
        migrations.CreateModel(
            name='GrundskoleLevel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('level', models.IntegerField(blank=True, null=True, verbose_name='Grundskoleniveau', choices=[(0, '0. klasse'), (1, '1. klasse'), (2, '2. klasse'), (3, '3. klasse'), (4, '4. klasse'), (5, '5. klasse'), (6, '6. klasse'), (7, '7. klasse'), (8, '8. klasse'), (9, '9. klasse'), (10, '10. klasse')])),
            ],
            options={
                'ordering': ['level'],
                'verbose_name': 'Grundskoleniveau',
                'verbose_name_plural': 'Grundskoleniveauer',
            },
        ),
        migrations.RenameModel(
            old_name='BookingSubjectLevel',
            new_name='BookingGymnasieSubjectLevel',
        ),
        migrations.AlterModelOptions(
            name='bookinggymnasiesubjectlevel',
            options={'verbose_name': 'fagniveau for booking (gymnasium)', 'verbose_name_plural': 'fagniveauer for bookinger (gymnasium)'},
        ),
        migrations.AddField(
            model_name='bookinggrundskolesubjectlevel',
            name='level',
            field=models.ForeignKey(to='booking.GrundskoleLevel'),
        ),
        migrations.AddField(
            model_name='bookinggrundskolesubjectlevel',
            name='subject',
            field=models.ForeignKey(to='booking.Subject'),
        ),
    ]
