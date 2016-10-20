# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import datetime
import booking.utils
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0048_auto_20160311_1341'),
    ]

    operations = [
        migrations.AddField(
            model_name='booking',
            name='created_time',
            field=models.DateTimeField(default=datetime.datetime(2016, 3, 14, 13, 26, 12, 766409, tzinfo=utc), auto_now_add=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='autosend',
            name='days',
            field=models.PositiveSmallIntegerField(null=True, verbose_name='Dage', blank=True),
        ),
        migrations.AlterField(
            model_name='autosend',
            name='template_key',
            field=models.IntegerField(verbose_name='Skabelon', choices=[(1, 'G\xe6st: Booking oprettet'), (7, 'G\xe6st: Generel besked'), (2, 'V\xe6rt: Booking oprettet'), (3, 'V\xe6rt: Frivillige undervisere'), (4, 'V\xe6rt: Frivillige v\xe6rter'), (5, 'V\xe6rt: Tilknyttet bes\xf8g'), (6, 'V\xe6rt: Foresp\xf8rg lokale'), (8, 'Alle: Booking f\xe6rdigplanlagt'), (9, 'Alle: Booking aflyst'), (10, 'Alle: Reminder om booking'), (11, 'V\xe6rt: Ledig v\xe6rtsrolle')]),
        ),
        migrations.AlterField(
            model_name='emailtemplate',
            name='key',
            field=models.IntegerField(default=1, verbose_name='Key', choices=[(1, 'G\xe6st: Booking oprettet'), (7, 'G\xe6st: Generel besked'), (2, 'V\xe6rt: Booking oprettet'), (3, 'V\xe6rt: Frivillige undervisere'), (4, 'V\xe6rt: Frivillige v\xe6rter'), (5, 'V\xe6rt: Tilknyttet bes\xf8g'), (6, 'V\xe6rt: Foresp\xf8rg lokale'), (8, 'Alle: Booking f\xe6rdigplanlagt'), (9, 'Alle: Booking aflyst'), (10, 'Alle: Reminder om booking'), (11, 'V\xe6rt: Ledig v\xe6rtsrolle')]),
        ),
        migrations.AlterField(
            model_name='studymaterial',
            name='file',
            field=models.FileField(storage=booking.utils.CustomStorage(), null=True, upload_to=b'material', blank=True),
        ),
    ]
