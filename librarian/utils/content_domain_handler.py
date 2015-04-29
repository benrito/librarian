"""
content_domain_handler.py: Load content based on the requested domain

Copyright 2014-2015, Outernet Inc.
Some rights reserved.

This software is free software licensed under the terms of GPLv3. See COPYING
file that comes with the source code, or http://www.gnu.org/licenses/gpl.txt.
"""

import logging
import urlparse
import functools

from bottle import request, redirect
from bottle_utils.i18n import i18n_url

from ..core.archive import Archive
from . import netutils


def get_content_url(root_url, domain):
    conf = request.app.config
    archive = Archive.setup(conf['librarian.backend'],
                            request.db.main,
                            contentdir=conf['content.contentdir'],
                            spooldir=conf['content.spooldir'],
                            meta_filename=conf['content.metadata'])
    matched_contents = archive.content_for_domain(domain)
    try:
        # as multiple matches are possible, pick the first one
        meta = matched_contents[0]
    except IndexError:
        # invalid content domain
        path = 'content-not-found'
    else:
        base_path = i18n_url('content:reader', content_id=meta.md5)
        path = '{0}?path={1}'.format(base_path, request.path)

    return urlparse.urljoin(root_url, path)


def content_resolver_plugin(root_url, ap_client_ip_range):
    ip_range = netutils.IPv4Range(*ap_client_ip_range)
    log_base = '[CONTENT RESOLVER] '
    pre_resolve = log_base + 'CLIENT: {0} REQUESTED DOMAIN: {1} PATH: {2}'
    post_resolve = log_base + 'REDIRECT TO: {0}'

    def decorator(callback):
        @functools.wraps(callback)
        def wrapper(*args, **kwargs):
            target_host = netutils.get_target_host()
            is_regular_access = target_host in root_url
            if not is_regular_access and request.remote_addr in ip_range:
                logging.info(pre_resolve.format(request.remote_addr,
                                                target_host,
                                                request.fullpath))
                # a content domain was entered(most likely), try to load it
                content_url = get_content_url(root_url, target_host)
                logging.info(post_resolve.format(content_url))
                return redirect(content_url)
            return callback(*args, **kwargs)
        return wrapper
    return decorator
