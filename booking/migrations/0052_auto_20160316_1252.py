# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('booking', '0051_resource_created_by'),
    ]

    operations = [
        migrations.AddField(
            model_name='visit',
            name='default_hosts',
            field=models.ManyToManyField(related_name='hosted_visits', verbose_name='Faste v\xe6rter', to=settings.AUTH_USER_MODEL, blank=True),
        ),
        migrations.AddField(
            model_name='visit',
            name='default_teachers',
            field=models.ManyToManyField(related_name='taught_visits', verbose_name='Faste undervisere', to=settings.AUTH_USER_MODEL, blank=True),
        ),
        migrations.AlterField(
            model_name='autosend',
            name='template_key',
            field=models.IntegerField(verbose_name='Skabelon', choices=[(1, 'G\xe6st: Booking oprettet'), (7, 'G\xe6st: Generel besked'), (2, 'V\xe6rt: Booking oprettet'), (3, 'V\xe6rt: Frivillige undervisere'), (4, 'V\xe6rt: Frivillige v\xe6rter'), (5, 'V\xe6rt: Tilknyttet bes\xf8g'), (6, 'V\xe6rt: Foresp\xf8rg lokale'), (8, 'Alle: Booking f\xe6rdigplanlagt'), (9, 'Alle: Booking aflyst'), (10, 'Alle: Reminder om booking'), (11, 'V\xe6rt: Ledig v\xe6rtsrolle'), (12, 'Foresp\xf8rgsel fra bruger')]),
        ),
        migrations.AlterField(
            model_name='emailtemplate',
            name='key',
            field=models.IntegerField(default=1, verbose_name='Key', choices=[(1, 'G\xe6st: Booking oprettet'), (7, 'G\xe6st: Generel besked'), (2, 'V\xe6rt: Booking oprettet'), (3, 'V\xe6rt: Frivillige undervisere'), (4, 'V\xe6rt: Frivillige v\xe6rter'), (5, 'V\xe6rt: Tilknyttet bes\xf8g'), (6, 'V\xe6rt: Foresp\xf8rg lokale'), (8, 'Alle: Booking f\xe6rdigplanlagt'), (9, 'Alle: Booking aflyst'), (10, 'Alle: Reminder om booking'), (11, 'V\xe6rt: Ledig v\xe6rtsrolle'), (12, 'Foresp\xf8rgsel fra bruger')]),
        ),
    ]
