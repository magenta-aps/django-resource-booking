-- Insert non-visit resources in the otherresource table
INSERT INTO booking_otherresource (resource_ptr_id, link)
SELECT
    booking_resource.id pk,
    ''  link
FROM
    booking_resource
WHERE
    booking_resource.type NOT IN (0, 1, 3, 6)
    AND
    NOT EXISTS (
        SELECT
            resource_ptr_id
        FROM
            booking_otherresource
        WHERE
            booking_otherresource.resource_ptr_id=booking_resource.id
    )
;

-- Delete non-visit resources in the visit table
DELETE FROM
    booking_visit
WHERE
    booking_visit.resource_ptr_id IN (
        SELECT
            booking_resource.id
        FROM
            booking_resource
        WHERE
            booking_resource.type NOT IN (0, 1, 3, 6)
            AND
            booking_resource.id = booking_visit.resource_ptr_id
    )
;
