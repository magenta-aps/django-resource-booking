# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0011_auto_20160121_1043'),
    ]

    operations = [
        migrations.AlterField(
            model_name='resource',
            name='audience',
            field=models.IntegerField(default=3, verbose_name='M\xe5lgruppe', choices=[(1, 'L\xe6rer'), (2, 'Elev'), (3, 'Alle')]),
        ),
    ]
