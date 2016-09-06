# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import djorm_pgfulltext.fields


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0021_auto_20160203_1519'),
    ]

    operations = [
        migrations.AddField(
            model_name='booking',
            name='extra_search_text',
            field=models.TextField(default=b'', verbose_name='Tekst-v\xe6rdier til friteksts\xf8gning', editable=False, blank=True),
        ),
        migrations.AddField(
            model_name='booking',
            name='search_index',
            field=djorm_pgfulltext.fields.VectorField(default=b'', serialize=False, null=True, editable=False, db_index=True),
        ),
    ]
