# -*- coding: utf-8 -*-
# Generated by Django 1.11.20 on 2020-08-21 12:22
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0007_visit_is_multiproductvisit'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='teaser',
            field=models.TextField(max_length=300, verbose_name='Teaser'),
        ),
        migrations.AlterField(
            model_name='product',
            name='title',
            field=models.CharField(max_length=80, verbose_name='Titel'),
        ),
    ]