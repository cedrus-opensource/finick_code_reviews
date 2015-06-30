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
    def __init__(self, file_location, parsed_args, defaults_only=False):
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
        self.__str_rvrt = ''
        self.__verbose = -1
        self.__invoker_eml = ''
        self.__only_maint = False
        self.__requests = []
        self.__mailserver = ''
        self.__mailport = 0
        self.__maillogin = ''
        self.__mailpword = ''

        if not parsed_args is None:
            self._process_args(parsed_args)

        if False == defaults_only:
            self._initialize_from_file(file_location)
            self._read_userfile_settings()
            # todo: we need to sanity check this more thoroughly before setting to true
            self.__is_ok = True

    @classmethod
    def dummyinstance(cls):
        return cls('', None, True)

    def _fail_setter(self, value):
        raise FinickError("FinickConfig objects are immutable")

    def _set_email(self, value):
        # todo: verify it is a valid-looking email
        self.__invoker_eml = value

    # yapf: disable
    def contains_a_configurable_tool_string(self, the_string):
        if (self.__str_start in the_string or
            self.__str_abort in the_string or
            self.__str_finish in the_string or
            self.__str_maint in the_string or
            self.__str_rvrt in the_string):
            return True
        else:
            return False
    # yapf: enable

    def get_all_commit_strings(self):
        return [self.__str_start, self.__str_abort, self.__str_finish,
                self.__str_maint, self.__str_rvrt]


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

    str_rvrt   = property(lambda s : s.__str_rvrt,      _fail_setter)

    verbosity  = property(lambda s : s.__verbose,       _fail_setter)

    mailserver = property(lambda s : s.__mailserver,    _fail_setter)

    mailport   = property(lambda s : s.__mailport,      _fail_setter)

    maillogin  = property(lambda s : s.__maillogin,     _fail_setter)

    mailpword  = property(lambda s : s.__mailpword,     _fail_setter)

    # email address of the reviewer (the person driving the review session)
    reviewer   = property(lambda s : s.__invoker_eml,   _set_email  )

    opt_nosession = property(lambda s : s.__only_maint, _fail_setter)

    opt_requests  = property(lambda s : s.__requests,   _fail_setter)

    # yapf: enable

    def _get_file_fullname_fullpath_by_our_name(self, prefix_string):
        result = prefix_string + '.'
        result += self.configname
        result += '.txt'
        result = self.confdir + os.sep + result

        return result

    def get_db_file_fullname_fullpath(self):
        return self.confdir + os.sep + self.configname + '.txt'

    def get_todos_file_fullname_fullpath(self):
        return self._get_file_fullname_fullpath_by_our_name('todos')

    def get_assign_file_fullname_fullpath(self):
        return self._get_file_fullname_fullpath_by_our_name('assignments')

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
        self.__str_rvrt = cf.get('GitReviews', 'CommitStringAutoRevertOops')
        file_basename = os.path.basename(file_location)
        self.__config = os.path.splitext(file_basename)[0]
        location = os.path.dirname(file_location)
        self.__cfgdir = os.path.normpath(location)
        self.__verbose = int(cf.get('GitReviews', 'Verbosity'))

    def _read_userfile_settings(self):

        appdata_or_empty = os.getenv('APPDATA', '')

        appdata_ini_loc = os.path.normpath(
            appdata_or_empty + os.sep + 'finickmail.ini')
        # on unix-like platforms, use the leading dot (.) to make a hidden file:
        tilde_ini_loc = os.path.normpath(
            os.path.expanduser('~') + os.sep + '.finickmail.ini')

        required_loc = '\'' + tilde_ini_loc + '\''

        if appdata_or_empty != '':
            required_loc = 'either \'' + appdata_ini_loc + '\' or else ' + required_loc

        appdata_item_found = os.path.isfile(appdata_ini_loc)
        tilde_item_found = os.path.isfile(tilde_ini_loc)

        cf = configparser.ConfigParser()

        if not (appdata_item_found or tilde_item_found):
            raise FinickError(
                'User-data ini file missing. We require this ' +
                'secondary ini file (which must reside OUTSIDE ' +
                'the directory of the git-repo under review) ' +
                'for email smtp settings. Put the file here, please: ' +
                required_loc)

        elif appdata_item_found:
            # it is crucial to open with utf-8 for py2/py3 cross-compatibility
            cf.readfp(open(appdata_ini_loc, encoding='utf-8'))

        elif tilde_item_found:
            # it is crucial to open with utf-8 for py2/py3 cross-compatibility
            cf.readfp(open(tilde_ini_loc, encoding='utf-8'))

        else:
            print(
                'We should NEVER execute this line. Did our boolean logic in this if/elif/elif get messed up?')

        self.__mailserver = cf.get('FinickMail', 'MailServerString')
        self.__mailport = int(cf.get('FinickMail', 'MailPortInteger'))
        self.__maillogin = cf.get('FinickMail', 'MailAccountLoginName')
        self.__mailpword = cf.get('FinickMail', 'MailAccountPword')

    def _process_args(self, parsed_args):

        try:
            self.__only_maint = (parsed_args.no_session == True)
        except AttributeError:
            self.__only_maint = False

        try:
            if len(parsed_args.commits) > 0 and parsed_args.commits[0] is None:
                # this means that no commit-requests (requested assignments) were given at the command line.
                pass
            else:
                if len(parsed_args.commits) < 1:
                    raise FinickError(
                        'Command-line argument for commits requested was turned into an empty list.')

                if self.__only_maint:
                    raise FinickError(
                        'You cannot both use the \'-n\' flag and list requested commits (for a session) at the same time.')

                self.__requests = parsed_args.commits

        except AttributeError:
            self.__requests = []
