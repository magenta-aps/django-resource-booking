from booking.data.default_email_templates import import_all
from booking.models import School, GymnasieLevel, GrundskoleLevel, Region, \
    Locality, Municipality, PostCode, KUEmailMessage, Guide, \
    ExercisePresentation, EmailTemplateType

def setup_defaults(overwrite_templates=False):
    EmailTemplateType.set_defaults()
    Region.create_defaults()
    Locality.create_defaults()
    Municipality.create_defaults()
    PostCode.create_defaults()
    School.create_defaults()
    GymnasieLevel.create_defaults()
    GrundskoleLevel.create_defaults()
    KUEmailMessage.migrate()
    Guide.create_defaults()
    ExercisePresentation.create_defaults()
    if overwrite_templates:
        import_all()
