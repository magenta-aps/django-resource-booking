# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0017_auto_20160201_1404'),
    ]

    operations = [
        migrations.CreateModel(
            name='ResourceGrundskoleFag',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('class_level_min', models.IntegerField(default=0, verbose_name='Klassetrin fra', choices=[(0, '0'), (1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5'), (6, '6'), (7, '7'), (8, '8'), (9, '9'), (10, '10')])),
                ('class_level_max', models.IntegerField(default=10, verbose_name='Klassetrin til', choices=[(0, '0'), (1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5'), (6, '6'), (7, '7'), (8, '8'), (9, '9'), (10, '10')])),
            ],
            options={
                'verbose_name': 'Grundskolefagtilknytning',
                'verbose_name_plural': 'Grundskolefagtilknytninger',
            },
        ),
        migrations.CreateModel(
            name='ResourceGymnasieFag',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('level', models.ManyToManyField(to='booking.GymnasieLevel')),
            ],
            options={
                'verbose_name': 'Gymnasiefagtilknytning',
                'verbose_name_plural': 'Gymnasiefagtilknytninger',
            },
        ),
        migrations.RemoveField(
            model_name='resource',
            name='class_level_max',
        ),
        migrations.RemoveField(
            model_name='resource',
            name='class_level_min',
        ),
        migrations.RemoveField(
            model_name='resource',
            name='level',
        ),
        migrations.RemoveField(
            model_name='resource',
            name='subjects',
        ),
        migrations.AddField(
            model_name='resourcegymnasiefag',
            name='resource',
            field=models.ForeignKey(to='booking.Resource'),
        ),
        migrations.AddField(
            model_name='resourcegymnasiefag',
            name='subject',
            field=models.ForeignKey(to='booking.Subject'),
        ),
        migrations.AddField(
            model_name='resourcegrundskolefag',
            name='resource',
            field=models.ForeignKey(to='booking.Resource'),
        ),
        migrations.AddField(
            model_name='resourcegrundskolefag',
            name='subject',
            field=models.ForeignKey(to='booking.Subject'),
        ),
        migrations.AddField(
            model_name='resource',
            name='grundskolefag',
            field=models.ManyToManyField(related_name='grundskole_resources', verbose_name='Grundskolefag', to='booking.Subject', through='booking.ResourceGrundskoleFag', blank=True),
        ),
        migrations.AddField(
            model_name='resource',
            name='gymnasiefag',
            field=models.ManyToManyField(related_name='gymnasie_resources', verbose_name='Gymnasiefag', to='booking.Subject', through='booking.ResourceGymnasieFag', blank=True),
        ),
    ]
