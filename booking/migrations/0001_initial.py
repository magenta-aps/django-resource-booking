# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime
import uuid

import django.core.validators
import django.utils.timezone
import recurrence.fields
from django.conf import settings
from django.db import migrations, models

import booking.mixins
import booking.models
import booking.utils


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Autosend',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('template_key', models.IntegerField(verbose_name='Skabelon')),
                ('days', models.PositiveSmallIntegerField(null=True, verbose_name='Dage', blank=True)),
                ('enabled', models.BooleanField(default=True, verbose_name='Aktiv')),
            ],
        ),
        migrations.CreateModel(
            name='BookerResponseNonce',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uuid', models.UUIDField(default=uuid.uuid4)),
                ('created', models.DateTimeField(default=django.utils.timezone.now)),
                ('expires_in', models.DurationField(default=datetime.timedelta(2))),
            ],
        ),
        migrations.CreateModel(
            name='Booking',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('waitinglist_spot', models.IntegerField(default=0, verbose_name='Ventelisteposition')),
                ('notes', models.TextField(verbose_name='Bem\xe6rkninger', blank=True)),
                ('cancelled', models.BooleanField(default=False, verbose_name='Aflyst')),
            ],
            options={
                'verbose_name': 'booking',
                'verbose_name_plural': 'bookinger',
            },
        ),
        migrations.CreateModel(
            name='BookingGrundskoleSubjectLevel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
            ],
            options={
                'verbose_name': 'klasseniveau for booking (grundskole)',
                'verbose_name_plural': 'klasseniveauer for bookinger(grundskole)',
            },
        ),
        migrations.CreateModel(
            name='BookingGymnasieSubjectLevel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
            ],
            options={
                'verbose_name': 'fagniveau for booking (gymnasium)',
                'verbose_name_plural': 'fagniveauer for bookinger (gymnasium)',
            },
        ),
        migrations.CreateModel(
            name='Calendar',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
            ],
            bases=(booking.mixins.AvailabilityUpdaterMixin, models.Model),
        ),
        migrations.CreateModel(
            name='CalendarCalculatedAvailable',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('start', models.DateTimeField(verbose_name='Starttidspunkt')),
                ('end', models.DateTimeField(verbose_name='Sluttidspunkt', blank=True)),
                ('calendar', models.ForeignKey(verbose_name='Kalender', to='booking.Calendar')),
            ],
        ),
        migrations.CreateModel(
            name='CalendarEvent',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=60, verbose_name='Titel')),
                ('availability', models.IntegerField(default=0, verbose_name='Tilg\xe6ngelighed', choices=[(0, 'Tilg\xe6ngelig'), (1, 'Utilg\xe6ngelig')])),
                ('start', models.DateTimeField(verbose_name='Starttidspunkt')),
                ('end', models.DateTimeField(verbose_name='Sluttidspunkt', blank=True)),
                ('recurrences', recurrence.fields.RecurrenceField(null=True, verbose_name='Gentagelser', blank=True)),
                ('calendar', models.ForeignKey(verbose_name='Kalender', to='booking.Calendar')),
            ],
            bases=(booking.mixins.AvailabilityUpdaterMixin, models.Model),
        ),
        migrations.CreateModel(
            name='EmailTemplate',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('key', models.IntegerField(default=1, verbose_name='Type')),
                ('subject', models.CharField(max_length=65584, verbose_name='Emne')),
                ('body', models.CharField(max_length=65584, verbose_name='Tekst')),
            ],
        ),
        migrations.CreateModel(
            name='EmailTemplateType',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('key', models.IntegerField(default=1, verbose_name='Type')),
                ('name_da', models.CharField(max_length=1024, null=True, verbose_name='Navn')),
                ('ordering', models.IntegerField(default=0, verbose_name='Sortering')),
                ('manual_sending_visit_enabled', models.BooleanField(default=False)),
                ('manual_sending_mpv_enabled', models.BooleanField(default=False)),
                ('manual_sending_mpv_sub_enabled', models.BooleanField(default=False)),
                ('manual_sending_booking_enabled', models.BooleanField(default=False)),
                ('manual_sending_booking_mpv_enabled', models.BooleanField(default=False)),
                ('send_to_editors', models.BooleanField(default=False)),
                ('send_to_contactperson', models.BooleanField(default=False)),
                ('send_to_booker', models.BooleanField(default=False)),
                ('send_to_booker_on_waitinglist', models.BooleanField(default=False)),
                ('send_to_unit_hosts', models.BooleanField(default=False)),
                ('send_to_unit_teachers', models.BooleanField(default=False)),
                ('send_to_potential_hosts', models.BooleanField(default=False)),
                ('send_to_potential_teachers', models.BooleanField(default=False)),
                ('send_to_visit_hosts', models.BooleanField(default=False)),
                ('send_to_visit_teachers', models.BooleanField(default=False)),
                ('send_to_visit_added_host', models.BooleanField(default=False)),
                ('send_to_visit_added_teacher', models.BooleanField(default=False)),
                ('send_to_room_responsible', models.BooleanField(default=False)),
                ('enable_days', models.BooleanField(default=False)),
                ('enable_booking', models.BooleanField(default=False)),
                ('avoid_already_assigned', models.BooleanField(default=False)),
                ('is_default', models.BooleanField(default=False)),
                ('enable_autosend', models.BooleanField(default=False)),
                ('form_show', models.BooleanField(default=False)),
                ('disabled_for_product_types', models.TextField(default=None, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='EventTime',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('bookable', models.BooleanField(default=True, verbose_name='Kan bookes')),
                ('resource_status', models.IntegerField(default=1, verbose_name='Ressource-status', choices=[(1, 'Ressourcer ledige'), (2, 'Blokeret af manglende ressourcer'), (3, 'Ressourcer tildelt')])),
                ('start', models.DateTimeField(null=True, verbose_name='Starttidspunkt', blank=True)),
                ('end', models.DateTimeField(null=True, verbose_name='Sluttidspunkt', blank=True)),
                ('has_specific_time', models.BooleanField(default=True, verbose_name='Angivelse af tidspunkt', choices=[(True, 'B\xe5de dato og tidspunkt'), (False, 'Kun dato')])),
                ('notes', models.TextField(default=b'', verbose_name='Interne kommentarer', blank=True)),
                ('has_notified_start', models.BooleanField(default=False)),
                ('has_notified_end', models.BooleanField(default=False)),
            ],
            options={
                'ordering': ['start', 'end'],
                'verbose_name': 'tidspunkt',
                'verbose_name_plural': 'tidspunkter',
            },
        ),
        migrations.CreateModel(
            name='ExercisePresentation',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('value', models.IntegerField()),
                ('name', models.CharField(max_length=256)),
            ],
        ),
        migrations.CreateModel(
            name='GrundskoleLevel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('level', models.IntegerField(blank=True, null=True, verbose_name='Grundskoleniveau', choices=[(0, '0. klasse'), (1, '1. klasse'), (2, '2. klasse'), (3, '3. klasse'), (4, '4. klasse'), (5, '5. klasse'), (6, '6. klasse'), (7, '7. klasse'), (8, '8. klasse'), (9, '9. klasse'), (10, '10. klasse')])),
            ],
            options={
                'ordering': ['level'],
                'verbose_name': 'Grundskoleniveau',
                'verbose_name_plural': 'Grundskoleniveauer',
            },
        ),
        migrations.CreateModel(
            name='Guest',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('firstname', models.CharField(max_length=64, verbose_name='Fornavn')),
                ('lastname', models.CharField(max_length=64, verbose_name='Efternavn')),
                ('email', models.EmailField(max_length=64, verbose_name='Email')),
                ('phone', models.CharField(max_length=14, verbose_name='Telefon')),
                ('line', models.IntegerField(blank=True, null=True, verbose_name='Linje', choices=[(0, 'stx'), (1, 'hf'), (2, 'htx'), (3, 'eux'), (5, 'hhx')])),
                ('level', models.IntegerField(verbose_name='Niveau', choices=[(17, '0. klasse'), (7, '1. klasse'), (8, '2. klasse'), (9, '3. klasse'), (10, '4. klasse'), (11, '5. klasse'), (12, '6. klasse'), (13, '7. klasse'), (14, '8. klasse'), (15, '9. klasse'), (16, '10. klasse'), (1, '1.g'), (2, '2.g'), (3, '3.g'), (4, 'Afsluttet gymnasieuddannelse'), (5, 'Andet')])),
                ('attendee_count', models.IntegerField(blank=True, null=True, verbose_name='Antal deltagere', validators=[django.core.validators.MinValueValidator(1)])),
                ('teacher_count', models.IntegerField(default=None, null=True, verbose_name='Heraf l\xe6rere', blank=True)),
                ('consent', models.BooleanField(default=False, verbose_name='Samtykke')),
            ],
            options={
                'verbose_name': 'bes\xf8gende',
                'verbose_name_plural': 'bes\xf8gende',
            },
        ),
        migrations.CreateModel(
            name='Guide',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('value', models.IntegerField()),
                ('name', models.CharField(max_length=64)),
            ],
        ),
        migrations.CreateModel(
            name='GymnasieLevel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('level', models.IntegerField(blank=True, null=True, verbose_name='Gymnasieniveau', choices=[(0, 'A'), (1, 'B'), (2, 'C')])),
            ],
            options={
                'ordering': ['level'],
                'verbose_name': 'Gymnasieniveau',
                'verbose_name_plural': 'Gymnasieniveauer',
            },
        ),
        migrations.CreateModel(
            name='KUEmailMessage',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(default=django.utils.timezone.now)),
                ('subject', models.TextField()),
                ('body', models.TextField()),
                ('htmlbody', models.TextField(null=True, blank=True)),
                ('from_email', models.TextField()),
                ('original_from_email', models.TextField(null=True, blank=True)),
                ('recipients', models.TextField()),
                ('object_id', models.PositiveIntegerField(default=None, null=True)),
                ('reply_nonce', models.UUIDField(default=None, null=True, blank=True)),
                ('template_key', models.IntegerField(default=None, null=True, verbose_name='Template key', blank=True)),
                ('content_type', models.ForeignKey(default=None, to='contenttypes.ContentType', null=True)),
                ('reply_to_message', models.ForeignKey(verbose_name='Reply to', blank=True, to='booking.KUEmailMessage', null=True)),
                ('template_type', models.ForeignKey(default=None, blank=True, to='booking.EmailTemplateType', null=True, verbose_name='Template type')),
            ],
        ),
        migrations.CreateModel(
            name='KUEmailRecipient',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.TextField(null=True, blank=True)),
                ('formatted_address', models.TextField(null=True, blank=True)),
                ('email', models.TextField(null=True, blank=True)),
                ('type', models.IntegerField(default=0, choices=[(0, 'Anden'), (1, 'G\xe6st'), (2, 'Underviser'), (3, 'V\xe6rt'), (4, 'Koordinator'), (6, 'Modtager af sp\xf8rgsm\xe5l'), (7, 'Lokaleansvarlig'), (8, 'Tilbudsansvarlig'), (9, 'Enhedsansvarlig')])),
                ('email_message', models.ForeignKey(to='booking.KUEmailMessage')),
                ('guest', models.ForeignKey(blank=True, to='booking.Guest', null=True)),
                ('user', models.ForeignKey(blank=True, to=settings.AUTH_USER_MODEL, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Link',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('url', models.URLField()),
                ('name', models.CharField(max_length=256)),
                ('description', models.CharField(max_length=256, blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='Locality',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=256, verbose_name='Navn')),
                ('description', models.TextField(verbose_name='Beskrivelse', blank=True)),
                ('address_line', models.CharField(max_length=256, verbose_name='Adresse')),
                ('zip_city', models.CharField(max_length=256, verbose_name='Postnummer og by')),
                ('no_address', models.BooleanField(default=False)),
            ],
            options={
                'ordering': ['name'],
                'verbose_name': 'lokalitet',
                'verbose_name_plural': 'lokaliteter',
            },
        ),
        migrations.CreateModel(
            name='MultiProductVisitTemp',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('date', models.DateField(verbose_name='Dato')),
                ('updated', models.DateTimeField(auto_now=True)),
                ('notes', models.TextField(verbose_name='Bem\xe6rkninger', blank=True)),
                ('required_visits', models.PositiveIntegerField(default=2, verbose_name='Antal \xf8nskede bes\xf8g')),
            ],
        ),
        migrations.CreateModel(
            name='MultiProductVisitTempProduct',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('index', models.IntegerField()),
                ('multiproductvisittemp', models.ForeignKey(to='booking.MultiProductVisitTemp')),
            ],
        ),
        migrations.CreateModel(
            name='Municipality',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=30, verbose_name='Navn')),
            ],
            options={
                'verbose_name': 'kommune',
                'verbose_name_plural': 'kommuner',
            },
        ),
        migrations.CreateModel(
            name='ObjectStatistics',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created_time', models.DateTimeField(auto_now_add=True)),
                ('updated_time', models.DateTimeField(auto_now_add=True)),
                ('visited_time', models.DateTimeField(null=True, blank=True)),
                ('display_counter', models.IntegerField(default=0)),
            ],
        ),
        migrations.CreateModel(
            name='OrganizationalUnit',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100)),
                ('url', models.URLField(null=True, verbose_name='Hjemmeside', blank=True)),
                ('autoassign_resources_enabled', models.BooleanField(default=False, verbose_name='Automatisk ressourcetildeling mulig')),
                ('contact', models.ForeignKey(related_name='contactperson_for_units', on_delete=django.db.models.deletion.SET_NULL, verbose_name='Kontaktperson', blank=True, to=settings.AUTH_USER_MODEL, null=True)),
                ('parent', models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, blank=True, to='booking.OrganizationalUnit', null=True)),
            ],
            options={
                'ordering': ['name'],
                'verbose_name': 'enhed',
                'verbose_name_plural': 'enheder',
            },
        ),
        migrations.CreateModel(
            name='OrganizationalUnitType',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=25)),
            ],
            options={
                'verbose_name': 'enhedstype',
                'verbose_name_plural': 'Enhedstyper',
            },
        ),
        migrations.CreateModel(
            name='PostCode',
            fields=[
                ('number', models.IntegerField(serialize=False, primary_key=True)),
                ('city', models.CharField(max_length=48)),
            ],
            options={
                'verbose_name': 'postnummer',
                'verbose_name_plural': 'postnumre',
            },
        ),
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('type', models.IntegerField(default=5, choices=[(0, 'Studerende for en dag'), (9, 'Studiepraktik'), (7, '\xc5bent hus'), (6, 'Tilbud til undervisere'), (1, 'Bes\xf8g med klassen'), (3, 'Studieretningsprojekt'), (8, 'Lektiehj\xe6lp'), (4, 'Andre tilbud'), (5, 'Undervisningsmateriale')])),
                ('state', models.IntegerField(verbose_name='Status', choices=[(None, b'---------'), (0, 'Under udarbejdelse'), (1, 'Offentlig'), (2, 'Skjult')])),
                ('title', models.CharField(max_length=60, verbose_name='Titel')),
                ('teaser', models.TextField(max_length=210, verbose_name='Teaser')),
                ('description', models.TextField(verbose_name='Beskrivelse')),
                ('mouseover_description', models.CharField(max_length=512, verbose_name='Mouseover-tekst', blank=True)),
                ('institution_level', models.IntegerField(default=1, verbose_name='Institution', choices=[(1, 'Gymnasie'), (2, 'Grundskole'), (3, 'B\xe5de gymnasie og grundskole')])),
                ('time_mode', models.IntegerField(default=1, verbose_name='H\xe5ndtering af tidspunkter', choices=[(1, 'Tilbuddet har ingen tidspunkter og ingen tilmelding'), (2, 'Tilbuddets tidspunkter styres af ressourcer'), (6, 'Tilbuddets tidspunkter styres af ressourcer, med automatisk tildeling'), (3, 'Tilbuddet har faste tidspunkter'), (5, 'Tilbuddet har faste tidspunkter, men er uden tilmelding'), (4, 'G\xe6ster foresl\xe5r mulige tidspunkter')])),
                ('preparation_time', models.CharField(max_length=200, null=True, verbose_name='Forberedelsestid', blank=True)),
                ('price', models.DecimalField(decimal_places=2, default=0, max_digits=10, blank=True, null=True, verbose_name='Pris')),
                ('comment', models.TextField(verbose_name='Kommentar', blank=True)),
                ('search_index', booking.models.VectorField(default=b'', serialize=False, null=True, editable=False)),
                ('extra_search_text', models.TextField(default=b'', verbose_name='Tekst-v\xe6rdier til friteksts\xf8gning', editable=False, blank=True)),
                ('rooms_needed', models.BooleanField(default=True, verbose_name='Tilbuddet kr\xe6ver brug af et eller flere lokaler')),
                ('duration', models.CharField(blank=True, max_length=8, null=True, verbose_name='Varighed', choices=[(b'00:00', b'00:00'), (b'00:15', b'00:15'), (b'00:30', b'00:30'), (b'00:45', b'00:45'), (b'01:00', b'01:00'), (b'01:15', b'01:15'), (b'01:30', b'01:30'), (b'01:45', b'01:45'), (b'02:00', b'02:00'), (b'02:15', b'02:15'), (b'02:30', b'02:30'), (b'02:45', b'02:45'), (b'03:00', b'03:00'), (b'03:15', b'03:15'), (b'03:30', b'03:30'), (b'03:45', b'03:45'), (b'04:00', b'04:00'), (b'04:15', b'04:15'), (b'04:30', b'04:30'), (b'04:45', b'04:45'), (b'05:00', b'05:00'), (b'05:15', b'05:15'), (b'05:30', b'05:30'), (b'05:45', b'05:45'), (b'06:00', b'06:00'), (b'06:15', b'06:15'), (b'06:30', b'06:30'), (b'06:45', b'06:45'), (b'07:00', b'07:00'), (b'07:15', b'07:15'), (b'07:30', b'07:30'), (b'07:45', b'07:45'), (b'08:00', b'08:00'), (b'08:15', b'08:15'), (b'08:30', b'08:30'), (b'08:45', b'08:45'), (b'09:00', b'09:00'), (b'09:15', b'09:15'), (b'09:30', b'09:30'), (b'09:45', b'09:45'), (b'10:00', b'10:00'), (b'10:15', b'10:15'), (b'10:30', b'10:30'), (b'10:45', b'10:45'), (b'11:00', b'11:00'), (b'11:15', b'11:15'), (b'11:30', b'11:30'), (b'11:45', b'11:45')])),
                ('do_send_evaluation', models.BooleanField(default=False, verbose_name='Udsend evaluering')),
                ('is_group_visit', models.BooleanField(default=True, verbose_name='Gruppebes\xf8g')),
                ('minimum_number_of_visitors', models.IntegerField(null=True, verbose_name='Mindste antal deltagere', blank=True)),
                ('maximum_number_of_visitors', models.IntegerField(null=True, verbose_name='H\xf8jeste antal deltagere', blank=True)),
                ('do_create_waiting_list', models.BooleanField(default=False, verbose_name='Ventelister')),
                ('waiting_list_length', models.IntegerField(null=True, verbose_name='Antal pladser', blank=True)),
                ('waiting_list_deadline_days', models.IntegerField(null=True, verbose_name='Lukning af venteliste (dage inden bes\xf8g)', blank=True)),
                ('waiting_list_deadline_hours', models.IntegerField(null=True, verbose_name='Lukning af venteliste (timer inden bes\xf8g)', blank=True)),
                ('do_show_countdown', models.BooleanField(default=False, verbose_name='Vis nedt\xe6lling')),
                ('tour_available', models.BooleanField(default=False, verbose_name='Mulighed for rundvisning')),
                ('catering_available', models.BooleanField(default=False, verbose_name='Mulighed for forplejning')),
                ('presentation_available', models.BooleanField(default=False, verbose_name='Mulighed for opl\xe6g om uddannelse')),
                ('custom_available', models.BooleanField(default=False, verbose_name='Andet')),
                ('custom_name', models.CharField(max_length=50, null=True, verbose_name='Navn for tilpasset mulighed', blank=True)),
                ('needed_hosts', models.IntegerField(default=0, verbose_name='N\xf8dvendigt antal v\xe6rter', choices=[(None, b'---------'), (0, 'Ingen'), (1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5'), (6, '6'), (7, '7'), (8, '8'), (9, '9'), (10, '10'), (-10, 'Mere end 10')])),
                ('needed_teachers', models.IntegerField(default=0, verbose_name='N\xf8dvendigt antal undervisere', choices=[(None, b'---------'), (0, 'Ingen'), (1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5'), (6, '6'), (7, '7'), (8, '8'), (9, '9'), (10, '10'), (-10, 'Mere end 10')])),
                ('only_one_guest_per_visit', models.BooleanField(default=False, verbose_name='Der tillades kun 1 tilmelding pr. bes\xf8g')),
                ('booking_close_days_before', models.IntegerField(default=6, null=True, verbose_name='Antal dage f\xf8r afholdelse, hvor der lukkes for tilmeldinger')),
                ('booking_max_days_in_future', models.IntegerField(default=90, null=True, verbose_name='Maksimalt antal dage i fremtiden hvor der kan tilmeldes')),
                ('inquire_enabled', models.BooleanField(default=True, verbose_name='"Sp\xf8rg om tilbud" aktiveret')),
                ('education_name', models.CharField(max_length=50, null=True, verbose_name='Navn p\xe5 uddannelsen', blank=True)),
                ('calendar', models.OneToOneField(null=True, on_delete=django.db.models.deletion.SET_NULL, default=None, to='booking.Calendar')),
                ('created_by', models.ForeignKey(related_name='created_visits_set', on_delete=django.db.models.deletion.SET_NULL, verbose_name='Oprettet af', blank=True, to=settings.AUTH_USER_MODEL, null=True)),
            ],
            options={
                'verbose_name': 'tilbud',
                'verbose_name_plural': 'tilbud',
            },
            bases=(booking.mixins.AvailabilityUpdaterMixin, models.Model),
        ),
        migrations.CreateModel(
            name='ProductGrundskoleFag',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('class_level_min', models.IntegerField(default=0, verbose_name='Klassetrin fra', choices=[(0, '0'), (1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5'), (6, '6'), (7, '7'), (8, '8'), (9, '9'), (10, '10')])),
                ('class_level_max', models.IntegerField(default=10, verbose_name='Klassetrin til', choices=[(0, '0'), (1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5'), (6, '6'), (7, '7'), (8, '8'), (9, '9'), (10, '10')])),
                ('product', models.ForeignKey(to='booking.Product')),
            ],
            options={
                'ordering': ['subject__name'],
                'verbose_name': 'grundskolefagtilknytning',
                'verbose_name_plural': 'grundskolefagtilknytninger',
            },
        ),
        migrations.CreateModel(
            name='ProductGymnasieFag',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('display_value_cached', models.CharField(max_length=100, null=True)),
                ('level', models.ManyToManyField(to='booking.GymnasieLevel')),
                ('product', models.ForeignKey(to='booking.Product')),
            ],
            options={
                'ordering': ['subject__name'],
                'verbose_name': 'gymnasiefagtilknytning',
                'verbose_name_plural': 'gymnasiefagtilknytninger',
            },
        ),
        migrations.CreateModel(
            name='Region',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=16, verbose_name='Navn')),
                ('name_en', models.CharField(max_length=16, null=True, verbose_name='Engelsk navn')),
            ],
            options={
                'verbose_name': 'region',
                'verbose_name_plural': 'regioner',
            },
        ),
        migrations.CreateModel(
            name='Resource',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
            ],
            bases=(booking.mixins.AvailabilityUpdaterMixin, models.Model),
        ),
        migrations.CreateModel(
            name='ResourcePool',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=1024, verbose_name='Navn')),
                ('organizationalunit', models.ForeignKey(verbose_name='Ressourcens enhed', to='booking.OrganizationalUnit')),
            ],
            bases=(booking.mixins.AvailabilityUpdaterMixin, models.Model),
        ),
        migrations.CreateModel(
            name='ResourceRequirement',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('required_amount', models.IntegerField(verbose_name='P\xe5kr\xe6vet antal', validators=[django.core.validators.MinValueValidator(1)])),
                ('being_deleted', models.BooleanField(default=False)),
                ('product', models.ForeignKey(to='booking.Product')),
                ('resource_pool', models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, verbose_name='Ressourcegruppe', to='booking.ResourcePool', null=True)),
            ],
            bases=(booking.mixins.AvailabilityUpdaterMixin, models.Model),
        ),
        migrations.CreateModel(
            name='ResourceType',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=30)),
                ('plural', models.CharField(default=b'', max_length=30)),
            ],
        ),
        migrations.CreateModel(
            name='Room',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=64, verbose_name='Navn p\xe5 lokale')),
                ('locality', models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, verbose_name='Lokalitet', blank=True, to='booking.Locality', null=True)),
            ],
            options={
                'verbose_name': 'lokale',
                'verbose_name_plural': 'lokaler',
            },
        ),
        migrations.CreateModel(
            name='RoomResponsible',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=50)),
                ('email', models.EmailField(max_length=64, null=True, blank=True)),
                ('phone', models.CharField(max_length=14, null=True, blank=True)),
                ('organizationalunit', models.ForeignKey(blank=True, to='booking.OrganizationalUnit', null=True)),
            ],
            options={
                'verbose_name': 'Lokaleanvarlig',
                'verbose_name_plural': 'Lokaleanvarlige',
            },
        ),
        migrations.CreateModel(
            name='School',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=128)),
                ('address', models.CharField(max_length=128, null=True, verbose_name='Adresse')),
                ('cvr', models.IntegerField(null=True, verbose_name='CVR-nummer')),
                ('ean', models.BigIntegerField(null=True, verbose_name='EAN-nummer')),
                ('type', models.IntegerField(default=1, verbose_name='Uddannelsestype', choices=[(2, 'Folkeskole'), (1, 'Gymnasie')])),
                ('municipality', models.ForeignKey(to='booking.Municipality', null=True)),
                ('postcode', models.ForeignKey(to='booking.PostCode', null=True)),
            ],
            options={
                'ordering': ['name', 'postcode'],
                'verbose_name': 'uddannelsesinstitution',
                'verbose_name_plural': 'uddannelsesinstitutioner',
            },
        ),
        migrations.CreateModel(
            name='StudyMaterial',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('type', models.IntegerField(default=0, choices=[(0, 'URL'), (1, 'Vedh\xe6ftet fil')])),
                ('url', models.URLField(null=True, blank=True)),
                ('file', models.FileField(storage=booking.utils.CustomStorage(), null=True, upload_to=b'material', blank=True)),
                ('product', models.ForeignKey(to='booking.Product', null=True)),
            ],
            options={
                'verbose_name': 'undervisningsmateriale',
                'verbose_name_plural': 'undervisningsmaterialer',
            },
        ),
        migrations.CreateModel(
            name='Subject',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=256)),
                ('subject_type', models.IntegerField(default=1, verbose_name='Skoleniveau', choices=[(1, 'Gymnasie'), (2, 'Grundskole'), (3, 'B\xe5de gymnasie og grundskole')])),
                ('description', models.TextField(blank=True)),
            ],
            options={
                'ordering': ['name'],
                'verbose_name': 'fag',
                'verbose_name_plural': 'fag',
            },
        ),
        migrations.CreateModel(
            name='SurveyXactEvaluation',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('surveyId', models.IntegerField()),
                ('for_students', models.BooleanField(default=False)),
                ('for_teachers', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='SurveyXactEvaluationGuest',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('status', models.SmallIntegerField(default=1, verbose_name='status', choices=[(0, 'Modtager ikke evaluering'), (1, 'Ikke afholdt / ikke afsendt'), (2, 'Sendt f\xf8rste gang'), (3, 'Sendt anden gang'), (4, 'Har klikket p\xe5 link')])),
                ('shortlink_id', models.CharField(max_length=16)),
                ('evaluation', models.ForeignKey(blank=True, to='booking.SurveyXactEvaluation', null=True)),
                ('guest', models.ForeignKey(to='booking.Guest')),
            ],
        ),
        migrations.CreateModel(
            name='Tag',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=256)),
                ('description', models.TextField(blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='Topic',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=256)),
                ('description', models.TextField(blank=True)),
            ],
            options={
                'verbose_name': 'emne',
                'verbose_name_plural': 'emner',
            },
        ),
        migrations.CreateModel(
            name='Visit',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('deprecated_start_datetime', models.DateTimeField(null=True, verbose_name='Starttidspunkt', blank=True)),
                ('deprecated_end_datetime', models.DateTimeField(null=True, blank=True)),
                ('deprecated_bookable', models.BooleanField(default=False, verbose_name='Kan bookes')),
                ('desired_time', models.CharField(max_length=2000, null=True, verbose_name='\xd8nsket tidspunkt', blank=True)),
                ('override_duration', models.CharField(max_length=8, null=True, verbose_name='Varighed', blank=True)),
                ('override_needed_hosts', models.IntegerField(blank=True, null=True, verbose_name='Antal n\xf8dvendige v\xe6rter', choices=[(None, 'Brug v\xe6rdi fra tilbud'), (1, 1), (2, 2), (3, 3), (4, 4), (5, 5), (6, 6), (7, 7), (8, 8), (9, 9)])),
                ('override_needed_teachers', models.IntegerField(blank=True, null=True, verbose_name='Antal n\xf8dvendige undervisere', choices=[(None, 'Brug v\xe6rdi fra tilbud'), (1, 1), (2, 2), (3, 3), (4, 4), (5, 5), (6, 6), (7, 7), (8, 8), (9, 9)])),
                ('room_status', models.IntegerField(default=2, verbose_name='Status for tildeling af lokaler', choices=[(0, 'Tildeling af lokaler ikke p\xe5kr\xe6vet'), (2, 'Afventer tildeling/bekr\xe6ftelse'), (1, 'Tildelt/bekr\xe6ftet')])),
                ('workflow_status', models.IntegerField(default=0, choices=[(0, 'Under planl\xe6gning'), (1, 'Afvist af undervisere eller v\xe6rt'), (2, 'Planlagt (ressourcer tildelt)'), (9, 'Planlagt og lukket for booking'), (3, 'Bekr\xe6ftet af g\xe6st'), (4, 'P\xe5mindelse afsendt'), (5, 'Afviklet'), (6, 'Evalueret'), (7, 'Aflyst'), (8, 'Udeblevet'), (10, 'Automatisk tildeling fejlet')])),
                ('last_workflow_update', models.DateTimeField(default=django.utils.timezone.now)),
                ('needs_attention_since', models.DateTimeField(default=None, null=True, verbose_name='Behov for opm\xe6rksomhed siden', blank=True)),
                ('comments', models.TextField(default=b'', verbose_name='Interne kommentarer', blank=True)),
                ('search_index', booking.models.VectorField(default=b'', serialize=False, null=True, editable=False)),
                ('extra_search_text', models.TextField(default=b'', verbose_name='Tekst-v\xe6rdier til friteksts\xf8gning', editable=False, blank=True)),
                ('multi_priority', models.IntegerField(default=0)),
                ('is_multi_sub', models.BooleanField(default=False)),
            ],
            options={
                'ordering': ['id'],
                'verbose_name': 'bes\xf8g',
                'verbose_name_plural': 'bes\xf8g',
            },
            bases=(booking.mixins.AvailabilityUpdaterMixin, models.Model),
        ),
        migrations.CreateModel(
            name='VisitComment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('deleted_user_name', models.CharField(max_length=30)),
                ('text', models.CharField(max_length=500, verbose_name='Kommentartekst')),
                ('time', models.DateTimeField(auto_now=True, verbose_name='Tidsstempel')),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, null=True)),
            ],
            options={
                'ordering': ['-time'],
            },
        ),
        migrations.CreateModel(
            name='VisitResource',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
            ],
            bases=(booking.mixins.AvailabilityUpdaterMixin, models.Model),
        ),
        migrations.CreateModel(
            name='ClassBooking',
            fields=[
                ('booking_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='booking.Booking')),
                ('tour_desired', models.BooleanField(default=False, verbose_name='Rundvisning \xf8nsket')),
                ('catering_desired', models.BooleanField(default=False, verbose_name='Forplejning \xf8nsket')),
                ('presentation_desired', models.BooleanField(default=False, verbose_name='Opl\xe6g om uddannelse \xf8nsket')),
                ('custom_desired', models.BooleanField(default=False, verbose_name='Specialtilbud \xf8nsket')),
            ],
            options={
                'verbose_name': 'booking for klassebes\xf8g',
                'verbose_name_plural': 'bookinger for klassebes\xf8g',
            },
            bases=('booking.booking',),
        ),
        migrations.CreateModel(
            name='CustomResource',
            fields=[
                ('resource_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='booking.Resource')),
                ('name', models.CharField(max_length=1024, verbose_name='Navn')),
            ],
            options={
                'abstract': False,
            },
            bases=('booking.resource',),
        ),
        migrations.CreateModel(
            name='HostResource',
            fields=[
                ('resource_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='booking.Resource')),
                ('user', models.ForeignKey(verbose_name='Underviser', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
            bases=('booking.resource',),
        ),
        migrations.CreateModel(
            name='ItemResource',
            fields=[
                ('resource_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='booking.Resource')),
                ('name', models.CharField(max_length=1024, verbose_name='Navn')),
            ],
            options={
                'abstract': False,
            },
            bases=('booking.resource',),
        ),
        migrations.CreateModel(
            name='MultiProductVisit',
            fields=[
                ('visit_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='booking.Visit')),
                ('date', models.DateField(null=True, verbose_name='Dato')),
                ('required_visits', models.PositiveIntegerField(default=2, verbose_name='Antal \xf8nskede bes\xf8g')),
                ('responsible', models.ForeignKey(verbose_name='Bes\xf8gsansvarlig', blank=True, to=settings.AUTH_USER_MODEL, null=True)),
            ],
            bases=('booking.visit',),
        ),
        migrations.CreateModel(
            name='ProductAutosend',
            fields=[
                ('autosend_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='booking.Autosend')),
            ],
            bases=('booking.autosend',),
        ),
        migrations.CreateModel(
            name='RoomResource',
            fields=[
                ('resource_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='booking.Resource')),
                ('room', models.ForeignKey(verbose_name='Lokale', to='booking.Room')),
            ],
            bases=('booking.resource',),
        ),
        migrations.CreateModel(
            name='TeacherBooking',
            fields=[
                ('booking_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='booking.Booking')),
                ('subjects', models.ManyToManyField(to='booking.Subject')),
            ],
            options={
                'verbose_name': 'booking for tilbud til undervisere',
                'verbose_name_plural': 'bookinger for tilbud til undervisere',
            },
            bases=('booking.booking',),
        ),
        migrations.CreateModel(
            name='TeacherResource',
            fields=[
                ('resource_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='booking.Resource')),
                ('user', models.ForeignKey(verbose_name='Underviser', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
            bases=('booking.resource',),
        ),
        migrations.CreateModel(
            name='VehicleResource',
            fields=[
                ('resource_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='booking.Resource')),
                ('name', models.CharField(max_length=1024, verbose_name='Navn')),
            ],
            options={
                'abstract': False,
            },
            bases=('booking.resource',),
        ),
        migrations.CreateModel(
            name='VisitAutosend',
            fields=[
                ('autosend_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='booking.Autosend')),
                ('inherit', models.BooleanField(verbose_name='Genbrug indstilling fra tilbud')),
            ],
            bases=('booking.autosend',),
        ),
        migrations.AddField(
            model_name='visitresource',
            name='resource',
            field=models.ForeignKey(related_name='visitresource', verbose_name='Ressource', to='booking.Resource'),
        ),
        migrations.AddField(
            model_name='visitresource',
            name='resource_requirement',
            field=models.ForeignKey(related_name='visitresource', verbose_name='Ressourcebehov', to='booking.ResourceRequirement'),
        ),
        migrations.AddField(
            model_name='visitresource',
            name='visit',
            field=models.ForeignKey(related_name='visitresource', verbose_name='Bes\xf8g', to='booking.Visit'),
        ),
        migrations.AddField(
            model_name='visitcomment',
            name='visit',
            field=models.ForeignKey(verbose_name='Bes\xf8g', to='booking.Visit'),
        ),
        migrations.AddField(
            model_name='visit',
            name='cancelled_eventtime',
            field=models.ForeignKey(related_name='cancelled_visits', default=None, blank=True, to='booking.EventTime', null=True, verbose_name='Tidspunkt for aflyst bes\xf8g'),
        ),
        migrations.AddField(
            model_name='visit',
            name='deprecated_product',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, blank=True, to='booking.Product', null=True),
        ),
        migrations.AddField(
            model_name='visit',
            name='hosts',
            field=models.ManyToManyField(related_name='hosted_visits', verbose_name='Tilknyttede v\xe6rter', to=settings.AUTH_USER_MODEL, blank=True),
        ),
        migrations.AddField(
            model_name='visit',
            name='hosts_rejected',
            field=models.ManyToManyField(related_name='rejected_hosted_visits', verbose_name='V\xe6rter, som har afsl\xe5et', to=settings.AUTH_USER_MODEL, blank=True),
        ),
        migrations.AddField(
            model_name='visit',
            name='override_locality',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, verbose_name='Lokalitet', blank=True, to='booking.Locality', null=True),
        ),
        migrations.AddField(
            model_name='visit',
            name='resources',
            field=models.ManyToManyField(to='booking.Resource', verbose_name='Bes\xf8gets ressourcer', through='booking.VisitResource', blank=True),
        ),
        migrations.AddField(
            model_name='visit',
            name='rooms',
            field=models.ManyToManyField(to='booking.Room', verbose_name='Lokaler', blank=True),
        ),
        migrations.AddField(
            model_name='visit',
            name='statistics',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, to='booking.ObjectStatistics', null=True),
        ),
        migrations.AddField(
            model_name='visit',
            name='teachers',
            field=models.ManyToManyField(related_name='taught_visits', verbose_name='Tilknyttede undervisere', to=settings.AUTH_USER_MODEL, blank=True),
        ),
        migrations.AddField(
            model_name='visit',
            name='teachers_rejected',
            field=models.ManyToManyField(related_name='rejected_taught_visits', verbose_name='Undervisere, som har afsl\xe5et', to=settings.AUTH_USER_MODEL, blank=True),
        ),
        migrations.AddField(
            model_name='surveyxactevaluation',
            name='guests',
            field=models.ManyToManyField(to='booking.Guest', through='booking.SurveyXactEvaluationGuest'),
        ),
        migrations.AddField(
            model_name='surveyxactevaluation',
            name='product',
            field=models.ForeignKey(to='booking.Product', null=True),
        ),
        migrations.AddField(
            model_name='resourcepool',
            name='resource_type',
            field=models.ForeignKey(to='booking.ResourceType'),
        ),
        migrations.AddField(
            model_name='resourcepool',
            name='resources',
            field=models.ManyToManyField(to='booking.Resource', verbose_name='Ressourcer', blank=True),
        ),
        migrations.AddField(
            model_name='resource',
            name='calendar',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.SET_NULL, blank=True, to='booking.Calendar', verbose_name='Ressourcens kalender'),
        ),
        migrations.AddField(
            model_name='resource',
            name='organizationalunit',
            field=models.ForeignKey(verbose_name='Ressourcens enhed', to='booking.OrganizationalUnit'),
        ),
        migrations.AddField(
            model_name='resource',
            name='resource_type',
            field=models.ForeignKey(verbose_name='Type', to='booking.ResourceType'),
        ),
        migrations.AddField(
            model_name='productgymnasiefag',
            name='subject',
            field=models.ForeignKey(to='booking.Subject'),
        ),
        migrations.AddField(
            model_name='productgrundskolefag',
            name='subject',
            field=models.ForeignKey(to='booking.Subject'),
        ),
        migrations.AddField(
            model_name='product',
            name='grundskolefag',
            field=models.ManyToManyField(related_name='grundskole_resources', verbose_name='Grundskolefag', to='booking.Subject', through='booking.ProductGrundskoleFag', blank=True),
        ),
        migrations.AddField(
            model_name='product',
            name='gymnasiefag',
            field=models.ManyToManyField(related_name='gymnasie_resources', verbose_name='Gymnasiefag', to='booking.Subject', through='booking.ProductGymnasieFag', blank=True),
        ),
        migrations.AddField(
            model_name='product',
            name='links',
            field=models.ManyToManyField(to='booking.Link', verbose_name='Links', blank=True),
        ),
        migrations.AddField(
            model_name='product',
            name='locality',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, verbose_name='Lokalitet', blank=True, to='booking.Locality', null=True),
        ),
        migrations.AddField(
            model_name='product',
            name='organizationalunit',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, verbose_name='Enhed', to='booking.OrganizationalUnit', null=True),
        ),
        migrations.AddField(
            model_name='product',
            name='potentielle_undervisere',
            field=models.ManyToManyField(related_name='potentiel_underviser_for_set', verbose_name='Potentielle undervisere', to=settings.AUTH_USER_MODEL, blank=True),
        ),
        migrations.AddField(
            model_name='product',
            name='potentielle_vaerter',
            field=models.ManyToManyField(related_name='potentiel_vaert_for_set', verbose_name='Potentielle v\xe6rter', to=settings.AUTH_USER_MODEL, blank=True),
        ),
        migrations.AddField(
            model_name='product',
            name='roomresponsible',
            field=models.ManyToManyField(related_name='ansvarlig_for_besoeg_set', verbose_name='Lokaleansvarlige', to='booking.RoomResponsible', blank=True),
        ),
        migrations.AddField(
            model_name='product',
            name='rooms',
            field=models.ManyToManyField(to='booking.Room', verbose_name='Lokaler', blank=True),
        ),
        migrations.AddField(
            model_name='product',
            name='statistics',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, to='booking.ObjectStatistics', null=True),
        ),
        migrations.AddField(
            model_name='product',
            name='tags',
            field=models.ManyToManyField(to='booking.Tag', verbose_name='Tags', blank=True),
        ),
        migrations.AddField(
            model_name='product',
            name='tilbudsansvarlig',
            field=models.ForeignKey(related_name='tilbudsansvarlig_for_set', on_delete=django.db.models.deletion.SET_NULL, verbose_name='Koordinator', blank=True, to=settings.AUTH_USER_MODEL, null=True),
        ),
        migrations.AddField(
            model_name='product',
            name='topics',
            field=models.ManyToManyField(to='booking.Topic', verbose_name='Emner', blank=True),
        ),
        migrations.AddField(
            model_name='postcode',
            name='region',
            field=models.ForeignKey(to='booking.Region'),
        ),
        migrations.AddField(
            model_name='organizationalunit',
            name='type',
            field=models.ForeignKey(to='booking.OrganizationalUnitType'),
        ),
        migrations.AddField(
            model_name='municipality',
            name='region',
            field=models.ForeignKey(verbose_name='Region', to='booking.Region'),
        ),
        migrations.AddField(
            model_name='multiproductvisittempproduct',
            name='product',
            field=models.ForeignKey(related_name='prod', to='booking.Product'),
        ),
        migrations.AddField(
            model_name='multiproductvisittemp',
            name='baseproduct',
            field=models.ForeignKey(related_name='foobar', blank=True, to='booking.Product', null=True),
        ),
        migrations.AddField(
            model_name='multiproductvisittemp',
            name='products',
            field=models.ManyToManyField(related_name='products', through='booking.MultiProductVisitTempProduct', to='booking.Product', blank=True),
        ),
        migrations.AddField(
            model_name='locality',
            name='organizationalunit',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, verbose_name='Enhed', blank=True, to='booking.OrganizationalUnit', null=True),
        ),
        migrations.AddField(
            model_name='guest',
            name='school',
            field=models.ForeignKey(verbose_name='Skole', to='booking.School', null=True),
        ),
        migrations.AddField(
            model_name='eventtime',
            name='product',
            field=models.ForeignKey(to='booking.Product', null=True),
        ),
        migrations.AddField(
            model_name='eventtime',
            name='visit',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.SET_NULL, blank=True, to='booking.Visit'),
        ),
        migrations.AddField(
            model_name='emailtemplate',
            name='organizationalunit',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, verbose_name='Enhed', blank=True, to='booking.OrganizationalUnit', null=True),
        ),
        migrations.AddField(
            model_name='emailtemplate',
            name='type',
            field=models.ForeignKey(to='booking.EmailTemplateType', null=True),
        ),
        migrations.AddField(
            model_name='bookinggymnasiesubjectlevel',
            name='booking',
            field=models.ForeignKey(to='booking.Booking'),
        ),
        migrations.AddField(
            model_name='bookinggymnasiesubjectlevel',
            name='level',
            field=models.ForeignKey(to='booking.GymnasieLevel'),
        ),
        migrations.AddField(
            model_name='bookinggymnasiesubjectlevel',
            name='subject',
            field=models.ForeignKey(to='booking.Subject'),
        ),
        migrations.AddField(
            model_name='bookinggrundskolesubjectlevel',
            name='booking',
            field=models.ForeignKey(to='booking.Booking'),
        ),
        migrations.AddField(
            model_name='bookinggrundskolesubjectlevel',
            name='level',
            field=models.ForeignKey(to='booking.GrundskoleLevel'),
        ),
        migrations.AddField(
            model_name='bookinggrundskolesubjectlevel',
            name='subject',
            field=models.ForeignKey(to='booking.Subject'),
        ),
        migrations.AddField(
            model_name='booking',
            name='booker',
            field=models.OneToOneField(to='booking.Guest'),
        ),
        migrations.AddField(
            model_name='booking',
            name='statistics',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, to='booking.ObjectStatistics', null=True),
        ),
        migrations.AddField(
            model_name='booking',
            name='visit',
            field=models.ForeignKey(related_name='bookings', verbose_name='Bes\xf8g', blank=True, to='booking.Visit', null=True),
        ),
        migrations.AddField(
            model_name='bookerresponsenonce',
            name='booker',
            field=models.ForeignKey(to='booking.Guest'),
        ),
        migrations.AddField(
            model_name='autosend',
            name='template_type',
            field=models.ForeignKey(to='booking.EmailTemplateType', null=True),
        ),
        migrations.AddField(
            model_name='visitautosend',
            name='visit',
            field=models.ForeignKey(verbose_name='Bes\xf8gForekomst', to='booking.Visit'),
        ),
        migrations.AddField(
            model_name='visit',
            name='multi_master',
            field=models.ForeignKey(related_name='subvisit', on_delete=django.db.models.deletion.SET_NULL, blank=True, to='booking.MultiProductVisit', null=True),
        ),
        migrations.AddField(
            model_name='vehicleresource',
            name='locality',
            field=models.ForeignKey(verbose_name='Lokalitet', blank=True, to='booking.Locality', null=True),
        ),
        migrations.AddField(
            model_name='productautosend',
            name='product',
            field=models.ForeignKey(verbose_name='Bes\xf8g', to='booking.Product'),
        ),
        migrations.AddField(
            model_name='itemresource',
            name='locality',
            field=models.ForeignKey(verbose_name='Lokalitet', blank=True, to='booking.Locality', null=True),
        ),
        migrations.AlterIndexTogether(
            name='calendarcalculatedavailable',
            index_together=set([('end', 'start'), ('start', 'end')]),
        ),
    ]
