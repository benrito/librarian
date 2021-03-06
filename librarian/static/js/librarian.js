/**
 * Librarian apps API client
 *
 * Librarian
 * 2014 Outernet Inc
 * Some Rights Reserved
 *
 * This software is free software licensed under the terms of GPLv3. See
 * COPYING file that comes with the source code, or
 * http://www.gnu.org/licenses/gpl.txt.
 */


(function (window, $) {

  $.librarian = {};

  $.librarian.lang = {};

  // Get locale identifier in URL
  $.librarian.lang.getLocale = function () {
    return window.location.pathname.split('/')[1];
  };

  // Prefix a path with locale identifier
  $.librarian.lang.prefix = function(path) {
    var locale = this.getLocale();
    return '/' + locale + path;
  };

  $.librarian.files = {};

  // Get a directory listing or basic file metadata
  $.librarian.files.list = function (path, cb) {
    if (!path || path == '/') { path = '.'; }
    if (path.startsWith('/')) {
      path = path.slice(1);
    }
    var res = $.getJSON(
      $.librarian.lang.prefix('/files/' + path), 
      {f: 'json'}
    );
    res.done(function (data) { cb(data); });
    res.fail(function () { cb(null); });
  };

  $.librarian.files.url = function (path) {
    return $.librarian.lang.prefix('/files/' + path);
  };

}(this, jQuery));
