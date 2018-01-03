# encoding: utf-8


class AvailabilityUpdaterMixin(object):

    def save(self, *args, **kwargs):
        aff_qs = self.affected_eventtimes
        EventTime = aff_qs.model
        # Store what will be affected before the change
        affected = set(x.pk for x in aff_qs)

        # Perform change
        res = super(AvailabilityUpdaterMixin, self).save(*args, **kwargs)

        # Add what will be affected after the change
        for x in self.affected_eventtimes:
            affected.add(x.pk)

        print "Moooo"

        # Update availability for everything affected
        EventTime.update_resource_status_for_qs(
            EventTime.objects.filter(pk__in=affected)
        )

        return res

    def delete(self, *args, **kwargs):
        aff_qs = self.affected_eventtimes
        EventTime = aff_qs.model
        # Store what will be affected before the change
        affected = set(x for x in aff_qs)

        # Perform change
        res = super(AvailabilityUpdaterMixin, self).delete(*args, **kwargs)

        # Update availability for everything affected
        EventTime.update_resource_status_for_qs(
            EventTime.objects.filter(pk__in=affected)
        )

        return res
