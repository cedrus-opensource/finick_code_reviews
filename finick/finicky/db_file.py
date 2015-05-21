from __future__ import print_function
from __future__ import division  # py3 style. division promotes to floating point.
from __future__ import unicode_literals
from __future__ import absolute_import

import finicky.gitting
from finicky.db_row import DbRow
from finicky.session_row_printer import SessionRowPrinter
from finicky.error import FinickError
from finicky.basics import _

import os
from io import open
import copy


class _DbRowsCollection(object):
    def __init__(self):
        self.__rows = []
        self.__lookupmap = {}
        self.__lookup_size_10 = {}

    def is_empty(self):
        return len(self.__rows) == 0

    def mark_last_row_as_forefront(self, linetext):
        self.__rows[len(self.__rows) - 1].set_forefront_marker(linetext)

    def append_drow(self, drow):
        # todo: assert type DbRow
        self.__rows.append(drow)
        self.__lookupmap[drow.commithash] = drow
        self.__lookup_size_10[drow.commithash[0:10]] = drow

    def prepend_drow(self, drow):
        # todo: assert type DbRow
        self.__rows.insert(0, drow)
        self.__lookupmap[drow.commithash] = drow
        self.__lookup_size_10[drow.commithash[0:10]] = drow

    def write_to_diskfile(self, text_file):
        # the_file is expected to be a TextIOBase (from io)
        for r in self.__rows:
            r.write_to_diskfile(text_file)

    def contains_this_commit(self, commithash_str):
        return commithash_str in self.__lookupmap

    def _configured_strategy_says_to_assign_this_row(self, finick_config,
                                                     dbrow):
        # todo: implement a variety of assignment strategies/policies

        # for now, assign anything that wasn't authored by the reviewer:
        return dbrow.committer != finick_config.reviewer

    def find_then_mark_then_return_assignments(self, finick_config):
        # changing assigned items from TYPE_WAIT to TYPE_NOW
        results = []

        for r in self.__rows:
            if r.row_type == r.TYPE_WAIT:
                if self._configured_strategy_says_to_assign_this_row(
                    finick_config, r):
                    r.assign_for_current_review_session(finick_config.reviewer)
                    # make a deep copy, so that nothing that edits assignments can edit our __rows:
                    results.append(copy.deepcopy(r))

        return results

    def find_then_reverse_assignments(self, finick_config):
        for r in self.__rows:
            if r.row_type == r.TYPE_NOW:
                r.cancel_assignment_for_current_review_session()

    def find_todos_and_please_requests(self, email_of_debtor):
        # we need to care about TYPE_TODO and TYPE_PLS.
        # find rows of those types where the *committer* is the same as current session driver
        rough_results = []
        cancelled_hashes = []

        for r in self.__rows:
            if r.row_type == r.TYPE_TODO or r.row_type == r.TYPE_PLS:
                for_me = r.committer == email_of_debtor
                if for_me:
                    rough_results.append(copy.deepcopy(r))

            elif r.row_type == r.TYPE_FIXD:
                # each todo ref should be length 10
                cancelled_hashes += r.todo_refs

        results = []

        for r in rough_results:
            # we expect the todo refs to always be length 10
            if r.commithash[0:10] not in cancelled_hashes:
                results.append(r)

        return results

    def add_new_commits(self, incoming_rows):
        # incoming_rows is a list of DbRow objects.
        # IMPORTANT: 'incoming_rows' is NOT JUST new content. it is EXPECTED to overlap with current content in __rows

        if self.is_empty():
            # we must have initially read from an empty file, so now we incorporate *all* incoming commits
            for ir in incoming_rows:
                self.append_drow(ir)
        else:
            # work backwards through incoming_rows, looking for one that overlaps with __rows.
            # if we never find any overlap, report an error. (conflict between WeeksTilPurge, BeginningOfTime, or something?)
            # once we find an overlap, sanity-check that all further incoming_rows overlap with __rows. otherwise report
            # a sanity-check failure.
            # finally, append the NON-overlapping stuff from incoming_rows, preserving order.

            newrows_i = len(incoming_rows) - 1
            matched_at = -1

            # IMPORTANT: 'incoming_rows' is NOT JUST new content. it
            # is EXPECTED to overlap with current content in __rows
            while newrows_i >= 0:
                if self.__rows[len(self.__rows) -
                               1].commithash == incoming_rows[newrows_i].commithash:
                    matched_at = newrows_i
                    break

                newrows_i -= 1

            if matched_at == -1:
                raise FinickError(
                    'Unable to find where incoming commits line up with existing commit '
                    + self.__rows[len(self.__rows) - 1].commithash)

            # keep going, for further sanity check:
            while newrows_i >= 0:

                if not self.contains_this_commit(
                    incoming_rows[newrows_i].commithash):
                    raise FinickError(
                        'Incoming commits contain commit hashes not known to our prior history! Example: '
                        + incoming_rows[newrows_i].commithash)

                newrows_i -= 1

            # we made it through sanity checking. now go back to the overlap spot:
            newrows_i = matched_at + 1
            while newrows_i < len(incoming_rows):
                self.append_drow(incoming_rows[newrows_i])
                newrows_i += 1

    def short_commithash_is_known_in_collection(self, commithash_str):
        if len(commithash_str) != 10:
            raise FinickError(
                'The short_commithash lookup function only takes length-10 strings.')

        return commithash_str in self.__lookup_size_10

    def merge_completed_assignments(self, assign_file, finick_config):
        AssertType_DbTextFile(assign_file)

        assign_rows = assign_file._DbTextFile__rowcollection._DbRowsCollection__rows

        work_count = 0

        # REMEMBER! we read in the completed assignments file backwards! newest commits first!
        for ar in assign_rows:
            try:
                our_row = self.__lookupmap[ar.commithash]
            except KeyError:
                raise FinickError(
                    'In assignment file, unrecognized commit hash: ' +
                    ar.commithash)

            # now we work with 'our_row' and 'ar'

            # if 'ar' is still in row_type 'NOW', then put it back to 'WAIT'
            # other valid values for ar type: OK, FIXD, TODO, PLS, OOPS
            if ar.row_type != ar.TYPE_OOPS:
                work_count += our_row.merge_with_completed_assignment_all_cases_except_OOPS(
                    ar, self.short_commithash_is_known_in_collection)

            elif ar.row_type == ar.TYPE_OOPS:
                # OOPS is the tricky case. we try a clean revert. if it fails, we use TODO instead.
                # returns the commit hash of the revert-commit if it succeeds, else ''

                # make sure we have a comment BEFORE we invoke any git commands:
                ar.throw_exception_if_bad_actioncomment()

                reverthash, reason_to_hide = finicky.gitting.git_best_effort_to_commit_a_revert(
                    finick_config, ar.commithash, ar.comment)

                # the merge function will decide (based on reverthash) whether to merge as TODO or OOPS
                new_row = our_row.merge_OOPS_row(ar, reverthash,
                                                 reason_to_hide,
                                                 finick_config.reviewer)

                if None != new_row:
                    # if the merge returned a new row, then add it
                    self.append_drow(new_row)

                # either way (as OOPS or as TODO), this was one review:
                work_count += 1

            else:
                raise FinickError(
                    'Invalid incoming assignment row type while trying to merge completed assignments.')

        return work_count


def AssertType_DbTextFile(o):
    rhs = DbTextFile.dummyinstance()
    incoming_type = str(type(o))
    if type(o) != type(rhs):
        raise FinickError(
            "AssertType_DbTextFile failed. DbTextFile was required, but instead we got: "
            + incoming_type)


class DbTextFile(object):
    @classmethod
    def create_from_file(cls, finick_config, filename_w_fullpath,
                         is_session_starting):
        return cls(False, finick_config, filename_w_fullpath,
                   is_session_starting)

    @classmethod
    def create_from_file_rows_reversed(cls, finick_config,
                                       filename_w_fullpath):
        return cls(False, finick_config, filename_w_fullpath,
                   is_session_starting=False,
                   reverse_the_rows=True)

    @classmethod
    def dummyinstance(cls):
        return cls(True)

    def __init__(self, is_dummy,
                 finick_config=None,
                 filename_w_fullpath='',
                 is_session_starting=False,
                 reverse_the_rows=False):

        # if some on a team need to keep older file format, this will need to be configurable:
        self.__CURR_FILE_VER = 0
        # the prefix before 'finick_code_reviews' is to make sure this would be INVALID if read as an email address
        self.__CURR_VERSION_STRING = '@:..finick_code_reviews db_file v0.00'

        self.__file_location = ''
        self.__finick_config = None
        self.__is_ok = False
        self.__version_from_fileread = -1  # later code RELIES on this -1 as a flag
        self.__rowcollection = _DbRowsCollection()

        if False == is_dummy:
            self._initialize_from_file(finick_config, filename_w_fullpath,
                                       is_session_starting, reverse_the_rows)
            pass

    def _fail_setter(self, value):
        raise FinickError(
            "The value you are trying to assign to in DbTextFile is read-only.")

    is_ok = property(lambda s: s.__is_ok, _fail_setter)

    def _initialize_from_file(self, finick_config, filename_w_fullpath,
                              is_session_starting, reverse_the_rows):

        finicky.parse_config.AssertType_FinickConfig(finick_config)

        # before we check the content of the file, we should check whether it is known (committed) to git

        expected_db = filename_w_fullpath

        db_found = os.path.isfile(expected_db)
        db_commit_status_ok = False
        is_ok = False

        if not db_found:
            print(expected_db, 'not found')
        else:
            is_committed = finicky.gitting.git_repo_contains_committed_file(
                finick_config, os.path.abspath(expected_db))
            if filename_w_fullpath == finick_config.get_assign_file_fullname_fullpath(
            ):
                # the assignment file should be git-ignored. not committed:
                db_commit_status_ok = not is_committed
            else:
                db_commit_status_ok = is_committed

        if not db_commit_status_ok:
            print(expected_db, 'not committed')

        if db_found and db_commit_status_ok:
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
                            if self.__rowcollection.is_empty():
                                print(
                                    'Warning: found a forefront marker without any preceding row to attach it to.')
                            else:
                                self.__rowcollection.mark_last_row_as_forefront(
                                    linetext)

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

                            if reverse_the_rows:
                                self.__rowcollection.prepend_drow(drow)
                            else:
                                self.__rowcollection.append_drow(drow)

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

        if self.__rowcollection.is_empty():
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

        self.__rowcollection.write_to_diskfile(text_file)

        text_file.close()

    def purge_older_reviewed_commits(self):

        # TODO. will use WeeksTilPurge setting from the ini.
        # (however, anything NEWER than the 'forefront' must be kept no matter what)
        pass

    def add_new_commits(self):

        # self.__rowcollection is a list holding DbRow objects
        if self.__version_from_fileread == -1:
            raise FinickError(
                'You are expected to read and parse a file before calling add_new_commits')

        # nice-to-have: pass in something more recent (some appropriate commit hash), so that
        # git log doesn't have to go back to the 'BeginningOfTime' each time.
        # the commit must be chosen carefully. when we have 2+ diverging paths in the git
        # history that have not yet merged back together, we do NOT want to pick a commit
        # from during that diverged part of history.
        commits = finicky.gitting.git_retrieve_history(self.__finick_config)

        incoming_rows = []

        for c in commits:
            drow = DbRow.create_from_gitting_tuple(c)
            incoming_rows.append(drow)

        # we are TRANSFERING ownership of incoming_rows. do NOT use
        # incoming_rows further after passing it to __rowcollection
        self.__rowcollection.add_new_commits(incoming_rows)

        incoming_rows = None  # we MUST not mutate the rows from here onward!

    def abort_current_assignments(self, finick_config):

        return self.__rowcollection.find_then_reverse_assignments(finick_config)

    def generate_assignments_for_this_session(self, finick_config):

        # changing assigned items from TYPE_WAIT to TYPE_NOW
        return self.__rowcollection.find_then_mark_then_return_assignments(
            finick_config)

    def generate_todos_for_this_session(self, finick_config):

        # we need to care about TYPE_TODO and TYPE_PLS.
        # find rows of those types where the *committer* is the same as current session driver
        return self.__rowcollection.find_todos_and_please_requests(
            finick_config.reviewer)

    def merge_completed_assignments(self, assign_file):

        # note: the rows from assignments might be mutated after this call:
        return self.__rowcollection.merge_completed_assignments(
            assign_file, self.__finick_config)


def db_integrity_check_open(finick_config):

    return _db_integrity_check(finick_config, True)


def db_integrity_check_close(finick_config):

    # reviews file should now be properly upgraded already.
    # first line in DB file should be file version info
    return _db_integrity_check(finick_config, False)


def _db_integrity_check(finick_config, is_session_starting):

    db_handle = DbTextFile.create_from_file(
        finick_config, finick_config.get_db_file_fullname_fullpath(),
        is_session_starting)

    if db_handle.is_ok:
        return db_handle
    else:
        return None


def db_preopen_session(finick_config, db_handle):

    finicky.parse_config.AssertType_FinickConfig(finick_config)
    AssertType_DbTextFile(db_handle)

    # if we are starting one session, there must not be any other session in progress (even from other INI file) [job of git_establish_session_readiness_start]

    db_handle.purge_older_reviewed_commits()
    db_handle.add_new_commits()

    assignments = db_handle.generate_assignments_for_this_session(finick_config)

    todos_n_pleases = db_handle.generate_todos_for_this_session(finick_config)

    wrapper_helper = SessionRowPrinter(finick_config, assignments,
                                       todos_n_pleases)
    return wrapper_helper


def db_close_session_nothing_to_review(finick_config, db_handle):

    # when this is called there shouldn't be any NOW rows. no NOW markers to remove, right?
    db_handle.flush_back_to_disk()

    finicky.gitting.git_perform_maintenance_commit(finick_config)


def db_open_session(finick_config, db_handle):

    # do this AFTER generating assignments, so the 'NOW' markers can show up
    db_handle.flush_back_to_disk()

    finicky.gitting.git_perform_sessionstart_commit(finick_config)


def db_merge_with_completed_assignments(finick_config, db_handle):

    # assignments file integrity check.
    # we need to reverse the rows, so we try any requested 'git revert' from newest to oldest
    assign_fhandle = DbTextFile.create_from_file_rows_reversed(
        finick_config, finick_config.get_assign_file_fullname_fullpath())

    if not assign_fhandle.is_ok:
        raise FinickError('Failed to parse the completed assignments file.')

    # note: the rows from assignments might be mutated after this call:
    work_count = db_handle.merge_completed_assignments(assign_fhandle)

    # mark ##__forefront__## position in reviews file

    db_handle.flush_back_to_disk()

    # we can leave the on-disk assignments file alone. user might want to keep it.

    # commit session-end message, push all to origin reviews branch
    finicky.gitting.git_perform_session_completion_commit(finick_config,
                                                          work_count)

    # push whatever possible to zero branch
    # send email (email to remind todo items. todo items past certain date?)


def db_abort_current_assignments(finick_config, db_handle):

    db_handle.abort_current_assignments(finick_config)

    db_handle.flush_back_to_disk()

    # we can leave the on-disk assignments file alone. user might want to keep it.

    # commit session-abort message, push all to origin reviews branch
    finicky.gitting.git_perform_session_abort_commit(finick_config)
