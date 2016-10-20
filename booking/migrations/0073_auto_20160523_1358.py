# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0072_auto_20160520_1333'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='bookedroom',
            name='booking',
        ),
        migrations.AlterModelOptions(
            name='room',
            options={'verbose_name': 'lokale', 'verbose_name_plural': 'lokaler'},
        ),
        migrations.RemoveField(
            model_name='visit',
            name='rooms_assignment',
        ),
        migrations.AddField(
            model_name='resource',
            name='rooms',
            field=models.ManyToManyField(to='booking.Room', verbose_name='Lokaler', blank=True),
        ),
        migrations.AddField(
            model_name='room',
            name='locality',
            field=models.ForeignKey(verbose_name='Lokalitet', blank=True, to='booking.Locality', null=True),
        ),
        migrations.AddField(
            model_name='visitoccurrence',
            name='rooms',
            field=models.ManyToManyField(to='booking.Room', verbose_name='Lokaler', blank=True),
        ),
        migrations.AlterField(
            model_name='room',
            name='visit',
            field=models.ForeignKey(blank=True, editable=False, to='booking.Visit', null=True, verbose_name='Bes\xf8g'),
        ),
        migrations.AlterField(
            model_name='visitoccurrence',
            name='room_status',
            field=models.IntegerField(default=2, verbose_name='Status for tildeling af lokaler', choices=[(0, 'Tildeling af lokaler ikke p\xe5kr\xe6vet'), (2, 'Afventer tildeling/bekr\xe6ftelse'), (1, 'Tildelt/bekr\xe6ftet')]),
        ),
        migrations.DeleteModel(
            name='BookedRoom',
        ),
    ]
