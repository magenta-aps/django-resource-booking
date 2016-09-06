# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0024_auto_20160205_1541'),
    ]

    operations = [
        migrations.CreateModel(
            name='EmailTemplate',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('key', models.IntegerField(default=1, verbose_name='Key', choices=[(1, 'Booking created')])),
                ('subject', models.CharField(max_length=77, verbose_name='Emne')),
                ('body', models.CharField(max_length=65584, verbose_name='Tekst')),
                ('unit', models.ForeignKey(verbose_name='Enhed', blank=True, to='booking.Unit', null=True)),
            ],
        ),
    ]
