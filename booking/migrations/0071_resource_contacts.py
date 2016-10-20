# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0070_auto_20160520_1204'),
    ]

    operations = [
        migrations.AddField(
            model_name='resource',
            name='contacts',
            field=models.ManyToManyField(related_name='contact_visit', verbose_name='Kontaktpersoner', to='booking.UserPerson', blank=True),
        ),
    ]
