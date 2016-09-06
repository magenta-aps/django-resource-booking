# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import datetime
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0031_auto_20160217_1238'),
    ]

    operations = [
        migrations.AlterField(
            model_name='emailtemplate',
            name='key',
            field=models.IntegerField(default=1, verbose_name='Key', choices=[(1, 'G\xe6st: Booking oprettet'), (7, 'G\xe6st: Generel besked'), (2, 'V\xe6rt: Booking oprettet'), (3, 'V\xe6rt: Frivillige undervisere'), (4, 'V\xe6rt: Frivillige v\xe6rter'), (5, 'V\xe6rt: Tilknyttet bes\xf8g'), (6, 'V\xe6rt: Foresp\xf8rg lokale'), (8, 'V\xe6rt: Booking f\xe6rdigplanlagt'), (9, 'Alle: Booking aflyst'), (10, 'Alle: Reminder om booking')]),
        ),
        migrations.AlterField(
            model_name='kuemailmessage',
            name='created',
            field=models.DateTimeField(default=datetime.datetime(2016, 2, 18, 14, 32, 18, 658716, tzinfo=utc)),
        ),
    ]
