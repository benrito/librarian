"""
downloads.py: routes related to downloads

Copyright 2014, Outernet Inc.
Some rights reserved.

This software is free software licensed under the terms of GPLv3. See COPYING
file that comes with the source code, or http://www.gnu.org/licenses/gpl.txt.
"""

from bottle import request, view, redirect, default_app

from ..lib import downloads
from ..lib.i18n import i18n_path, lazy_gettext as _

__all__ = ('app', 'list_downloads', 'manage_downloads',)

PREFIX = '/downloads'


app = default_app()


@app.get(PREFIX + '/')
@view('downloads', vals={})
def list_downloads():
    """ Render a list of downloaded content """
    # FIXME: The whole process of decrypting signed content is vulnerable to
    # injection of supposedly decrypted zip files. If attacker is able to gain
    # access to filesystem and is able to write a new zip file in the spool
    # directory, the system will treat it as a safe content file. There are
    # currently no mechanisms for invalidating such files.
    decryptables = downloads.get_decryptable()
    extracted, errors = downloads.decrypt_all(decryptables)
    zipballs = downloads.get_zipballs()
    metadata = []
    for z in zipballs:
        meta = downloads.get_metadata(z)
        meta['md5'] = downloads.get_md5_from_path(z)
        metadata.append(meta)
    # FIXME: Log errors
    return dict(metadata=metadata, errors=errors)


@app.post(PREFIX + '/')
@view('downloads_error')  # TODO: Add this view
def manage_downloads():
    """ Manage the downloaded content """
    forms = request.forms
    action = forms.get('action')
    file_list = forms.getall('selection')
    if not action:
        # Bad action
        return {'error': _('Invalid action, please use one of the form '
                           'buttons.')}
    if action == 'add':
        downloads.add_to_archive(file_list)
    if action == 'delete':
        downloads.remove_downloads(file_list)
    redirect(i18n_path('/downloads/'))

