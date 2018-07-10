# encoding: utf-8
import cStringIO
import codecs
import csv
import os
import re
import sys
from itertools import chain
from subprocess import Popen, PIPE

import requests
from django.conf import settings
from django.contrib.admin.models import LogEntry, DELETION, ADDITION, CHANGE
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import SuspiciousFileOperation
from django.core.files.storage import FileSystemStorage


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
    flat = []
    if type(args) in (type(()), type([])):
        for arg in args:
            flat.extend(flatten(arg))
    else:
        flat.append(args)
    return flat


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
    for item in list(flatten([items])):
        try:
            base = base | item
        except:
            pass
    return base


def binary_and(*items):
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


class DummyRecipient(object):
    def get_name(self):
        return "Eksempel Modtager"

    def get_email(self):
        return "email@example.com"


class TemplateSplit(object):

    if_re = r'{%\s*if[^}]+}'
    elif_re = r'{%\s*elif[^}]+}'
    else_re = r'{%\s*else[^}]+}'
    endif_re = r'{%\s*endif[^}]+}'

    class SubBlock(object):
        def __init__(self, block, t_start, t_end):
            self.t_start = t_start
            self.t_end = t_end
            self.block = block

        def contains(self, index):
            return self.t_start[0] <= index < self.t_end[1]

        @property
        def condition(self):
            return self.block.templatesplit.text[
                   self.t_start[0]:self.t_start[1]
            ]

        def has_condition(self, condition):
            return condition in self.condition

        @property
        def text(self, inclusive=False):
            start = self.t_start[0 if inclusive else 1]
            end = self.t_end[1 if inclusive else 0]
            return self.block.templatesplit.text[start:end]

        def __str__(self):
            return "SubBlock from %s to %s" % (self.t_start, self.t_end)

    class Block(object):
        def __init__(
                self, templatesplit, t_if, t_endif, t_else=None, l_elif=None
        ):
            self.t_if = t_if
            self.t_endif = t_endif
            self.t_else = t_else
            self.l_elif = l_elif
            self.subblocks = []
            self.templatesplit = templatesplit

            idx_list = [t_if]
            if l_elif is not None and len(l_elif) > 0:
                idx_list.extend(l_elif)
            if t_else is not None:
                idx_list.append(t_else)
            idx_list.append(t_endif)

            for idx, tup in enumerate(idx_list):
                if idx < len(idx_list) - 1:
                    next = idx_list[idx+1]
                    self.subblocks.append(
                        TemplateSplit.SubBlock(self, tup, next)
                    )

        def get_subblock_containing(self, index):
            for subblock in self.subblocks:
                if subblock.contains(index):
                    return subblock

        def get_subblock_with_condition(self, condition):
            for subblock in self.subblocks:
                if subblock.has_condition(condition):
                    return subblock

        def get_else_subblock(self):
            for subblock in self.subblocks:
                if subblock.t_start == self.t_else:
                    return subblock

        @property
        def text(self, inclusive=False):
            start = self.t_if[0 if inclusive else 1]
            end = self.t_endif[1 if inclusive else 0]
            return self.templatesplit.text[start:end]

        @property
        def text_before(self):
            end = self.t_if[0]
            return self.templatesplit.text[0:end]

        @property
        def text_after(self):
            start = self.t_endif[1]
            return self.templatesplit.text[start:]

    def __init__(self, text):
        self.text = text
        if_locations = list([
            match.span(0) for match in re.finditer(self.if_re, text)
        ])
        elif_locations = list([
            match.span(0) for match in re.finditer(self.elif_re, text)
        ])
        else_locations = list([
            match.span(0) for match in re.finditer(self.else_re, text)
        ])
        endif_locations = list([
            match.span(0) for match in re.finditer(self.endif_re, text)
        ])

        self.blocks = []
        while True:
            len_ifs = len(if_locations)
            found_complete_blocks = []
            for index, found_if in enumerate(if_locations):
                next_if = if_locations[index+1] if index < len_ifs-1 else None
                found_endif = self.find_next(
                    endif_locations,
                    found_if[1],
                    next_if[0] if next_if else None
                )
                found_else = self.find_next(
                    else_locations,
                    found_if[1],
                    found_endif[0] if found_endif else None
                )
                found_elif = self.find_all_next(
                    elif_locations,
                    found_if[1],
                    found_else[1] if found_else else (
                        found_endif[0] if found_endif else None
                    )
                )
                if found_endif:
                    found_complete_blocks.append(
                        TemplateSplit.Block(
                            self, found_if, found_endif,
                            found_else, found_elif
                        )
                    )

            if len(found_complete_blocks) > 0:
                self.blocks.extend(found_complete_blocks)
                for block in found_complete_blocks:
                    if_locations.remove(block.t_if)
                    endif_locations.remove(block.t_endif)
                    for t_elif in block.l_elif:
                        elif_locations.remove(t_elif)
            else:
                break

    def get_subblock_containing(self, c):
        candidates = []
        for block in self.blocks:
            if isinstance(c, basestring):
                subblock = block.get_subblock_with_condition(c)
            else:
                subblock = block.get_subblock_containing(c)
            if subblock is not None:
                candidates.append(subblock)
        if len(candidates) > 0:
            best_candidate = None
            for candidate in candidates:
                if best_candidate is None or \
                        candidate.t_start[0] > best_candidate.t_start[0]:
                    best_candidate = candidate
            return best_candidate

    def get_blocktext_containing(self, c, inclusive=False):
        block = self.get_subblock_containing(c)
        if block is not None:
            return block.text(inclusive)

    @staticmethod
    def find_next(locations, start, before=None):
        for (begin, end) in locations:
            if begin >= start:
                if before is not None and begin >= before:
                    return None
                return (begin, end)

    @staticmethod
    def find_all_next(locations, start, before=None):
        all = []
        while 1:
            found = TemplateSplit.find_next(locations, start, before)
            if found:
                all.append(found)
                start = found[1]
            else:
                return all


def surveyxact_upload(survey_id, data):
    config = settings.SURVEYXACT
    csv_prefix = '\xff\xfe'
    csv_suffix = '\x0a\x00'
    header = []
    body = []
    for key, value in data.iteritems():
        header.append(unicode(key))
        if value is None:
            value = ''
        if not isinstance(value, basestring):
            value = unicode(value)
        body.append(value)
    csv_body = u"%s\t\n%s\t" % ('\t'.join(header), '\t'.join(body))

    response = requests.post(
        config['url'],
        headers={
            'Expect': '100-continue'
        },
        data={
            'username': config['username'],
            'password': config['password'],
            'surveyId': str(survey_id)
        },
        files={
            'dataFile': (
                'data.csv',
                csv_prefix + csv_body.encode('UTF-16LE') + csv_suffix
            )
        }
    )
    if response.status_code != 200:
        print "Error creating respondent with data:"
        print body
    else:
        m = re.search(r'<collecturl>([^<]*)</collecturl>', response.text)
        if m is not None:
            return m.group(1)
        else:
            print "Didn't find collecturl in %s" % response.text


def bool2int(bool):
    return 1 if bool else 0


def prune_list(l, prune_empty_string=False):
    return [
        x for x in l
        if x is not None and not (prune_empty_string and x == '')
    ]


def getattr_long(object, path, default=None):
    for p in path.split('.'):
        try:
            object = getattr(object, p)
        except AttributeError:
            return default
    return object


def prose_list_join(items, sep, lsep):
    return sep.join([unicode(item) for item in items[:-1]]) + \
           unicode(lsep) + unicode(items[-1])


def lcfirst(string):
    return string[0].lower() + string[1:]
