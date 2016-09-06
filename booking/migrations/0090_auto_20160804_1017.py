# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('booking', '0089_auto_20160803_1134'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='visitoccurrence',
            name='host_status',
        ),
        migrations.RemoveField(
            model_name='visitoccurrence',
            name='teacher_status',
        ),
        migrations.AddField(
            model_name='resource',
            name='potentielle_undervisere',
            field=models.ManyToManyField(related_name='potentiel_underviser_for_set', verbose_name='Potentielle undervisere', to=settings.AUTH_USER_MODEL, blank=True),
        ),
        migrations.AddField(
            model_name='resource',
            name='potentielle_vaerter',
            field=models.ManyToManyField(related_name='potentiel_vaert_for_set', verbose_name='Potentielle v\xe6rter', to=settings.AUTH_USER_MODEL, blank=True),
        ),
        migrations.AddField(
            model_name='visitoccurrence',
            name='override_needed_hosts',
            field=models.IntegerField(blank=True, null=True, verbose_name='Antal n\xf8dvendige v\xe6rter', choices=[(None, 'Brug v\xe6rdi fra tilbud'), (1, 1), (2, 2), (3, 3), (4, 4), (5, 5), (6, 6), (7, 7), (8, 8), (9, 9)]),
        ),
        migrations.AddField(
            model_name='visitoccurrence',
            name='override_needed_teachers',
            field=models.IntegerField(blank=True, null=True, verbose_name='Antal n\xf8dvendige undervisere', choices=[(None, 'Brug v\xe6rdi fra tilbud'), (1, 1), (2, 2), (3, 3), (4, 4), (5, 5), (6, 6), (7, 7), (8, 8), (9, 9)]),
        ),
        migrations.AlterField(
            model_name='visitoccurrence',
            name='hosts',
            field=models.ManyToManyField(related_name='hosted_visitoccurrences', verbose_name='Tilknyttede v\xe6rter', to=settings.AUTH_USER_MODEL, blank=True),
        ),
        migrations.AlterField(
            model_name='visitoccurrence',
            name='teachers',
            field=models.ManyToManyField(related_name='taught_visitoccurrences', verbose_name='Tilknyttede undervisere', to=settings.AUTH_USER_MODEL, blank=True),
        ),
    ]
