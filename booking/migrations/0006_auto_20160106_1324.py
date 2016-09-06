# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0005_auto_20160106_1145'),
    ]

    operations = [
        migrations.AddField(
            model_name='visit',
            name='rooms_needed',
            field=models.BooleanField(default=True, verbose_name='Tilbuddet kr\xe6ver brug af et eller flere lokaler'),
        ),
        migrations.AlterField(
            model_name='visit',
            name='rooms_assignment',
            field=models.IntegerField(default=0, verbose_name='Tildeling af lokale(r)', choices=[(0, 'Lokaler tildeles p\xe5 forh\xe5nd'), (1, 'Lokaler tildeles ved booking')]),
        ),
    ]
