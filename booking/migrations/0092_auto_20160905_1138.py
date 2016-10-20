# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0091_refactor_changes'),
    ]

    operations = [
        migrations.RenameField(
            model_name='booking',
            old_name='visitoccurrence',
            new_name='visit',
        ),
        migrations.RenameField(
            model_name='emailtemplate',
            old_name='unit',
            new_name='organizationalunit',
        ),
        migrations.RenameField(
            model_name='locality',
            old_name='unit',
            new_name='organizationalunit',
        ),
        migrations.RenameField(
            model_name='productautosend',
            old_name='visit',
            new_name='product',
        ),
        migrations.RenameField(
            model_name='resource',
            old_name='unit',
            new_name='organizationalunit',
        ),
        migrations.RenameField(
            model_name='resource',
            old_name='lokaleansvarlige',
            new_name='roomresponsible',
        ),
        migrations.RenameField(
            model_name='room',
            old_name='visit',
            new_name='product',
        ),
        migrations.RenameField(
            model_name='roomresponsible',
            old_name='unit',
            new_name='organizationalunit',
        ),
        migrations.RenameField(
            model_name='visit',
            old_name='visit',
            new_name='product',
        ),
        migrations.RenameField(
            model_name='visitautosend',
            old_name='visitoccurrence',
            new_name='visit',
        ),
        migrations.RenameField(
            model_name='visitcomment',
            old_name='visitoccurrence',
            new_name='visit',
        ),
        migrations.AlterField(
            model_name='visit',
            name='hosts',
            field=models.ManyToManyField(related_name='hosted_visits', verbose_name='Tilknyttede v\xe6rter', to=settings.AUTH_USER_MODEL, blank=True),
        ),
        migrations.AlterField(
            model_name='visit',
            name='hosts_rejected',
            field=models.ManyToManyField(related_name='rejected_hosted_visits', verbose_name='V\xe6rter, som har afsl\xe5et', to=settings.AUTH_USER_MODEL, blank=True),
        ),
        migrations.AlterField(
            model_name='visit',
            name='teachers',
            field=models.ManyToManyField(related_name='taught_visits', verbose_name='Tilknyttede undervisere', to=settings.AUTH_USER_MODEL, blank=True),
        ),
        migrations.AlterField(
            model_name='visit',
            name='teachers_rejected',
            field=models.ManyToManyField(related_name='rejected_taught_visits', verbose_name='Undervisere, som har afsl\xe5et', to=settings.AUTH_USER_MODEL, blank=True),
        ),
    ]
