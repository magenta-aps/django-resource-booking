# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0004_auto_20151218_1142'),
    ]

    operations = [
        migrations.CreateModel(
            name='Room',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=64, verbose_name='Navn p\xe5 lokale')),
            ],
        ),
        migrations.RemoveField(
            model_name='visit',
            name='room',
        ),
        migrations.AddField(
            model_name='visit',
            name='rooms_assignment',
            field=models.IntegerField(default=0, verbose_name='Tildeling af lokale(r)', choices=[(0, 'Lokale tildeles p\xe5 bes\xf8g'), (1, 'Lokale tildeles ved booking')]),
        ),
        migrations.AddField(
            model_name='room',
            name='visit',
            field=models.ForeignKey(verbose_name='Bes\xf8g', to='booking.Visit'),
        ),
    ]
