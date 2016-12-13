# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('booking', '0087_auto_20160622_1326'),
    ]

    operations = [
        migrations.AddField(
            model_name='visitoccurrence',
            name='hosts_rejected',
            field=models.ManyToManyField(related_name='rejected_hosted_visitoccurrences', verbose_name='V\xe6rter, som har afsl\xe5et', to=settings.AUTH_USER_MODEL, blank=True),
        ),
        migrations.AddField(
            model_name='visitoccurrence',
            name='teachers_rejected',
            field=models.ManyToManyField(related_name='rejected_taught_visitoccurrences', verbose_name='Undervisere, som har afsl\xe5et', to=settings.AUTH_USER_MODEL, blank=True),
        ),
    ]
