# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0003_auto_20151209_1558'),
    ]

    operations = [
        migrations.AlterField(
            model_name='resource',
            name='extra_search_text',
            field=models.TextField(default=b'', verbose_name='Tekst-v\xe6rdier til friteksts\xf8gning', editable=False, blank=True),
        ),
    ]
