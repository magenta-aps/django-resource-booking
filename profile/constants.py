# encoding: utf-8

# This file is to keep contants separate from the models.py file so we avoid
# problems with mutual imports for files that just want to acces the contants.

from django.utils.translation import ugettext_lazy as _


TEACHER = 0
HOST = 1
COORDINATOR = 2
ADMINISTRATOR = 3
FACULTY_EDITOR = 4
NONE = 5

EDIT_ROLES = set([
    ADMINISTRATOR,
    FACULTY_EDITOR,
    COORDINATOR
])

user_role_choices = (
    (TEACHER, _(u"Underviser")),
    (HOST, _(u"Vært")),
    (COORDINATOR, _(u"Koordinator")),
    (ADMINISTRATOR, _(u"Administrator")),
    (FACULTY_EDITOR, _(u"Fakultetsredaktør")),
    (NONE, _(u"Ingen"))
)


def get_role_name(role):
    for id, label in user_role_choices:
        if id == role:
            return label

# Which roles are available for editing?
# E.g. a faculty editor can create, edit and delete coordinators but not admins
available_roles = {
    NONE: [],
    TEACHER: [],
    HOST: [],
    COORDINATOR: [TEACHER, HOST, COORDINATOR],
    FACULTY_EDITOR: [TEACHER, HOST, COORDINATOR, FACULTY_EDITOR],
    ADMINISTRATOR: [
        TEACHER, HOST, COORDINATOR, FACULTY_EDITOR, ADMINISTRATOR
    ]
}


def role_to_text(role):
    """Return text representation of role code."""
    for r, t in user_role_choices:
        if r == role:
            return unicode(t)
    return ""
