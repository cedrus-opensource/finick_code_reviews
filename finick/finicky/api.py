from __future__ import print_function
from __future__ import division  # py3 style. division promotes to floating point.
from __future__ import unicode_literals
from __future__ import absolute_import

import glob
import gettext
import locale

# Set up message catalog access.
# Python-3.4.3//Tools/i18n/pygettext.py finick/finicky/*py *py finick/*py # to generate pot
# The hard-coded path is lame. This is a version 0.0 kind of thing.
# make sure this is called as finick/start.py (use os.sep). this way we can count on CWD for finding locale folder
_t = gettext.translation('finick_code_review', './finick/locale',
                         ['en_US'])  #, fallback=True)
try:
    # for older python 2:
    _ = _t.ugettext
except AttributeError:
    _ = _t.gettext
"""
i probably will want to end up using the INSTALL-based way to get _, from here:
http://www.wefearchange.org/2012/06/the-right-way-to-internationalize-your.html
"""

import finicky.parse_config
from finicky.db_file import DbTextFile, AssertType_DbTextFile
from finicky.session_row_printer import SessionRowPrinter
from finicky.error import FinickError


def prelaunch_checklist_open(calling_filename):
    return _prelaunch_checklist(calling_filename, True)


def prelaunch_checklist_close(calling_filename):
    return _prelaunch_checklist(calling_filename, False)


def _prelaunch_checklist(calling_filename, is_session_starting):

    # make sure this is called as finick/start.py (use os.sep). this way we can count on CWD for finding config
    # config integrity check. (older than start of session to prevent mid-session reconfig).
    # are we on the right branch? (check this when False==is_session_starting. on start we will check out the branch)
    # do a git-whoami and make sure we have an email

    all_cwd_inis = glob.glob('*ini')

    if len(all_cwd_inis) != 1:
        # eventually we will allow the INI file to be passed as an argument
        raise FinickError(
            "you must have exactly one (and only one) ini file in the CWD")

    return finicky.parse_config.FinickConfig(all_cwd_inis[0])


def finick_db_integrity_check_open(finick_config):

    return _db_integrity_check(finick_config, True)


def finick_db_integrity_check_close(finick_config):

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


def finick_preopen_session(finick_config, db_handle):

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


def finick_close_session_nothing_to_review(finick_config, db_handle):

    # when this is called there shouldn't be any NOW rows. no NOW markers to remove, right?
    db_handle.flush_back_to_disk()

    finicky.gitting.git_perform_maintenance_commit(finick_config)


def finick_open_session(finick_config, db_handle):

    # do this AFTER generating assignments, so the 'NOW' markers can show up
    db_handle.flush_back_to_disk()

    finicky.gitting.git_perform_sessionstart_commit(finick_config)


def finick_db_merge_with_completed_assignments(finick_config, db_handle):

    # assignments file integrity check.
    # we need to reverse the rows, so we try any requested 'git revert' from newest to oldest
    assign_fhandle = DbTextFile.create_from_file_rows_reversed(
        finick_config, finick_config.get_assign_file_fullname_fullpath())

    if not assign_fhandle.is_ok:
        raise FinickError('Failed to parse the completed assignments file.')

    # after the (open-and-read-db_file,open-and-read-assignfile) stuff, between then and adding new revert-commits,
    # we need to account for any commits that happened in the interim.
    # (we know AT LEAST ONE commit happened: the CommitStringStartSession commit)
    db_handle.add_new_commits()

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


def finick_abort_current_assignments(finick_config, db_handle):

    db_handle.abort_current_assignments(finick_config)

    db_handle.flush_back_to_disk()

    # we can leave the on-disk assignments file alone. user might want to keep it.

    # commit session-abort message, push all to origin reviews branch
    finicky.gitting.git_perform_session_abort_commit(finick_config)