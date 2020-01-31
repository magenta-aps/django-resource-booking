from django.db.models.signals import post_save, post_delete, pre_delete
from django.dispatch import receiver

from booking.models import Guest, VisitResource, ResourceRequirement
from booking.models import Booking, ClassBooking, TeacherBooking
from booking.models import Product
from booking.models import Visit

MODELS_WITH_SEARCHVECTOR = set([Product, Visit])

BOOKING_MODELS = set([Booking, ClassBooking, TeacherBooking])


def run_searchvector_for_object(obj):
    model_type = type(obj)

    if model_type in MODELS_WITH_SEARCHVECTOR:
        # Disconnect signal to avoid recursion
        post_save.disconnect(update_search_vectors, sender=model_type)
        # Run the indexing
        obj.update_searchvector()
        # Re-enable signal
        post_save.connect(update_search_vectors, sender=model_type)


def update_search_vectors(sender, instance, **kwargs):
    run_searchvector_for_object(instance)


for model in MODELS_WITH_SEARCHVECTOR:
    post_save.connect(update_search_vectors, sender=model)


def on_booking_save(sender, instance, **kwargs):
    vo = getattr(instance, "visit", None)
    if vo:
        run_searchvector_for_object(vo)


for model in BOOKING_MODELS:
    post_save.connect(on_booking_save, sender=model)


def on_booker_save(sender, instance, **kwargs):
    vo = getattr(instance, "visit", None)
    if vo:
        run_searchvector_for_object(vo)


post_save.connect(on_booker_save, sender=Guest)


@receiver(pre_delete, sender=ResourceRequirement)
def before_requirement_delete(sender, instance, using, **kwargs):
    instance.being_deleted = True
    instance.save()


@receiver(post_delete, sender=VisitResource)
def on_visitresource_delete(sender, instance, using, **kwargs):
    if instance.visit is not None:
        instance.visit.autoassign_resources()
