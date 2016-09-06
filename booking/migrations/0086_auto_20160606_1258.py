# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0085_auto_20160603_1516'),
    ]

    operations = [
        migrations.AlterField(
            model_name='visit',
            name='needed_hosts',
            field=models.IntegerField(default=0, verbose_name='N\xf8dvendigt antal v\xe6rter', choices=[(None, b'---------'), (0, 'Ingen'), (1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5'), (6, '6'), (7, '7'), (8, '8'), (9, '9'), (10, '10'), (-10, 'Mere end 10')]),
        ),
        migrations.AlterField(
            model_name='visit',
            name='needed_teachers',
            field=models.IntegerField(default=0, verbose_name='N\xf8dvendigt antal undervisere', choices=[(None, b'---------'), (0, 'Ingen'), (1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5'), (6, '6'), (7, '7'), (8, '8'), (9, '9'), (10, '10'), (-10, 'Mere end 10')]),
        ),
    ]
