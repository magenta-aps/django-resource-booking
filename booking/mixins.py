# encoding: utf-8


class AvailabilityUpdaterMixin(object):

    def save(self, *args, **kwargs):
        aff_qs = self.affected_eventtimes
        EventTime = aff_qs.model
        # Store what will be affected before the change
        affected = set(x.pk for x in aff_qs)

        # Whenever affected_eventtimes is calculated using m2m relations we
        # will get one save before relations are saved and one after. In the
        # one after relations will be broken, but we still have to adjust the
        # eventtimes found at the first save. Therefore we must temporarily
        # store a list of eventtimes to be checked at the next save
        if (
            getattr(self, 'affected_eventtimes_uses_m2m', False) and
            hasattr(self, '_recently_affected')
        ):
            affected.update(self._recently_affected)

        # Perform change
        res = super(AvailabilityUpdaterMixin, self).save(*args, **kwargs)

        # Add what will be affected after the change
        for x in self.affected_eventtimes:
            affected.add(x.pk)

        # Store recently affected, or remove it if we just used it.
        if getattr(self, 'affected_eventtimes_uses_m2m', False):
            if hasattr(self, '_recently_affected'):
                delattr(self, '_recently_affected')
            else:
                self._recently_affected = affected

        # Update cached availability for any calendars affected by this change
        if hasattr(self, "affected_calendars"):
            for x in self.affected_calendars:
                x.recalculate_available()

        # Update availability for everything affected
        EventTime.update_resource_status_for_qs(
            EventTime.objects.filter(pk__in=affected)
        )

        return res

    def delete(self, *args, **kwargs):
        aff_qs = self.affected_eventtimes
        EventTime = aff_qs.model
        # Store what will be affected before the change
        affected = set(x.pk for x in aff_qs)

        # Make a copy of calendars that will be affected by the change
        if hasattr(self, "affected_calendars"):
            affected_calendars = tuple(self.affected_calendars)
        else:
            affected_calendars = None

        # Perform change
        res = super(AvailabilityUpdaterMixin, self).delete(*args, **kwargs)

        # Update cached availability for any calendars affected by this change
        if affected_calendars is not None:
            for x in affected_calendars:
                x.recalculate_available()

        # Update availability for everything affected
        EventTime.update_resource_status_for_qs(
            EventTime.objects.filter(pk__in=affected)
        )

        return res
