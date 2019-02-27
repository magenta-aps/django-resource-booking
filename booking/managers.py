from django.db import models


class VisitQuerySet(models.QuerySet):
    def active_qs(self):
        return self.exclude(workflow_status__in=[
            self.model.WORKFLOW_STATUS_CANCELLED,
            self.model.WORKFLOW_STATUS_REJECTED
        ])

    def being_planned_queryset(self, **kwargs):
        return self.filter(
            workflow_status__in=[
                self.model.WORKFLOW_STATUS_BEING_PLANNED,
                self.model.WORKFLOW_STATUS_AUTOASSIGN_FAILED,
                self.model.WORKFLOW_STATUS_REJECTED
            ],
            **kwargs
        )

    def planned_queryset(self, **kwargs):
        return self.filter(
            workflow_status__in=[
                self.WORKFLOW_STATUS_PLANNED,
                self.WORKFLOW_STATUS_PLANNED_NO_BOOKING,
                self.WORKFLOW_STATUS_CONFIRMED,
                self.WORKFLOW_STATUS_REMINDED
            ],
        ).filter(**kwargs)
