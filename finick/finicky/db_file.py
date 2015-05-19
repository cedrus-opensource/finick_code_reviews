from __future__ import print_function
from __future__ import division  # py3 style. division promotes to floating point.
from __future__ import unicode_literals
from __future__ import absolute_import

import finicky.gitting
from finicky.db_row import DbRow
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
    def create_from_file(cls, finick_config, is_session_starting):
        return cls(False, finick_config, is_session_starting)

    @classmethod
    def dummyinstance(cls):
        return cls(True)

    def __init__(self, is_dummy,
                 finick_config=None,
                 is_session_starting=False):

        # if some on a team need to keep older file format, this will need to be configurable:
        self.__CURR_FILE_VER = 0
        # the prefix before 'finick_code_reviews' is to make sure this would be INVALID if read as an email address
        self.__CURR_VERSION_STRING = '@:..finick_code_reviews db_file v0.00'

        self.__file_location = ''
        self.__finick_config = None
        self.__is_ok = False
        self.__version_from_fileread = -1  # later code RELIES on this -1 as a flag
        self.__rows = []

        if False == is_dummy:
            self._initialize_from_file(finick_config, is_session_starting)
            pass

    def _fail_setter(self, value):
        raise FinickError(
            "The value you are trying to assign to in DbTextFile is read-only.")

    is_ok = property(lambda s: s.__is_ok, _fail_setter)

    def _initialize_from_file(self, finick_config, is_session_starting):

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
            # file could be empty. that would mean a brand-new file.
            # ignore blank lines. (blank after trimming whitespace from both ends).
            # the first line should be the version line. otherwise, assume 0.00 (or empty file).
            # a maximum of one consecutive line can START with ';' and be a file comment.
            # file-comments (;) are treated as associated with the row below the comment.
            # a maximum of one consecutive line can start with '##__forefront__##' and a date.
            # forefront markers mark the commit from the PREVIOUS row.

            try:
                with open(expected_db, encoding='utf-8') as f:
                    # it opened without exception, so store this location for later file-save operations:
                    self.__file_location = expected_db

                    file_comments_waiting = ''

                    for line in f:
                        #print(_('someline')) # bogus test line. was part of gettext testing
                        linetext = line.rstrip().lstrip()
                        if len(linetext) == 0:
                            continue

                        is_comment = linetext.startswith(';')
                        is_versioninfo = linetext.startswith(
                            '@:..finick_code_reviews')
                        is_forefrontmark = linetext.startswith(
                            '##__forefront__##')

                        if is_versioninfo:
                            if self.__version_from_fileread != -1:
                                raise FinickError(
                                    'Once we set the value version_from_fileread,'
                                    ' no file lines should match is_versioninfo again!')

                            self._parse_version_from_fileread(linetext)

                        elif is_comment:
                            if len(file_comments_waiting) > 0:
                                raise FinickError(
                                    'Found another file-comment when we already had one pending.'
                                    ' Only a maximum of one consecutive file-comment line is allowed.')

                            file_comments_waiting = linetext

                        elif is_forefrontmark:
                            if len(self.__rows) == 0:
                                print(
                                    'Warning: found a forefront marker without any preceding row to attach it to.')
                            else:
                                self.__rows[len(self.__rows) -
                                            1].set_forefront_marker(linetext)

                        else:
                            if self.__version_from_fileread == -1:
                                print(
                                    'Warning: no version string before content. Assuming version 0.00')
                                self.__version_from_fileread = 0

                            drow = DbRow.create_from_string(
                                linetext, file_comments_waiting)
                            file_comments_waiting = ''
                            if is_session_starting and drow.row_type == drow.TYPE_NOW:
                                raise FinickError(
                                    'The session is not yet fully initialized. Therefore, we cannot have \'NOW\' rows.'
                                    'Bad row: ' + linetext)

                            self.__rows.append(drow)

                    # if we made it this far without exceptions:
                    is_ok = True

            except FinickError:
                # here is where we intend to catch our own parsing violations from db_row
                raise  # re-throw the same exception that got us here in the first place

            except IOError:
                configfile = finick_config.confdir + os.sep + finick_config.configname
                err_msg = 'Missing or unreadable DB file. (Create an empty file for first use.) '
                err_msg += 'While using config \'' + configfile + '\', you must have the DB file \'' + expected_db + '\''
                raise FinickError(err_msg)

        if len(self.__rows) == 0:
            # if we got here with no exceptions, but the __rows list is empty,
            # then we must have gotten an empty (fresh new) file.
            # in that case, we may as well say the file is in 'our version' format:
            self.__version_from_fileread = self.__CURR_FILE_VER

        self.__is_ok = is_ok
        # since all went well, store the config for use by other member functions later:
        self.__finick_config = finick_config

    def _parse_version_from_fileread(self, linetext):
        # this is the only thing we can handle in our 0.0 version:
        if linetext == self.__CURR_VERSION_STRING:
            self.__version_from_fileread = 0
        else:
            err_msg = str('Current version of finick db_file (' +
                          str(self.__CURR_FILE_VER) +
                          ') cannot parse file version: ' + linetext)
            raise FinickError(err_msg)

    def flush_back_to_disk(self):

        # upgrade file format if needed. (if some on a team need the old format, this requires configuration options)
        if self.__version_from_fileread < self.__CURR_FILE_VER:
            raise FinickError(
                'It seems we incremented __CURR_FILE_VER without a plan to upgrade older files!'
                ' Add implementation here, please!')

        # mode 'w' will TRUNCATE the file
        text_file = open(self.__file_location, encoding='utf-8', mode='w')

        # (first line should always be file version info).
        text_file.write(self.__CURR_VERSION_STRING + '\n')

        for r in self.__rows:
            r.write_to_diskfile(text_file)

        text_file.close()

    def purge_older_reviewed_commits(self):

        # TODO. will use WeeksTilPurge setting from the ini.
        # (however, anything NEWER than the 'forefront' must be kept no matter what)
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
    # first line in DB file should be file version info
    return _db_integrity_check(finick_config, False)


def _db_integrity_check(finick_config, is_session_starting):

    db_handle = DbTextFile.create_from_file(finick_config, is_session_starting)

    if db_handle.is_ok:
        return db_handle
    else:
        return None


def db_open_session(finick_config, db_handle):

    finicky.parse_config.AssertType_FinickConfig(finick_config)
    AssertType_DbTextFile(db_handle)

    # if we are starting one session, there must not be any other session in progress (even from other INI file) [job of git_establish_session_readiness]

    db_handle.purge_older_reviewed_commits()
    db_handle.add_new_commits()

    assignments = db_handle.generate_assignments_for_this_session()

    todos = db_handle.generate_todos_for_this_session()

    # do this AFTER generating assignments, so the 'NOW' markers can show up
    db_handle.flush_back_to_disk()

    return assignments, todos
