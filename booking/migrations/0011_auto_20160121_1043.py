# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0010_auto_20160121_1020'),
    ]

    operations = [
        migrations.AlterField(
            model_name='visit',
            name='locality',
            field=models.ForeignKey(verbose_name='Lokalitet', blank=True, to='booking.Locality', null=True),
        ),
    ]
