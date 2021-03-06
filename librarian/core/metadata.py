"""
metadata.py: Handling metadata

Copyright 2014-2015, Outernet Inc.
Some rights reserved.

This software is free software licensed under the terms of GPLv3. See COPYING
file that comes with the source code, or http://www.gnu.org/licenses/gpl.txt.
"""

from __future__ import unicode_literals

import os
import json
import glob
import logging
import zipfile

import dateutil.parser


def default_broadcast(key, meta):
    return dateutil.parser.parse(meta['timestamp']).date()


RTL_LANGS = ['ar', 'he', 'ur', 'yi', 'ji', 'iw', 'fa']

# FIXME: This is a dummy gettext to cause the strings to be extracted.
_ = lambda x: x

LICENSES = (
    (None, _('Unknown license')),
    ('CC-BY', _('Creative Commons Attribution')),
    ('CC-BY-ND', _('Creative Commons Attribution-NoDerivs')),
    ('CC-BY-NC', _('Creative Commons Attribution-NonCommercial')),
    ('CC-BY-ND-NC', _('Creative Commons Attribution-NonCommercial-NoDerivs')),
    ('CC-BY-SA', _('Creative Commons Attribution-ShareAlike')),
    ('CC-BY-NC-SA', _('Creative Commons Attribution-NonCommercial-ShareAlike')),
    ('GFDL', _('GNU Free Documentation License')),
    ('OPL', _('Open Publication License')),
    ('OCL', _('Open Content License')),
    ('ADL', _('Against DRM License')),
    ('FAL', _('Free Art License')),
    ('PD', _('Public Domain')),
    ('OF', _('Other free license')),
    ('ARL', _('All rights reserved')),
    ('ON', _('Other non-free license')),
)

# `default` defaults to `None`
# `aliases` defaults to `[]`
# `required` defaults to `False`
# `auto` defaults to `False`
META_SPECIFICATION = {
    'url': {'required': True},
    'title': {'required': True},
    'images': {'default': 0},
    'timestamp': {'required': True},
    'keep_formatting': {'default': False},
    'is_partner': {'default': False},
    'is_sponsored': {'default': False},
    'archive': {'default': 'core'},
    'publisher': {
        'default': '',
        'aliases': ['partner']
    },
    'license': {
        'required': True
    },
    'language': {'default': ''},
    'multipage': {'default': False},
    'entry_point': {
        'default': 'index.html',
        'aliases': ['index']
    },
    # although this field is required by the specification, legacy content that
    # has no such field defined would be just ignored during processing
    'broadcast': {
        'required': False,
        'default': default_broadcast
    },
    'keywords': {'default': ''},
    'md5': {'auto': True},
    'size': {'auto': True},
    'updated': {'auto': True}
}

STANDARD_FIELDS = dict((k, v) for k, v in META_SPECIFICATION.items()
                       if not v.get('auto', False))

# Used for simple checks
REQUIRED_KEYS = [k for k, v in META_SPECIFICATION.items()
                 if v.get('required', False)]


class MetadataError(Exception):
    """ Base metadata error """
    pass


class DecodeError(MetadataError):
    pass


class FormatError(MetadataError):
    """ Raised when metadata format is wrong """
    pass


def get_default_value(key, meta):
    default = STANDARD_FIELDS[key].get('default', None)
    if callable(default):
        return default(key, meta)
    return default


def get_aliases_for(key):
    return STANDARD_FIELDS[key].get('aliases', [])


def is_required(key):
    return STANDARD_FIELDS[key].get('required', False)


def add_missing_keys(meta):
    """ Make sure metadata dict contains all required keys

    This function modifies the metadata dict in-place, and has no useful return
    value.

    :param meta:    metadata dict
    """
    for key in STANDARD_FIELDS:
        if key not in meta:
            meta[key] = get_default_value(key, meta)


def replace_aliases(meta):
    """ Replace deprecated aliases with their current substitution.

    This function modifies the metadata dict in-place, and has no useful return
    value.

    :param meta:    metadata dict
    """
    for key in STANDARD_FIELDS:
        if key not in meta:
            for alias in get_aliases_for(key):
                if alias in meta:
                    meta[key] = meta.pop(alias)


def clean_keys(meta):
    """ Make sure metadta dict does not have any non-standard keys

    This function modifies the metadata dict in-place, and always returns
    ``None``.

    :param meta:    metadta dict
    """
    valid_keys = STANDARD_FIELDS.keys()
    for key in meta.keys():
        if key not in valid_keys:
            del meta[key]


def convert_json(meta):
    """ Convert metadata JSON to a dictionary and add missing keys

    :param meta:    string JSON meta
    :returns:       metadata dict
    """
    try:
        meta = str(meta.decode('utf8'))
    except UnicodeDecodeError as err:
        raise DecodeError("Failed to decode metadata: '%s'" % err)
    try:
        meta = json.loads(meta)
    except ValueError as err:
        raise DecodeError("Invalid JSON")
    replace_aliases(meta)
    for key in STANDARD_FIELDS:
        if key not in meta and is_required(key):
            raise FormatError("Mandatory key '%s' missing" % key)
    try:
        add_missing_keys(meta)
    except Exception as exc:
        raise DecodeError("Failed to add default values: '%s'" % exc)

    return meta


class Meta(object):
    """ Metadata wrapper with additional methods for easier consumption

    This classed is used as a dict wrapper that provides attrbute access to
    keys, and a few additional properties and methods to ease working with
    metadta.

    Parts of this class are tied to the filesystem (notably the parts that deal
    with content thumbnails). This functionality may be factored out of this
    class at a later time.
    """

    IMAGE_EXTENSIONS = ('.png', '.gif', '.jpg', '.jpeg')

    def __init__(self, meta, cover_dir, zip_path=None):
        """ Metadata wrapper instantiation

        Args:
            meta (dict)         Raw metadata as dict
            cover_dir (str)     Directory path where content covers are stored

        Kwargs:
            zip_path (str)      Optional path to zip file

        """
        self.meta = meta
        # We use ``or`` in the following line because 'tags' can be an empty
        # string, which is treated as invalid JSON
        self.tags = json.loads(meta.get('tags') or '{}')
        self._image = None
        self.cover_dir = os.path.normpath(cover_dir)
        self.zip_path = zip_path

    def __getattr__(self, attr):
        try:
            return self.meta[attr]
        except KeyError:
            raise AttributeError("Attribute or key '%s' not found" % attr)

    def __getitem__(self, key):
        return self.meta[key]

    def __setitem__(self, key, value):
        self.meta[key] = value

    def __delitem__(self, key):
        del self.meta[key]

    def __contains__(self, key):
        return key in self.meta

    def get(self, key, default=None):
        """ Return the value of a metadata or the default value

        This method works exactly the same as ``dict.get()``, except that it
        only works on the keys that exist on the underlying metadata dict.

        :param key:     name of the key to look up
        :param default: default value to use if key is missing
        """
        return self.meta.get(key, default)

    def cache_cover(self, ext, content):
        """ Store the content cover image with specified extension and content

        The cover is saved in a predefined path within the cover directory
        given during initialization. The filename of the cover file matches the
        content ID (md5 hash).

        .. caution::

            Attacker may inject non-image content in an image file to explot
            browser vulnerabilities. This method writes content to the file
            blindly without checking it. It is the caller's responsibility to
            chek the content before calling this method.

        :param ext:     file extension
        :param content: file content
        :returns:       filename (not full path) of the created cover
        """
        cover_path = os.path.join(self.cover_dir, '%s%s' % (self.md5, ext))
        with open(cover_path, 'wb') as f:
            f.write(content)
        return os.path.basename(cover_path)

    def extract_image(self):
        with open(self.zip_path, 'rb') as f:
            z = zipfile.ZipFile(f)
            for name in z.namelist():
                extension = os.path.splitext(name)[1].lower()
                if extension in self.IMAGE_EXTENSIONS:
                    content = z.open(name, 'r').read()
                    return extension, content
            return None, None

    def get_cover_path(self):
        cover_path = os.path.join(self.cover_dir, '%s.*' % self.md5)
        g = glob.glob(cover_path)
        try:
            return os.path.basename(g[0])
        except IndexError:
            return None

    @property
    def lang(self):
        return self.meta.get('language')

    @property
    def rtl(self):
        return self.lang in RTL_LANGS

    @property
    def i18n_attrs(self):
        s = ''
        if self.lang:
            # XXX: Do we want to keep the leading space?
            s += ' lang="%s"' % self.lang
        if self.rtl:
            s += ' dir="rtl"'
        return s

    @property
    def label(self):
        if self.meta.get('archive') == 'core':
            return 'core'
        elif self.meta.get('is_sponsored'):
            return 'sponsored'
        elif self.meta.get('is_partner'):
            return 'partner'
        return 'core'

    @property
    def free_license(self):
        return self.license not in ['ARL', 'ON']

    @property
    def image(self):
        if self._image is not None:
            return self._image
        cover = self.get_cover_path()
        if cover:
            self._image = cover
            return self._image
        if not self.zip_path:
            return None
        try:
            extension, content = self.extract_image()
        except (TypeError, OSError):
            # Could not find the zip file
            logging.error("Could not find or read zip file '%s.zip'", self.md5)
            return None
        if extension is None or content is None:
            return None
        try:
            self._image = self.cache_cover(extension, content)
        except OSError:
            # Could not write the content
            logging.error("Could not write the cover image for '%s'", self.md5)
            return None
        return self._image
