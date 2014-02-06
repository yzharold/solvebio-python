# -*- coding: utf-8 -*-
import urllib
import re

# from utils.tabulate import tabulate
from .client import client
# from querying import Query

try:
    import json
except ImportError:
    json = None

# test for compatible json module
if not (json and hasattr(json, 'loads')):
    import simplejson as json


def camelcase_to_underscore(name):
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def convert_to_solve_object(resp):
    types = {
        'Depository': Depository,
        'DepositoryVersion': DepositoryVersion,
        'Dataset': Dataset,
        'DatasetField': DatasetField,
        'User': User,
        'list': ListObject
    }

    if isinstance(resp, list):
        return [convert_to_solve_object(i) for i in resp]
    elif isinstance(resp, dict) and not isinstance(resp, SolveObject):
        resp = resp.copy()
        klass_name = resp.get('class_name')
        if isinstance(klass_name, basestring):
            klass = types.get(klass_name, SolveObject)
        else:
            klass = SolveObject
        return klass.construct_from(resp)
    else:
        return resp


class SolveObject(dict):
    """Base class for all SolveBio API resource objects"""

    def __init__(self, id=None, **params):
        super(SolveObject, self).__init__()

        if id:
            self['id'] = id
        elif params.get('urn'):
            self['urn'] = params.get('urn')

    def __setattr__(self, k, v):
        if k[0] == '_' or k in self.__dict__:
            return super(SolveObject, self).__setattr__(k, v)
        else:
            self[k] = v

    def __getattr__(self, k):
        if k[0] == '_':
            raise AttributeError(k)

        try:
            return self[k]
        except KeyError, err:
            raise AttributeError(*err.args)

    @classmethod
    def construct_from(cls, values):
        """Used to create a new object from an HTTP response"""
        instance = cls(values.get('id'))
        instance.refresh_from(values)
        return instance

    def refresh_from(self, values):
        self.clear()
        for k, v in values.iteritems():
            super(SolveObject, self).__setitem__(
                k, convert_to_solve_object(v))

    def request(self, method, url, params=None):
        response = client.request(method, url, params)
        return convert_to_solve_object(response)

    def __repr__(self):
        ident_parts = [type(self).__name__]

        if isinstance(self.get('class_name'), basestring):
            ident_parts.append(self.get('class_name').encode('utf8'))

        if isinstance(self.get('id'), int):
            ident_parts.append('id=%d' % (self.get('id'),))

        if isinstance(self.get('urn'), unicode):
            ident_parts.append('urn=%s' % (self.get('urn'),))

        return '<%s at %s> JSON: %s' % (
            ' '.join(ident_parts), hex(id(self)), str(self))

    def __str__(self):
        return json.dumps(self, sort_keys=True, indent=2)

    @property
    def solvebio_id(self):
        return self.id or self.urn


class APIResource(SolveObject):

    @classmethod
    def retrieve(cls, id, **params):
        instance = cls(id, **params)
        instance.refresh()
        return instance

    def refresh(self):
        self.refresh_from(self.request('get', self.instance_url()))
        return self

    @classmethod
    def class_name(cls):
        if cls == APIResource:
            raise NotImplementedError(
                'APIResource is an abstract class.  You should perform '
                'actions on its subclasses (e.g. Depository, Dataset)')
        return str(urllib.quote_plus(cls.__name__))

    @classmethod
    def class_url(cls):
        cls_name = cls.class_name()
        # pluralize
        if cls_name.endswith('y'):
            cls_name = cls_name[:-1] + 'ie'
        cls_name = camelcase_to_underscore(cls_name)
        return "/v1/%ss" % (cls_name,)

    def instance_url(self):
        """Get instance URL by ID or URN (if available)"""
        id = self.get('id')
        urn = self.get('urn')
        base = self.class_url()

        if id:
            return "%s/%d" % (base, id)
        elif urn:
            return "%s/%s" % (base, urn)
        else:
            raise Exception(
                'Could not determine which URL to request: %s instance '
                'has invalid ID: %r' % (type(self).__name__, id), 'id')


class ListObject(SolveObject):

    def all(self, **params):
        return self.request('get', self['url'], params)

    def create(self, **params):
        return self.request('post', self['url'], params)

    def next_page(self, **params):
        if self['links']['next']:
            return self.request('get', self['links']['next'], params)
        return None

    def prev_page(self, **params):
        if self['links']['prev']:
            self.request('get', self['links']['prev'], params)
        return None

    def objects(self):
        return convert_to_solve_object(self['data'])

    def __iter__(self):
        self._i = 0
        return self

    def next(self):
        if not getattr(self, '_i', None):
            self._i = 0

        if self._i >= len(self['data']):
            # get the next page of results
            next_page = self.next_page()
            if next_page is None:
                raise StopIteration
            self.refresh_from(next_page)
            self._i = 0

        obj = convert_to_solve_object(self['data'][self._i])
        self._i += 1
        return obj


class SingletonAPIResource(APIResource):

    @classmethod
    def retrieve(cls):
        return super(SingletonAPIResource, cls).retrieve(None)

    @classmethod
    def class_url(cls):
        cls_name = cls.class_name()
        cls_name = camelcase_to_underscore(cls_name)
        return "/v1/%s" % (cls_name,)

    def instance_url(self):
        return self.class_url()


class ListableAPIResource(APIResource):

    @classmethod
    def all(cls, **params):
        url = cls.class_url()
        response = client.request('get', url, params)
        return convert_to_solve_object(response)


class SearchableAPIResource(APIResource):

    @classmethod
    def search(cls, query='', **params):
        params.update({'q': query})
        url = cls.class_url()
        response = client.request('get', url, params)
        return convert_to_solve_object(response)


class CreateableAPIResource(APIResource):

    @classmethod
    def create(cls, **params):
        url = cls.class_url()
        response = client.request('post', url, params)
        return convert_to_solve_object(response)


class User(SingletonAPIResource):
    pass


class Depository(CreateableAPIResource, ListableAPIResource,
                 SearchableAPIResource):
    URN_REGEX = r'^urn:solvebio:[\w\d\-\.]+$'
    URN_FORMAT = 'urn:solvebio:{DEPOSITORY}'

    @classmethod
    def retrieve(cls, id, **params):
        """Supports lookup by URN"""
        if isinstance(id, unicode) or isinstance(id, str):
            params.update({'urn': unicode(id).strip()})
            id = None
            if not re.match(cls.URN_REGEX, params['urn']):
                raise Exception('Unrecognized URN. Must be in the following '
                                'format: "%s"' % cls.URN_FORMAT)

        return super(Depository, cls).retrieve(id, **params)

    def versions(self, **params):
        response = client.request('get', self.versions_url, params)
        return convert_to_solve_object(response)


class DepositoryVersion(CreateableAPIResource, ListableAPIResource):
    URN_REGEX = r'^urn:solvebio(:[\w\d\-\.]+){2}$'
    URN_FORMAT = 'urn:solvebio:{DEPOSITORY}:{VERSION}'

    @classmethod
    def retrieve(cls, id, **params):
        """Supports lookup by URN"""
        if isinstance(id, unicode) or isinstance(id, str):
            params.update({'urn': unicode(id).strip()})
            id = None
            if not re.match(cls.URN_REGEX, params['urn']):
                raise Exception('Unrecognized URN. Must be in the following '
                                'format: "%s"' % cls.URN_FORMAT)

        return super(DepositoryVersion, cls).retrieve(id, **params)

    def datasets(self, **params):
        response = client.request('get', self.datasets_url, params)
        return convert_to_solve_object(response)


class Dataset(CreateableAPIResource, ListableAPIResource):
    URN_REGEX = r'^urn:solvebio(:[\w\d\-\.]+){3}$'
    URN_FORMAT = 'urn:solvebio:{DEPOSITORY}:{VERSION}:{DATASET}'

    @classmethod
    def retrieve(cls, id, **params):
        """Supports lookup by URN"""
        if isinstance(id, unicode) or isinstance(id, str):
            params.update({'urn': unicode(id).strip()})
            id = None
            if not re.match(cls.URN_REGEX, params['urn']):
                raise Exception('Unrecognized URN. Must be in the following '
                                'format: "%s"' % cls.URN_FORMAT)

        return super(Dataset, cls).retrieve(id, **params)

    def depository_version(self):
        return DepositoryVersion.retrieve(self['depository_version'])

    def depository(self):
        return Depository.retrieve(self['depository'])

    def fields(self, **params):
        response = client.request('get', self.fields_url, params)
        return convert_to_solve_object(response)

    def query(self, **filters):
        # TODO: support querying
        pass


class DatasetField(CreateableAPIResource, ListableAPIResource):
    URN_REGEX = r'^urn:solvebio(:[\w\d\-\.]+){4}$'
    URN_FORMAT = 'urn:solvebio:{DEPOSITORY}:{VERSION}:{DATASET}:{FIELD}'

    @classmethod
    def retrieve(cls, id, **params):
        """Supports lookup by URN"""
        if isinstance(id, unicode) or isinstance(id, str):
            params.update({'urn': unicode(id).strip()})
            id = None
            if not re.match(cls.URN_REGEX, params['urn']):
                raise Exception('Unrecognized URN. Must be in the following '
                                'format: "%s"' % cls.URN_FORMAT)

        return super(Dataset, cls).retrieve(id, **params)

    def facets(self, **params):
        response = client.request('get', self.facets_url, params)
        return convert_to_solve_object(response)



# class NamespaceDirectory(object):
#     """
#     The Directory is a singleton used to contain all Namespaces.
#     """

#     def __init__(self):
#         self._name = 'solvebio.data'
#         self._namespaces = None  # lazy loaded

#     def __repr__(self):
#         return '<NamespaceDirectory: %s>' % self._name

#     def __str__(self):
#         return self._name

#     def __dir__(self):
#         return [k['name'] for k in self._get_namespaces()]

#     def __getattr__(self, name):
#         self._get_namespaces()
#         return object.__getattribute__(self, name)

#     def help(self):
#         _content = 'All Online Namespaces:\n\n'
#         _content += tabulate([(ns['name'], ns['title'])
#                              for ns in self._get_namespaces()],
#                              ['Namespace', 'Title'])
#         print _content

#     def _get_namespaces(self):
#         if self._namespaces is None:
#             # load Namespaces from API store in instance cache
#             self._namespaces = sorted(client.get_namespaces(),
#                                       key=lambda k: k['name'])
#             for namespace in self._namespaces:
#                 self.__dict__[namespace['name']] = Namespace(**namespace)

#         return self._namespaces


# class Namespace(object):
#     """Namespaces are named-containers of Datasets"""

#     def __init__(self, **meta):
#         self._datasets = None  # lazy loaded
#         for k, v in meta.items():
#             self.__dict__['_' + k] = v

#     def __repr__(self):
#         return '<Namespace: %s>' % self._name

#     def __str__(self):
#         return self._name

#     def __dir__(self):
#         return [k['name'] for k in self._get_datasets()]

#     def __getattr__(self, name):
#         self._get_datasets()
#         return object.__getattribute__(self, name)

#     def _get_datasets(self):
#         if self._datasets is None:
#             self._datasets = sorted(client.get_namespace(self._name)['datasets'],
#                                     key=lambda k: k['name'])
#             for ds in self._datasets:
#                 path = '%s/%s' % (ds['namespace'], ds['name'])
#                 self.__dict__[ds['name']] = Dataset(path, **ds)

#         return self._datasets

#     def help(self):
#         _content = 'Datasets in %s:\n\n' % self._name
#         _content += tabulate([('%s.%s' % (d['namespace'], d['name']), d['title'])
#                               for d in self._get_datasets()],
#                               ['Dataset', 'Title'])
#         print _content


# class Dataset(object):
#     """
#     Stores a Dataset and its fields
#     """

#     def __init__(self, path, **meta):
#         self._path = path
#         self._dataset = None

#         if not meta:
#             # if no metadata is passed, we'll need to fetch it
#             self._namespace, self._name = path.split('/')
#             meta = self._get_dataset()

#         for k, v in meta.items():
#             # prefix each field with '_'
#             self.__dict__['_' + k] = v

#     def _get_dataset(self):
#         if self._dataset is None:
#             self._dataset = client.get_dataset(self._namespace, self._name)

#         return self._dataset

#     def select(self, *filters, **kwargs):
#         """Create and return a new Select object with the set of Filters"""
#         return Select(self).select(*filters, **kwargs)

#     def range(self, chromosome, start, end, overlap=False):
#         """Shortcut to do a range queries on supported Datasets"""
#         return Select(self).range(chromosome, start, end, overlap)

#     def help(self, field=None):
#         self._get_dataset()

#         if field is None:
#             # show dataset help information
#             fields = [(k['name'], k['data_type'], k['description']) for k
#                         in sorted(self._dataset['fields'], key=lambda k: k['name'])]
#             print u'\nHelp for: %s\n%s\n%s\n\n%s\n\n' % (
#                         self,
#                         self._title,
#                         self._description,
#                         tabulate(fields, ['Field', 'Type', 'Description']))
#         else:
#             # Show detailed field information
#             try:
#                 field = client.get_dataset_field(self._namespace, self._name, field)
#             except:
#                 print u'\nSorry there was a problem getting information about that field. Please try again later.\n'
#                 return False

#             print u'\nHelp for field %s from dataset %s:\n' % (field['name'], self._title)
#             print u'This field contains %s-type data' % field['data_type']
#             print field['description']

#             if field['facets'] and field['data_type'] == 'string':
#                 print tabulate([(f,) for f in sorted(field['facets'])], ['Facets'])
#             elif field['facets'] and field['data_type'] in ('integer', 'double', 'long', 'float'):
#                 print 'Minimum value: %s' % field['facets'][0]
#                 print 'Maximum value: %s' % field['facets'][1]
#             else:
#                 print 'No facets are available for this field'

#     def __repr__(self):
#         return '<Dataset: %s>' % self._path

#     def __str__(self):
#         return self._path


# directory = NamespaceDirectory()