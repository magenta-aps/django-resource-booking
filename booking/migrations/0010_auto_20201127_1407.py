# Generated by Django 2.2.17 on 2020-11-27 13:07

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0009_auto_20201030_1055'),
    ]

    operations = [
        migrations.AlterField(
            model_name='bookinggrundskolesubjectlevel',
            name='subject',
            field=models.ForeignKey(limit_choices_to={'subject_type__in': [2]}, on_delete=django.db.models.deletion.CASCADE, to='booking.Subject'),
        ),
        migrations.AlterField(
            model_name='bookinggymnasiesubjectlevel',
            name='subject',
            field=models.ForeignKey(limit_choices_to={'subject_type__in': [1]}, on_delete=django.db.models.deletion.CASCADE, to='booking.Subject'),
        ),
        migrations.AlterField(
            model_name='product',
            name='catering_available',
            field=models.BooleanField(blank=True, default=False, verbose_name='Mulighed for forplejning'),
        ),
        migrations.AlterField(
            model_name='product',
            name='custom_available',
            field=models.BooleanField(blank=True, default=False, verbose_name='Andet'),
        ),
        migrations.AlterField(
            model_name='product',
            name='potentielle_undervisere',
            field=models.ManyToManyField(blank=True, limit_choices_to={'userprofile__user_role__role': 0}, related_name='potentiel_underviser_for_set', to=settings.AUTH_USER_MODEL, verbose_name='Potentielle undervisere'),
        ),
        migrations.AlterField(
            model_name='product',
            name='potentielle_vaerter',
            field=models.ManyToManyField(blank=True, limit_choices_to={'userprofile__user_role__role': 1}, related_name='potentiel_vaert_for_set', to=settings.AUTH_USER_MODEL, verbose_name='Potentielle værter'),
        ),
        migrations.AlterField(
            model_name='product',
            name='presentation_available',
            field=models.BooleanField(blank=True, default=False, verbose_name='Mulighed for oplæg om uddannelse'),
        ),
        migrations.AlterField(
            model_name='product',
            name='tour_available',
            field=models.BooleanField(blank=True, default=False, verbose_name='Mulighed for rundvisning'),
        ),
        migrations.AlterField(
            model_name='productgrundskolefag',
            name='subject',
            field=models.ForeignKey(limit_choices_to={'subject_type__in': [2, 3]}, on_delete=django.db.models.deletion.CASCADE, to='booking.Subject'),
        ),
        migrations.AlterField(
            model_name='productgymnasiefag',
            name='subject',
            field=models.ForeignKey(limit_choices_to={'subject_type__in': [1, 3]}, on_delete=django.db.models.deletion.CASCADE, to='booking.Subject'),
        ),
        migrations.AlterField(
            model_name='visit',
            name='hosts',
            field=models.ManyToManyField(blank=True, limit_choices_to={'userprofile__user_role__role': 1}, related_name='hosted_visits', to=settings.AUTH_USER_MODEL, verbose_name='Tilknyttede værter'),
        ),
        migrations.AlterField(
            model_name='visit',
            name='hosts_rejected',
            field=models.ManyToManyField(blank=True, limit_choices_to={'userprofile__user_role__role': 1}, related_name='rejected_hosted_visits', to=settings.AUTH_USER_MODEL, verbose_name='Værter, som har afslået'),
        ),
        migrations.AlterField(
            model_name='visit',
            name='teachers',
            field=models.ManyToManyField(blank=True, limit_choices_to={'userprofile__user_role__role': 0}, related_name='taught_visits', to=settings.AUTH_USER_MODEL, verbose_name='Tilknyttede undervisere'),
        ),
        migrations.AlterField(
            model_name='visit',
            name='teachers_rejected',
            field=models.ManyToManyField(blank=True, limit_choices_to={'userprofile__user_role__role': 0}, related_name='rejected_taught_visits', to=settings.AUTH_USER_MODEL, verbose_name='Undervisere, som har afslået'),
        ),
    ]