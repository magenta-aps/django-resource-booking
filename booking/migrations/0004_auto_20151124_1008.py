# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0003_auto_20151124_1006'),
    ]

    operations = [
        migrations.AlterField(
            model_name='unit',
            name='contact',
            field=models.ForeignKey(blank=True, to='booking.Person', null=True),
        ),
    ]
