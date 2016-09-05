# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import recurrence.fields
import django.db.models.deletion
from django.conf import settings
import djorm_pgfulltext.fields


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('booking', '0092_auto_20160905_1138'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProductGrundskoleFag',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('class_level_min', models.IntegerField(default=0, verbose_name='Klassetrin fra', choices=[(0, '0'), (1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5'), (6, '6'), (7, '7'), (8, '8'), (9, '9'), (10, '10')])),
                ('class_level_max', models.IntegerField(default=10, verbose_name='Klassetrin til', choices=[(0, '0'), (1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5'), (6, '6'), (7, '7'), (8, '8'), (9, '9'), (10, '10')])),
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
                ('level', models.ManyToManyField(to='booking.GymnasieLevel')),
            ],
            options={
                'ordering': ['subject__name'],
                'verbose_name': 'gymnasiefagtilknytning',
                'verbose_name_plural': 'gymnasiefagtilknytninger',
            },
        ),
        # Add new fields to product
        migrations.AddField(
            model_name='product',
            name='audience',
            field=models.IntegerField(default=None, null=True, verbose_name='M\xe5lgruppe', choices=[(None, b'---------'), (1, 'L\xe6rer'), (2, 'Elev'), (3, 'Alle')]),
        ),
        migrations.AddField(
            model_name='product',
            name='comment',
            field=models.TextField(verbose_name='Kommentar', blank=True),
        ),
        migrations.AddField(
            model_name='product',
            name='created_by',
            field=models.ForeignKey(related_name='created_visits_set', on_delete=django.db.models.deletion.SET_NULL, verbose_name='Oprettet af', blank=True, to=settings.AUTH_USER_MODEL, null=True),
        ),
        migrations.AddField(
            model_name='product',
            name='description',
            field=models.TextField(default='', verbose_name='Beskrivelse'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='product',
            name='extra_search_text',
            field=models.TextField(default=b'', verbose_name='Tekst-v\xe6rdier til friteksts\xf8gning', editable=False, blank=True),
        ),
        migrations.RenameField(
            model_name='product',
            old_name='resource_ptr',
            new_name='id',
        ),
        migrations.AlterField(
            model_name='product',
            name='id',
            field=models.AutoField(auto_created=True, primary_key=True, default=None, serialize=False, verbose_name='ID'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='product',
            name='institution_level',
            field=models.IntegerField(default=1, verbose_name='Institution', choices=[(1, 'Gymnasie'), (2, 'Grundskole'), (3, 'Begge')]),
        ),
        migrations.AddField(
            model_name='product',
            name='links',
            field=models.ManyToManyField(to='booking.Link', verbose_name='Links', blank=True),
        ),
        migrations.AddField(
            model_name='product',
            name='locality',
            field=models.ForeignKey(verbose_name='Lokalitet', blank=True, to='booking.Locality', null=True),
        ),
        migrations.AddField(
            model_name='product',
            name='mouseover_description',
            field=models.CharField(max_length=512, verbose_name='Mouseover-tekst', blank=True),
        ),
        migrations.AddField(
            model_name='product',
            name='organizationalunit',
            field=models.ForeignKey(verbose_name='Enhed', to='booking.OrganizationalUnit', null=True),
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
            name='preparation_time',
            field=models.CharField(max_length=200, null=True, verbose_name='Forberedelsestid', blank=True),
        ),
        migrations.AddField(
            model_name='product',
            name='price',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10, blank=True, null=True, verbose_name='Pris'),
        ),
        migrations.AddField(
            model_name='product',
            name='recurrences',
            field=recurrence.fields.RecurrenceField(null=True, verbose_name='Gentagelser', blank=True),
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
            name='search_index',
            field=djorm_pgfulltext.fields.VectorField(default=b'', serialize=False, null=True, editable=False, db_index=True),
        ),
        migrations.AddField(
            model_name='product',
            name='state',
            field=models.IntegerField(default=0, verbose_name='Status', choices=[(None, b'---------'), (0, 'Under udarbejdelse'), (1, 'Offentlig'), (2, 'Skjult')]),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='product',
            name='statistics',
            field=models.ForeignKey(to='booking.ObjectStatistics', null=True),
        ),
        migrations.AddField(
            model_name='product',
            name='tags',
            field=models.ManyToManyField(to='booking.Tag', verbose_name='Tags', blank=True),
        ),
        migrations.AddField(
            model_name='product',
            name='teaser',
            field=models.TextField(default='', max_length=210, verbose_name='Teaser'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='product',
            name='tilbudsansvarlig',
            field=models.ForeignKey(related_name='tilbudsansvarlig_for_set', verbose_name='Tilbudsansvarlig', blank=True, to=settings.AUTH_USER_MODEL, null=True),
        ),
        migrations.AddField(
            model_name='product',
            name='title',
            field=models.CharField(default='', max_length=60, verbose_name='Titel'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='product',
            name='topics',
            field=models.ManyToManyField(to='booking.Topic', verbose_name='Emner', blank=True),
        ),
        migrations.AddField(
            model_name='product',
            name='type',
            field=models.IntegerField(default=5, choices=[(0, 'Studerende for en dag'), (9, 'Studiepraktik'), (7, '\xc5bent hus'), (6, 'L\xe6rerarrangement'), (1, 'Bes\xf8g med klassen'), (3, 'Studieretningsprojekt'), (8, 'Lektiehj\xe6lp'), (4, 'Andre tilbud'), (5, 'Undervisningsmateriale')]),
        ),
        migrations.AddField(
            model_name='studymaterial',
            name='product',
            field=models.ForeignKey(to='booking.Product', null=True),
        ),
        migrations.AddField(
            model_name='productgymnasiefag',
            name='product',
            field=models.ForeignKey(to='booking.Product'),
        ),
        migrations.AddField(
            model_name='productgymnasiefag',
            name='subject',
            field=models.ForeignKey(to='booking.Subject'),
        ),
        migrations.AddField(
            model_name='productgrundskolefag',
            name='product',
            field=models.ForeignKey(to='booking.Product'),
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
        # Copy simple fields from resources to product
        migrations.RunSQL(
            """
                UPDATE
                    booking_product
                SET
                    "audience" = "r_src"."audience",
                    "comment" = "r_src"."comment",
                    "created_by_id" = "r_src"."created_by_id",
                    "description" = "r_src"."description",
                    "extra_search_text" = "r_src"."extra_search_text",
                    "institution_level" = "r_src"."institution_level",
                    "locality_id" = "r_src"."locality_id",
                    "mouseover_description" = "r_src"."mouseover_description",
                    "organizationalunit_id" = "r_src"."organizationalunit_id",
                    "preparation_time" = "r_src"."preparation_time",
                    "price" = "r_src"."price",
                    "recurrences" = "r_src"."recurrences",
                    "state" = "r_src"."state",
                    "statistics_id" = "r_src"."statistics_id",
                    "teaser" = "r_src"."teaser",
                    "tilbudsansvarlig_id" = "r_src"."tilbudsansvarlig_id",
                    "title" = "r_src"."title",
                    "type" = "r_src"."type"
                FROM
                    booking_product p_src
                    join booking_resource r_src on (
                        p_src.id = r_src.id
                    )
                WHERE
                    booking_product.id = r_src.id
                ;
            """
        ),
        # Remove simple fields from resource
        migrations.RemoveField(
            model_name='resource',
            name='audience',
        ),
        migrations.RemoveField(
            model_name='resource',
            name='comment',
        ),
        migrations.RemoveField(
            model_name='resource',
            name='created_by',
        ),
        migrations.RemoveField(
            model_name='resource',
            name='description',
        ),
        migrations.RemoveField(
            model_name='resource',
            name='extra_search_text',
        ),
        migrations.RemoveField(
            model_name='resource',
            name='institution_level',
        ),
        migrations.RemoveField(
            model_name='resource',
            name='locality',
        ),
        migrations.RemoveField(
            model_name='resource',
            name='mouseover_description',
        ),
        migrations.RemoveField(
            model_name='resource',
            name='organizationalunit',
        ),
        migrations.RemoveField(
            model_name='resource',
            name='preparation_time',
        ),
        migrations.RemoveField(
            model_name='resource',
            name='price',
        ),
        migrations.RemoveField(
            model_name='resource',
            name='recurrences',
        ),
        migrations.RemoveField(
            model_name='resource',
            name='search_index',
        ),
        migrations.RemoveField(
            model_name='resource',
            name='state',
        ),
        migrations.RemoveField(
            model_name='resource',
            name='statistics',
        ),
        migrations.RemoveField(
            model_name='resource',
            name='teaser',
        ),
        migrations.RemoveField(
            model_name='resource',
            name='tilbudsansvarlig',
        ),
        migrations.RemoveField(
            model_name='resource',
            name='title',
        ),
        migrations.RemoveField(
            model_name='resource',
            name='type',
        ),

        # Remove no-longer-needed field from room
        migrations.RemoveField(
            model_name='room',
            name='product',
        ),

        # Migrate ManyToMany relations for Resource => Product
        migrations.RunSQL(
            """
                INSERT INTO
                    "booking_productgrundskolefag"
                    (
                        "id",
                        "class_level_min",
                        "class_level_max",
                        "product_id",
                        "subject_id"
                    )
                SELECT
                    "id",
                    "class_level_min",
                    "class_level_max",
                    "resource_id",
                    "subject_id"
                FROM booking_resourcegrundskolefag;
            """
        ),
        migrations.RemoveField(
            model_name='resourcegrundskolefag',
            name='resource',
        ),
        migrations.RemoveField(
            model_name='resourcegrundskolefag',
            name='subject',
        ),
        migrations.RemoveField(
            model_name='resource',
            name='grundskolefag',
        ),


        migrations.RunSQL(
            """
                INSERT INTO
                    "booking_productgymnasiefag"
                    ("id", "product_id", "subject_id")
                SELECT
                    "id", "resource_id", "subject_id"
                FROM booking_resourcegymnasiefag;
            """
        ),
        migrations.RunSQL(
            """
                INSERT INTO
                    "booking_productgymnasiefag_level"
                    ("id", "productgymnasiefag_id", "gymnasielevel_id")
                SELECT
                    "id", "resourcegymnasiefag_id", "gymnasielevel_id"
                FROM booking_resourcegymnasiefag_level;
            """
        ),
        migrations.RemoveField(
            model_name='resourcegymnasiefag',
            name='level',
        ),
        migrations.RemoveField(
            model_name='resourcegymnasiefag',
            name='resource',
        ),
        migrations.RemoveField(
            model_name='resourcegymnasiefag',
            name='subject',
        ),
        migrations.RemoveField(
            model_name='resource',
            name='gymnasiefag',
        ),

        migrations.RunSQL(
            """
                INSERT INTO
                    "booking_product_links"
                    ("id", "product_id", "link_id")
                SELECT
                    "id", "resource_id", "link_id"
                FROM booking_resource_links;
            """
        ),
        migrations.RemoveField(
            model_name='resource',
            name='links',
        ),

        migrations.RunSQL(
            """
                INSERT INTO
                    "booking_product_potentielle_undervisere"
                    ("id", "product_id", "user_id")
                SELECT
                    "id", "resource_id", "user_id"
                FROM booking_resource_potentielle_undervisere;
            """
        ),
        migrations.RemoveField(
            model_name='resource',
            name='potentielle_undervisere',
        ),

        migrations.RunSQL(
            """
                INSERT INTO
                    "booking_product_potentielle_vaerter"
                    ("id", "product_id", "user_id")
                SELECT
                    "id", "resource_id", "user_id"
                FROM booking_resource_potentielle_vaerter;
            """
        ),
        migrations.RemoveField(
            model_name='resource',
            name='potentielle_vaerter',
        ),

        migrations.RunSQL(
            """
                INSERT INTO
                    "booking_product_roomresponsible"
                    ("id", "product_id", "roomresponsible_id")
                SELECT
                    "id", "resource_id", "roomresponsible_id"
                FROM booking_resource_roomresponsible;
            """
        ),
        migrations.RemoveField(
            model_name='resource',
            name='roomresponsible',
        ),

        migrations.RunSQL(
            """
                INSERT INTO
                    "booking_product_rooms"
                    ("id", "product_id", "room_id")
                SELECT
                    "id", "resource_id", "room_id"
                FROM booking_resource_rooms;
            """
        ),
        migrations.RemoveField(
            model_name='resource',
            name='rooms',
        ),

        migrations.RunSQL(
            """
                INSERT INTO
                    "booking_product_tags"
                    ("id", "product_id", "tag_id")
                SELECT
                    "id", "resource_id", "tag_id"
                FROM booking_resource_tags;
            """
        ),
        migrations.RemoveField(
            model_name='resource',
            name='tags',
        ),

        migrations.RunSQL(
            """
                INSERT INTO
                    "booking_product_topics"
                    ("id", "product_id", "topic_id")
                SELECT
                    "id", "resource_id", "topic_id"
                FROM booking_resource_topics;
            """
        ),
        migrations.RemoveField(
            model_name='resource',
            name='topics',
        ),

        # Fix foreign references to resource
        migrations.RunSQL(
            """
                UPDATE
                    booking_studymaterial
                SET
                    product_id = resource_id;
            """
        ),
        migrations.RemoveField(
            model_name='studymaterial',
            name='resource',
        ),

        migrations.DeleteModel(
            name='ResourceGrundskoleFag',
        ),
        migrations.DeleteModel(
            name='ResourceGymnasieFag',
        ),

    ]
