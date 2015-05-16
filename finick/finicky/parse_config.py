from __future__ import print_function
from __future__ import division  # py3 style. division promotes to floating point.
from __future__ import unicode_literals
from __future__ import absolute_import

try:
    # python 3 name
    import configparser
except ImportError:
    # old name
    import ConfigParser as configparser

from finicky.error import FinickError

import os
from io import open


def AssertType_FinickConfig(o):
    rhs = FinickConfig.dummyinstance()
    incoming_type = str(type(o))
    if type(o) != type(rhs):
        raise FinickError(
            "AssertType_FinickConfig failed. FinickConfig was required, but instead we got: "
            + incoming_type)


class FinickConfig(object):
    def __init__(self, file_location, defaults_only=False):
        self.__is_ok = False

        self.__config = ''
        self.__cfgdir = ''
        self.__branch = ''
        self.__repopath = ''
        self.__purgeweeks = -1
        self.__ourepochstart = 0
        self.__str_start = ''
        self.__str_abort = ''
        self.__str_finish = ''
        self.__str_maint = ''
        self.__verbose = -1
        self.__invoker_eml = ''

        if False == defaults_only:
            self._initialize_from_file(file_location)

    @classmethod
    def dummyinstance(cls):
        return cls('', True)

    def _fail_setter(self, value):
        raise FinickError("FinickConfig objects are immutable")

    def _set_email(self, value):
        # todo: verify it is a valid-looking email
        self.__invoker_eml = value

    # yapf: disable

    is_ok      = property(lambda s : s.__is_ok,         _fail_setter)

    branch     = property(lambda s : s.__branch,        _fail_setter)

    configname = property(lambda s : s.__config,        _fail_setter)

    confdir    = property(lambda s : s.__cfgdir,        _fail_setter)

    repopath   = property(lambda s : s.__repopath,      _fail_setter)

    purgeweeks = property(lambda s : s.__purgeweeks,    _fail_setter)

    startepoch = property(lambda s : s.__ourepochstart, _fail_setter)

    str_start  = property(lambda s : s.__str_start,     _fail_setter)

    str_abort  = property(lambda s : s.__str_abort,     _fail_setter)

    str_finish = property(lambda s : s.__str_finish,    _fail_setter)

    str_maint  = property(lambda s : s.__str_maint,     _fail_setter)

    verbosity  = property(lambda s : s.__verbose,       _fail_setter)

    # email address of the reviewer (the person driving the review session)
    reviewer   = property(lambda s : s.__invoker_eml,   _set_email  )

    # yapf: enable

    def _initialize_from_file(self, file_location):

        cf = configparser.ConfigParser()
        # it is crucial to open with utf-8 for py2/py3 cross-compatibility
        cf.readfp(open(file_location, encoding='utf-8'))

        self.__branch = cf.get('GitReviews', 'MainReviewBranch')
        # on Windows, normpath converts forward slashes to backward slashes:
        self.__repopath = os.path.normpath(cf.get('GitReviews', 'RepoPath'))
        self.__purgeweeks = int(cf.get('GitReviews', 'WeeksTilPurge'))
        self.__ourepochstart = int(cf.get('GitReviews', 'BeginningOfTime'))
        self.__str_start = cf.get('GitReviews', 'CommitStringStartSession')
        self.__str_abort = cf.get('GitReviews', 'CommitStringAbortSession')
        self.__str_finish = cf.get('GitReviews', 'CommitStringFinishSession')
        self.__str_maint = cf.get('GitReviews',
                                  'CommitStringMaintWithoutSession')
        file_basename = os.path.basename(file_location)
        self.__config = os.path.splitext(file_basename)[0]
        location = os.path.dirname(file_location)
        self.__cfgdir = os.path.normpath(location)
        self.__verbose = int(cf.get('GitReviews', 'Verbosity'))

        # todo: we need to sanity check this more thoroughly before setting to true
        self.__is_ok = True
