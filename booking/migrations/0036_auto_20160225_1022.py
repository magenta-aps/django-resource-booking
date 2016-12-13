# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0035_auto_20160224_1559'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='otherresource',
            name='link',
        ),
        migrations.AlterField(
            model_name='resource',
            name='type',
            field=models.IntegerField(default=5, choices=[(0, 'Studerende for en dag'), (9, 'Studiepraktik'), (7, '\xc5bent hus'), (6, 'L\xe6rerarrangement'), (1, 'Bes\xf8g med klassen'), (3, 'Studieretningsprojekt'), (8, 'Lektiehj\xe6lp'), (4, 'Andre tilbud'), (5, 'Undervisningsmateriale')]),
        ),
    ]
