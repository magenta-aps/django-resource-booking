# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0054_auto_20160316_1402'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='bookedroom',
            options={'verbose_name': 'lokale for bes\xf8g', 'verbose_name_plural': 'lokaler for bes\xf8g'},
        ),
        migrations.AlterModelOptions(
            name='visitoccurrence',
            options={'ordering': ['start_datetime'], 'verbose_name': 'bes\xf8g', 'verbose_name_plural': 'bes\xf8g'},
        ),
        migrations.AlterField(
            model_name='visitoccurrence',
            name='workflow_status',
            field=models.IntegerField(default=0, choices=[(0, 'Under planl\xe6gning'), (1, 'Afvist af undervisere eller v\xe6rter'), (2, 'Planlagt (ressourcer tildelt)'), (9, 'Planlagt og lukket for booking'), (3, 'Bekr\xe6ftet af booker'), (4, 'P\xe5mindelse afsendt'), (5, 'Afviklet'), (6, 'Evalueret'), (7, 'Aflyst'), (8, 'Udeblevet')]),
        ),
    ]
