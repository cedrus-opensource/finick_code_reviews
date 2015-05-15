from __future__ import print_function
from __future__ import division  # py3 style. division promotes to floating point.
from __future__ import unicode_literals
from __future__ import absolute_import

import finicky.gitting
from finicky.error import FinickError
from finicky.basics import _

import os
from io import open


def AssertType_DbTextFile(o):
    rhs = DbTextFile.dummyinstance()
    incoming_type = str(type(o))
    if type(o) != type(rhs):
        raise FinickError(
            "AssertType_DbTextFile failed. DbTextFile was required, but instead we got: "
            + incoming_type)


class DbTextFile(object):
    @classmethod
    def create_from_file(cls, finick_config):
        return cls(False, finick_config)

    @classmethod
    def dummyinstance(cls):
        return cls(True)

    def __init__(self, is_dummy, finick_config=None):

        # if some on a team need to keep older file format, this will need to be configurable:
        self.__CURR_FILE_VER = 0

        self.__finick_config = None
        self.__is_ok = False
        self.__version_from_fileread = -1

        if False == is_dummy:
            self._initialize_from_file(finick_config)
            pass

    def _fail_setter(self, value):
        raise FinickError(
            "The value you are trying to assign to in DbTextFile is read-only.")

    is_ok = property(lambda s: s.__is_ok, _fail_setter)

    def _initialize_from_file(self, finick_config):

        finicky.parse_config.AssertType_FinickConfig(finick_config)

        # before we check the content of the file, we should check whether it is known (committed) to git

        expected_db = finick_config.confdir + os.sep + finick_config.configname + '.txt'

        db_found = os.path.isfile(expected_db)
        db_committed = False
        is_ok = False

        if not db_found:
            print(expected_db, 'not found')
        else:
            db_committed = finicky.gitting.git_repo_contains_committed_file(
                finick_config, os.path.abspath(expected_db))

        if not db_committed:
            print(expected_db, 'not committed')

        if db_found and db_committed:
            try:
                with open(expected_db, encoding='utf-8') as f:
                    for line in f:
                        print(_('someline'))

            except:
                configfile = finick_config.confdir + os.sep + finick_config.configname
                err_msg = 'Missing or unreadable DB file. (Create an empty file for first use.) '
                err_msg += 'While using config \'' + configfile + '\', you must have the DB file \'' + expected_db + '\''
                raise FinickError(err_msg)

        self.__is_ok = is_ok
        # since all went well, store the config for use by other member functions later:
        self.__finick_config = finick_config

    def flush_back_to_disk(self):

        # upgrade file format if needed. (if some on a team need the old format, this requires configuration options)

        # (last line should always be file version info).
        pass

    def purge_older_reviewed_commits(self):

        pass

    def add_new_commits(self):

        pass

    def generate_assignments_for_this_session(self):

        # return a tuple of assignments? (undecided what the structure of an assignment is)
        pass

    def generate_todos_for_this_session(self):

        # return a tuple of todos? (undecided what the structure of an todo is)
        pass


def db_integrity_check_open(finick_config):

    return _db_integrity_check(finick_config, True)


def db_integrity_check_close(finick_config):

    # reviews file should now be properly upgraded already.
    # last line in DB file should be file version info
    return _db_integrity_check(finick_config, False)


def _db_integrity_check(finick_config, is_session_starting):

    db_handle = DbTextFile.create_from_file(finick_config)

    if db_handle.is_ok:
        return db_handle
    else:
        return None


def db_open_session(finick_config, db_handle):

    finicky.parse_config.AssertType_FinickConfig(finick_config)
    AssertType_DbTextFile(db_handle)

    print('db open session')

    # if we are starting one session, there must not be any other session in progress (even from other INI file) [job of git_establish_session_readiness]

    db_handle.purge_older_reviewed_commits()
    db_handle.add_new_commits()
    db_handle.flush_back_to_disk()

    assignments = db_handle.generate_assignments_for_this_session()

    todos = db_handle.generate_todos_for_this_session()

    return assignments, todos
