# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    def populate_units(apps, schema_editor):
        from booking.models import Unit as unit, UnitType as unittype
        # unit = apps.get_model("booking", "Unit")
        # unittype = apps.get_model("booking", "UnitType")

        fakultet = unittype(name=u"Fakultet")
        fakultet.save()
        institut = unittype(name=u"Institut")
        institut.save()

        fakultet_humaniora = unit(name="Det Humanistiske Fakultet", type=fakultet)
        fakultet_humaniora.save()
        fakultet_jura = unit(name="Det Juridiske Fakultet", type=fakultet)
        fakultet_jura.save()
        fakultet_naturvidenskab = unit(name="Det Natur- og Biovidenskabelige Fakultet", type=fakultet)
        fakultet_naturvidenskab.save()
        fakultet_samfund = unit(name="Det Samfundsvidenskabelige Fakultet", type=fakultet)
        fakultet_samfund.save()
        fakultet_sundhed = unit(name="Det Sundhedsvidenskabelige Fakultet", type=fakultet)
        fakultet_sundhed.save()
        fakultet_teologi = unit(name="Det Teologiske Fakultet", type=fakultet)
        fakultet_teologi.save()

        db_alias = schema_editor.connection.alias
        unit.objects.using(db_alias).bulk_create([

            # Oh the humanities
            unit(name=u"Institut for Engelsk, Germansk og Romansk", parent=fakultet_humaniora, type=institut),
            unit(name=u"Institut for Kunst- og Kulturvidenskab", parent=fakultet_humaniora, type=institut),
            unit(name=u"Institut for Medier, Erkendelse og Formidling", parent=fakultet_humaniora, type=institut),
            unit(name=u"Institut for Nordiske Studier og Sprogvidenskab", parent=fakultet_humaniora, type=institut),
            unit(name=u"Institut for Tværkulturelle og Regionale Studier", parent=fakultet_humaniora, type=institut),
            unit(name=u"Nordisk Forskningsinstitut", parent=fakultet_humaniora, type=institut),
            unit(name=u"SAXO-Instituttet", parent=fakultet_humaniora, type=institut),

            # Det juridiske fakultet er et enhedsfakultet uden institutter

            # Naturvidenskab - where the real work is done
            unit(name=u"Biologisk Institut", parent=fakultet_naturvidenskab, type=institut),
            unit(name=u"Cirkus Naturligvis", parent=fakultet_naturvidenskab, type=institut),
            unit(name=u"Datalogisk Institut", parent=fakultet_naturvidenskab, type=institut),
            unit(name=u"Det Natur- og Biovidenskabelige Fakultets Skoletjeneste", parent=fakultet_naturvidenskab, type=institut),
            unit(name=u"Institut for Idræt og Ernæring", parent=fakultet_naturvidenskab, type=institut),
            unit(name=u"Institut for Geovidenskab og Naturforvaltning", parent=fakultet_naturvidenskab, type=institut),
            unit(name=u"Institut for Fødevarevidenskab", parent=fakultet_naturvidenskab, type=institut),
            unit(name=u"Institut for Matematiske Fag", parent=fakultet_naturvidenskab, type=institut),
            unit(name=u"Institut for Naturfagenes Didaktik", parent=fakultet_naturvidenskab, type=institut),
            unit(name=u"Institut for Plante- og Miljøvidenskab", parent=fakultet_naturvidenskab, type=institut),
            unit(name=u"Institut for Fødevare- og Ressourceøkonomi", parent=fakultet_naturvidenskab, type=institut),
            unit(name=u"Kemisk Institut", parent=fakultet_naturvidenskab, type=institut),
            unit(name=u"Niels Bohr Institutet", parent=fakultet_naturvidenskab, type=institut),
            unit(name=u"Statens Naturhistoriske Museum", parent=fakultet_naturvidenskab, type=institut),
            unit(name=u"Statens Naturhistoriske Museums Skoletjeneste", parent=fakultet_naturvidenskab, type=institut),

            # Samfundsvidenskab - holder hjulene i gang
            unit(name=u"Institut for Antropologi", parent=fakultet_samfund, type=institut),
            unit(name=u"Institut for Psykologi", parent=fakultet_samfund, type=institut),
            unit(name=u"Institut for Statskundskab", parent=fakultet_samfund, type=institut),
            unit(name=u"Sociologisk Institut", parent=fakultet_samfund, type=institut),
            unit(name=u"Økonomisk Institut", parent=fakultet_samfund, type=institut),

            # Sundhedsvidenskab - så vi ikke pludselig dør
            unit(name=u"Biomedicinsk Institut", parent=fakultet_sundhed, type=institut),
            unit(name=u"Institut for Cellulær og Molekylær Medicin", parent=fakultet_sundhed, type=institut),
            unit(name=u"Institut for Farmaci", parent=fakultet_sundhed, type=institut),
            unit(name=u"Institut for Folkesundhedsvidenskab", parent=fakultet_sundhed, type=institut),
            unit(name=u"Institut for Immunologi og Mikrobiologi", parent=fakultet_sundhed, type=institut),
            unit(name=u"Institut for Klinisk Medicin", parent=fakultet_sundhed, type=institut),
            unit(name=u"Institut for Klinisk Veterinær- og Husdyrvidenskab", parent=fakultet_sundhed, type=institut),
            unit(name=u"Institut for Lægemiddeldesign og Farmakologi", parent=fakultet_sundhed, type=institut),
            unit(name=u"Institut for Neurovidenskab og Farmakologi", parent=fakultet_sundhed, type=institut),
            unit(name=u"Odontologisk Institut", parent=fakultet_sundhed, type=institut),
            unit(name=u"Institut for Produktionsdyr og Heste", parent=fakultet_sundhed, type=institut),
            unit(name=u"Retsmedicinsk Institut", parent=fakultet_sundhed, type=institut),
            unit(name=u"Institut for Veterinær Sygdomsbiologi", parent=fakultet_sundhed, type=institut),
            unit(name=u"Skolen for Klinikassistenter og Tandplejere", parent=fakultet_sundhed, type=institut),

            # Det teologiske fakultet er et enhedsfakultet uden institutter
        ])

    dependencies = [("booking", "0001_initial")]

    operations = [
        migrations.RunPython(populate_units),
    ]
