# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0019_auto_20160203_0914'),
    ]

    operations = [
        migrations.AddField(
            model_name='school',
            name='type',
            field=models.IntegerField(default=1, verbose_name='Uddannelsestype', choices=[(0, 'Folkeskole'), (1, 'Gymnasie')]),
        ),
    ]
