import mock

# Patch bottle's view decorator
import bottle
bottle.mako_view = bottle.view = lambda x, **kw: lambda y: y

import librarian.routes.content as mod

MOD = 'librarian.routes.content'


@mock.patch(MOD + '.redirect')
@mock.patch(MOD + '.i18n')
@mock.patch('librarian.core.archive.remove_from_archive')
def test_remove(remove_from_archive, i18n, redirect):
    remove_from_archive.return_value = (['foo'], [])
    ret = mod.remove_content('foo')
    remove_from_archive.assert_called_once_with(['foo'])
    assert ret is None
    assert redirect.called


@mock.patch(MOD + '.redirect')
@mock.patch(MOD + '.i18n')
@mock.patch('librarian.core.archive.remove_from_archive')
def test_remove_failed(remove_from_archive, i18n, redirect):
    remove_from_archive.return_value = ([], ['foo'])
    ret = mod.remove_content('foo')
    assert ret == {}
    assert not redirect.called

