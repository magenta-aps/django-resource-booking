# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0009_auto_20160121_0935'),
    ]

    operations = [
        migrations.AlterField(
            model_name='resource',
            name='type',
            field=models.IntegerField(default=5, choices=[(0, 'Studerende for en dag'), (9, 'Studiepraktik'), (7, '\xc5bent hus'), (6, 'L\xe6rerarrangement'), (1, 'Bes\xf8g med klassen'), (3, 'Studieretningsprojekt'), (8, 'Opgavehj\xe6lp'), (4, 'Enkeltst\xe5ende event'), (5, 'Undervisningsmateriale')]),
        ),
    ]
