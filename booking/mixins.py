# encoding: utf-8


class AvailabilityUpdaterMixin(object):

    def save(self, *args, **kwargs):
        # Store what will be affected before the change
        affected = set(x for x in self.affected_eventtimes)

        # Perform change
        res = super(AvailabilityUpdaterMixin, self).save(*args, **kwargs)

        # Add what will be affected after the change
        for x in self.affected_eventtimes:
            affected.add(x)

        # Update availability for everything affected
        for x in affected:
            x.update_availability()

        return res

    def delete(self, *args, **kwargs):
        # Store what will be affected before the change
        affected = set(x for x in self.affected_eventtimes)

        # Perform change
        res = super(AvailabilityUpdaterMixin, self).delete(*args, **kwargs)

        # Update availability for everything affected
        for x in affected:
            x.update_availability()

        return res
