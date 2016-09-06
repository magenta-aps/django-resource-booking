# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0046_auto_20160310_1057'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='StudyMaterial_Migrate',
            new_name='StudyMaterial',
        ),
    ]
