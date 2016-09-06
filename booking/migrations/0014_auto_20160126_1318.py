# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0013_auto_20160122_1527'),
    ]

    operations = [
        migrations.CreateModel(
            name='Booker',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('firstname', models.CharField(max_length=64, verbose_name='Fornavn')),
                ('lastname', models.CharField(max_length=64, verbose_name='Efternavn')),
                ('email', models.EmailField(max_length=64, verbose_name='Email')),
                ('phone', models.CharField(max_length=14, verbose_name='Telefon')),
                ('line', models.IntegerField(blank=True, verbose_name='Linje', choices=[(0, 'stx'), (1, 'hf'), (2, 'htx'), (3, 'eux'), (5, 'hhx')])),
                ('level', models.IntegerField(blank=True, verbose_name='Niveau', choices=[(1, '1.g'), (2, '2.g'), (3, '3.g'), (4, 'Student'), (5, 'Andet')])),
                ('attendee_count', models.IntegerField(verbose_name='Antal deltagere')),
                ('notes', models.TextField(verbose_name='Bem\xe6rkninger', blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='Booking',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
            ],
        ),
        migrations.CreateModel(
            name='PostCode',
            fields=[
                ('number', models.IntegerField(serialize=False, primary_key=True)),
                ('city', models.CharField(max_length=48)),
            ],
        ),
        migrations.CreateModel(
            name='Region',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=16)),
            ],
        ),
        migrations.CreateModel(
            name='School',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=128)),
                ('postcode', models.ForeignKey(to='booking.PostCode', null=True)),
            ],
        ),
        migrations.AlterField(
            model_name='resource',
            name='description',
            field=models.TextField(verbose_name='Beskrivelse'),
        ),
        migrations.AlterField(
            model_name='resource',
            name='subjects',
            field=models.ManyToManyField(to='booking.Subject', verbose_name='Fag'),
        ),
        migrations.AlterField(
            model_name='resource',
            name='teaser',
            field=models.TextField(max_length=210, verbose_name='Teaser'),
        ),
        migrations.AlterField(
            model_name='resource',
            name='unit',
            field=models.ForeignKey(verbose_name='Enhed', to='booking.Unit', null=True),
        ),
        migrations.AlterField(
            model_name='visit',
            name='price',
            field=models.DecimalField(default=0, verbose_name='Pris', max_digits=10, decimal_places=2, blank=True),
        ),
        migrations.CreateModel(
            name='ClassBooking',
            fields=[
                ('booking_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='booking.Booking')),
                ('time', models.DateTimeField(null=True, verbose_name='Tidspunkt', blank=True)),
                ('desired_time', models.CharField(max_length=2000, null=True, verbose_name='\xd8nsket tidspunkt', blank=True)),
                ('tour_desired', models.BooleanField(verbose_name='Rundvisning \xf8nsket')),
            ],
            bases=('booking.booking',),
        ),
        migrations.CreateModel(
            name='TeacherBooking',
            fields=[
                ('booking_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='booking.Booking')),
                ('subjects', models.ManyToManyField(to='booking.Subject')),
            ],
            bases=('booking.booking',),
        ),
        migrations.AddField(
            model_name='postcode',
            name='region',
            field=models.ForeignKey(to='booking.Region'),
        ),
        migrations.AddField(
            model_name='booking',
            name='booker',
            field=models.ForeignKey(to='booking.Booker'),
        ),
        migrations.AddField(
            model_name='booking',
            name='visit',
            field=models.ForeignKey(to='booking.Visit', null=True),
        ),
        migrations.AddField(
            model_name='booker',
            name='school',
            field=models.ForeignKey(verbose_name='Skole', to='booking.School', null=True),
        ),
    ]
