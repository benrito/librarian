"""
plugin.py: Diskspace plugin

Display application log on dashboard.

Copyright 2014, Outernet Inc.
Some rights reserved.

This software is free software licensed under the terms of GPLv3. See COPYING
file that comes with the source code, or http://www.gnu.org/licenses/gpl.txt.
"""

import os

from bottle import request, view, redirect, MultiDict, abort

from ...lib import archive
from ...lib.html import hsize
from ...lib.i18n import lazy_gettext as _, i18n_path

from ..dashboard import DashboardPlugin
from ..exceptions import NotSupportedError


@view('cleanup', message=None, vals=MultiDict())
def cleanup_list():
    """ Render a list of items that can be deleted """
    return {'metadata': archive.cleanup_list(),
            'needed': archive.needed_space()}


@view('cleanup', message=None, vals=MultiDict())
def cleanup():
    forms = request.forms
    action = forms.get('action', 'check')
    if action not in ['check', 'delete']:
        # Translators, used as response to innvalid HTTP request
        abort(400, _('Invalid request'))
    selected = forms.getall('selection')
    metadata = list(archive.cleanup_list())
    selected = [z for z in metadata if z['md5'] in selected]
    if action == 'check':
        if not selected:
            # Translators, used as message to user when clean-up is started
            # without selecting any content
            message = _('No content selected')
        else:
            tot = hsize(sum([s['size'] for s in selected]))
            message = str(
                # Translators, used when user is previewing clean-up, %s is
                # replaced by amount of content that can be freed in bytes,
                # KB, MB, etc
                _('%s can be freed by removing selected content')) % tot
        return {'vals': forms, 'metadata': metadata, 'message': message,
                'needed': archive.needed_space()}
    else:
        success, errors = archive.remove_from_archive([z['md5']
                                                       for z in selected])
        if selected and not errors:
            redirect(i18n_path('/'))

        if errors:
            # Translators, error message shown on clean-up page when some of
            # the content could not be removed for unknown reasons
            message = _('Some files could not be removed')
        elif not selected:
            # Translators, error message shown on clean-up page when there was
            # no deletable content
            message = _('Nothing to delete')
        metadata = archive.cleanup_list()
        return {'vals': MultiDict(), 'metadata': metadata,
                'message': message, 'needed': archive.needed_space()}



def install(app, route):
    try:
        os.statvfs
    except AttributeError:
        raise NotSupportedError(
            'Disk space information not available on this platform')
    route('/cleanup/', 'GET', callback=dashboard.cleanup_list)
    route('/cleanup/', 'POST', callback=dashboard.cleanup)


class Dashboard(DashboardPlugin):
    # Translators, used as dashboard section title
    heading = _('Content library stats')
    name = 'diskspace'

    def get_context(self):
        spool, content, total = archive.free_space()
        count = archive.zipball_count()
        used = archive.archive_space_used()
        last_updated = archive.last_update()
        needed = archive.needed_space()
        return locals()