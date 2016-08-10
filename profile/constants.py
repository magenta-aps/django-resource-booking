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

# Which roles are available for editing?
# E.g. a faculty editor can create, edit and delete coordinators but not admins
available_roles = {
    NONE: [],
    TEACHER: [],
    HOST: [],
    COORDINATOR: [NONE, TEACHER, HOST, COORDINATOR],
    FACULTY_EDITOR: [NONE, TEACHER, HOST, COORDINATOR, FACULTY_EDITOR],
    ADMINISTRATOR: [
        NONE, TEACHER, HOST, COORDINATOR, FACULTY_EDITOR, ADMINISTRATOR
    ]
}