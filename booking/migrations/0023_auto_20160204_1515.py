# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0022_auto_20160204_1146'),
    ]

    operations = [
        migrations.AlterField(
            model_name='booker',
            name='level',
            field=models.IntegerField(verbose_name='Niveau', choices=[(7, '1. klasse'), (8, '2. klasse'), (9, '3. klasse'), (10, '4. klasse'), (11, '5. klasse'), (12, '6. klasse'), (13, '7. klasse'), (14, '8. klasse'), (15, '9. klasse'), (16, '10. klasse'), (1, '1.g'), (2, '2.g'), (3, '3.g'), (4, 'Student'), (5, 'Andet')]),
        ),
        migrations.AlterField(
            model_name='booker',
            name='line',
            field=models.IntegerField(blank=True, null=True, verbose_name='Linje', choices=[(0, 'stx'), (1, 'hf'), (2, 'htx'), (3, 'eux'), (5, 'hhx')]),
        ),
        migrations.AlterField(
            model_name='school',
            name='type',
            field=models.IntegerField(default=1, verbose_name='Uddannelsestype', choices=[(2, 'Folkeskole'), (1, 'Gymnasie')]),
        ),
    ]
