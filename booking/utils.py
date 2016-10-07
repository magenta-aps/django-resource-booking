# encoding: utf-8
from django.contrib.contenttypes.models import ContentType
from django.contrib.admin.models import LogEntry, DELETION, ADDITION, CHANGE
from django.core.exceptions import SuspiciousFileOperation
from django.core.files.storage import FileSystemStorage
from subprocess import Popen, PIPE
import os
import sys

import csv
import codecs
import cStringIO
from itertools import chain


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

_releated_content_types_cache = {}


def get_related_content_types(model):
    if model not in _releated_content_types_cache:

        types = [ContentType.objects.get_for_model(model)]

        for rel in model._meta.get_all_related_objects():
            if not rel.one_to_one:
                continue

            rel_model = rel.related_model

            if model not in rel_model._meta.get_parent_list():
                continue

            types.append(
                ContentType.objects.get_for_model(rel_model)
            )

        _releated_content_types_cache[model] = types

    return _releated_content_types_cache[model]


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
        cmd = "w3m -dump -T text/html -O utf-8"
        proc = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE)
        enc_str = unicode(value).encode('ascii', 'xmlcharrefreplace')
        return proc.communicate(enc_str)[0]
    except OSError:
        # something bad happened, so just return the input
        return value


def get_model_field_map(model, visited_models=None):
    if visited_models is None:
        visited_models = set()

    visited_models.add(model)
    map = {}

    for field in model._meta.get_fields():
        label = field.name
        if field.is_relation:
            # For backwards compatibility GenericForeignKey should not be
            # included in the results.
            if field.many_to_one and field.related_model is None:
                continue

            # Relations to child proxy models should not be included.
            # if field.model != model and
            # field.model._meta.concrete_model == model.concrete_model:
            #    continue

            if field.one_to_many:
                # print "ignoring field %s.%s because
                # it is one-to-many" % (model.__name__, field.name)
                continue

            if field.many_to_many:
                # print "ignoring field %s.%s because
                # it is many-to-many" % (model.__name__, field.name)
                continue

            if field.related_model == model:
                # print "ignoring field %s.%s because
                # it points to the same model" % (model.__name__, field.name)
                continue

            if field.related_model in visited_models:
                # print "Already seen %s.%s (%s)" %
                # (model.__name__, field.name, field.related_model.__name__)
                continue

            if issubclass(field.related_model, model):
                # print "%s is subclass of %s" %
                # (field.related_model.__name__, model.__name__)
                continue

            try:
                label = field.related_model._meta.verbose_name
            except:
                pass
            value = get_model_field_map(field.related_model, visited_models)
        else:
            try:
                label = field.verbose_name
            except:
                pass
            value = True
        map[(field.name, label)] = value
    return map

INFINITY = float("inf")


class UnicodeWriter:
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-16le", **kwds):
        # Redirect output to a queue
        self.queue = cStringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def writerow(self, row):
        self.writer.writerow([s.encode("utf-8") for s in row])
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)


def merge_dicts(*dicts):
    result = {}
    for dict in dicts:
        result.update(dict)
    return result


def flatten(args):
    for arg in args:
        if type(arg) in (type(()), type([])):
            for elem in arg:
                yield flatten(elem)
        else:
            yield arg


def intersection(*lists):
    """
    Given several lists, find the intersection between them all
    """
    common = set(lists[0])
    for item in lists[1:]:
        common = common.intersection(item)
    return list(common)


def union(*lists):
    """
    Given several lists, find the union of them all
    """
    return list(set(chain(*lists)))


def binary_or(*items):
    """
    OR several integers together (handy when they vary in number)
    """
    base = 0
    for item in flatten([items]):
        try:
            base = base | item
        except:
            pass
    return base


def binary_and(items):
    """
    AND several integers together (handy when they vary in number)
    """
    base = sys.maxint
    for item in flatten(items):
        try:
            base = base & item
        except:
            pass
    return base

