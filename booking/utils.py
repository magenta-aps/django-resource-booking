# encoding: utf-8
from django.contrib.contenttypes.models import ContentType
from django.contrib.admin.models import LogEntry, DELETION, ADDITION, CHANGE
from django.core.exceptions import SuspiciousFileOperation
from django.core.files.storage import FileSystemStorage
from subprocess import Popen, PIPE
import os


class LogAction(object):
    CREATE = ADDITION
    CHANGE = CHANGE
    DELETE = DELETION
    # If we need to add additional values make sure they do not conflict with
    # system defined ones by adding 128 to the value.
    CUSTOM1 = 128 + 1
    CUSTOM2 = 128 + 2


def log_action(user, obj, action_flag, change_message=''):
    user_id = user.pk if user else None
    content_type_id = None
    object_id = None
    object_repr = ""
    if obj:
        ctype = ContentType.objects.get_for_model(obj)
        content_type_id = ctype.pk
        try:
            object_id = obj.pk
        except:
            pass
        try:
            object_repr = repr(obj)
        except:
            pass

    LogEntry.objects.log_action(
        user_id,
        content_type_id,
        object_id,
        object_repr,
        action_flag,
        change_message
    )


# Decorator for @property on class variables
class ClassProperty(object):

    def __init__(self, func):
        self.func = func

    def __get__(self, inst, cls):
        return self.func(cls)


def full_email(email, name=None):
    if name is None or name == '':
        return email
    return "\"%s\" <%s>" % (name, email)


# Cribbed from django.core.files.storage.Storage with a few modifications
class CustomStorage(FileSystemStorage):
    def get_available_name(self, name, max_length=None):
        """
        Returns a filename that's free on the target storage system, and
        available for new content to be written to.
        """
        dir_name, file_name = os.path.split(name)
        file_root, file_ext = os.path.splitext(file_name)
        # If the filename already exists, add an underscore and a random 7
        # character alphanumeric string (before the file extension, if one
        # exists) to the filename until the generated filename doesn't exist.
        # Truncate original name if required, so the new filename does not
        # exceed the max_length.
        counter = 1
        while self.exists(name) or (max_length and len(name) > max_length):
            # file_ext includes the dot.
            name = os.path.join(dir_name, "%s_%d%s" % (file_root, counter,
                                                       file_ext))
            if max_length is None:
                continue
            # Truncate file_root if max_length exceeded.
            truncation = len(name) - max_length
            if truncation > 0:
                file_root = file_root[:-truncation]
                # Entire file_root was truncated in attempt
                # to find an available filename.
                if not file_root:
                    raise SuspiciousFileOperation(
                        'Storage can not find an available filename for "%s". '
                        'Please make sure that the corresponding file field '
                        'allows sufficient "max_length".' % name
                    )
                name = os.path.join(dir_name, "%s_%d%s" %
                                    (file_root, counter, file_ext))
            counter += 1
        return name


def html2text(value):
    """
    Pipes given HTML string into the text browser W3M, which renders it.
    Rendered text is grabbed from STDOUT and returned.
    """
    try:
        cmd = "w3m -dump -T text/html -O ascii"
        proc = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE)
        return proc.communicate(str(value))[0]
    except OSError:
        # something bad happened, so just return the input
        return value
