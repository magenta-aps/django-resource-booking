# from django.db.models import Q
# from django.db.models.signals import post_save, post_delete
# from django.db.models.signals import m2m_changed
#
# from booking.models import Visit
# from booking.resource_based.models import Calendar
# from booking.resource_based.models import EventTime
# from booking.resource_based.models import Resource
# from booking.resource_based.models import ResourcePool
# from booking.resource_based.models import ResourceRequirement
#
#
# # When a calendar is created it affects the availability of any resource it
# # belongs to. Any currently available eventtime that might use that resource
# # will have recalculate availability.
# def resources_on_calendar_save(sender, instance, created, **kwargs):
#     if created:
#         if hasattr(instance, 'resource'):
#             qs = instance.resource.affected_eventtimes.filter(
#                 resource_status=EventTime.RESOURCE_STATUS_AVAILABLE
#             )
#             EventTime.update_resource_status_for_qs(qs)
#
# post_save.connect(resources_on_calendar_save, sender=Calendar)
#
#
# # When a calendar is deleted it affects the availability of any resource it
# # belongs to. Any blocked eventtime that might use that resource will have
# # recalculate availability.
# def resources_on_calendar_delete(sender, instance, **kwargs):
#     if hasattr(instance, 'resource'):
#         qs = instance.resource.affected_eventtimes.filter(
#             resource_status=EventTime.RESOURCE_STATUS_BLOCKED
#         )
#         EventTime.update_resource_status_for_qs(qs)
#
# post_delete.connect(resources_on_calendar_delete, sender=Calendar)
#
#
# # When a requirement is changed or added to a product any eventtimes for the
# # product will have to recalculate availability
# def resources_on_requirement_save(sender, instance, created, **kwargs):
#     qs = instance.product.eventtime_set.filter(
#         resource_status=EventTime.RESOURCE_STATUS_AVAILABLE
#     )
#     EventTime.update_resource_status_for_qs(qs)
#
# post_save.connect(resources_on_requirement_save, sender=ResourceRequirement)
#
#
# # When a requirement is removed from a product any eventtimes for that
# # product will have to recalculate availability
# def resources_on_requirement_delete(sender, instance, **kwargs):
#     qs = instance.product.eventtime_set.filter(
#         resource_status=EventTime.RESOURCE_STATUS_BLOCKED
#     )
#     EventTime.update_resource_status_for_qs(qs)
#
# post_delete.connect(
#     resources_on_requirement_delete, sender=ResourceRequirement
# )
#
#
# def resources_on_assignment(
#     sender, instance, action, reverse, model, pk_set, **kwargs
# ):
#
#     if action == "post_add" or action == "post_remove":
#         # If we're called with reverse we get the pk_set from the instance
#         # The way we look up affected EventTimes will ensure that we always
#         # update any relevant Visit's eventtimes.
#         if reverse:
#             # Visits are in the pk_set, so we look up any EventTimes from
#             # that:
#             eventtimes = EventTime.objects.filter(visit__in=pk_set)
#             # We want pk_set to be a set of Resource pks so we get the pk
#             # from instance:
#             pk_set = set([instance.pk])
#         else:
#             # Find the EventTime associated with the instance visit
#             eventtimes = EventTime.objects.filter(visit=instance.pk)
#         # When a resource is assigned or unassigned to/from a visit any
#         # EventTimes that might use that resource at the same time needs to
#         # recalculate availability.
#         pools = ResourcePool.objects.filter(
#             resources__in=pk_set
#         )
#         qs = EventTime.objects.filter(
#             product__resourcerequirement__resource_pool__in=pools
#         )
#         time_cond = Q()
#         for x in eventtimes:
#             time_cond = time_cond | Q(
#                 end__gt=x.start,
#                 start__lt=x.end
#             )
#         if time_cond:
#             qs = qs.filter(time_cond)
#
#         if action == "post_add":
#             # When we restrict new resources we're only interested in
#             # updating eventtimes currently marked as available.
#             qs = qs.filter(
#                 resource_status=EventTime.RESOURCE_STATUS_AVAILABLE
#             )
#         else:
#             # When we free up resources we're only interested in updating
#             # eventtimes currently marked as unavailable.
#             qs = qs.filter(
#                 resource_status=EventTime.RESOURCE_STATUS_BLOCKED
#             )
#
#         EventTime.update_resource_status_for_qs(qs)
#
# m2m_changed.connect(resources_on_assignment, sender=Visit.resources.through)
#
#
# def resources_on_teacher_host_assignment(
#     sender, instance, action, reverse, model, pk_set, **kwargs
# ):
#
#     if action == "post_add" or action == "post_remove":
#         if reverse:
#             pk_set = set([instance.pk])
#
#         resources = Resource.objects.filter(
#             Q(teacherresource__user_id__in=pk_set) |
#             Q(hostresource__user_id__in=pk_set)
#         )
#         pools = ResourcePool.objects.filter(resources__in=resources)
#         qs = EventTime.objects.filter(
#             product__resourcerequirement__resource_pool__in=pools
#         )
#         if action == "post_add":
#             # Teachers or hosts being assigned means that available times
#             # that might need them needs to be checked
#             qs = qs.filter(
#                 resource_status=EventTime.RESOURCE_STATUS_AVAILABLE
#             )
#         else:
#             # Teachers or hosts being unassigned means that blocked times
#             # that might need them needs to be checked
#             qs = qs.filter(
#                 resource_status=EventTime.RESOURCE_STATUS_BLOCKED
#             )
#
#         EventTime.update_resource_status_for_qs(qs)
#
# m2m_changed.connect(
#     resources_on_teacher_host_assignment, sender=Visit.teachers.through
# )
# m2m_changed.connect(
#     resources_on_teacher_host_assignment, sender=Visit.hosts.through
# )
#
#
# def resourcepool_assignment_change(
#     sender, instance, action, reverse, model, pk_set, **kwargs
# ):
#     args = (sender, instance, action, reverse, model, pk_set, kwargs)
#     print args
#
#     if action == "pre_clear":
#         setattr(
#             instance,
#             "m2m_changed_pks",
#             set([x for x in instance.resources.all()])
#         )
#     elif action == "post_add":
#         print getattr(instance, "m2m_changed_pks", None)
#
#
# m2m_changed.connect(
#     resourcepool_assignment_change, sender=ResourcePool.resources.through
# )
