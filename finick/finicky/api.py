from __future__ import print_function
from __future__ import division  # py3 style. division promotes to floating point.
from __future__ import unicode_literals
from __future__ import absolute_import

import glob
import gettext
import locale
import argparse

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
from finicky.session_row_printer import RowPrinterForSessionStart, RowPrinterSessionEndSummary
from finicky.error import FinickError


def prelaunch_checklist_open(calling_filename):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-n", "--no-session",
        help=
        "update the db file, output your todos, but do not start a session. "
        "(this is especially helpful when you need the db txt file to contain "
        "your latest commit hashes, so you can attach a file-comment to one of them.)",
        action="store_true")
    parser.add_argument(
        "-t", "--print-todos",
        nargs=1,
        metavar="TODO_DEBTOR",
        help="output todos of the TODO_DEBTOR, but do not start a session",
        action="store")
    parser.add_argument(
        "commits",
        nargs='*',
        default=[None],
        help=
        'you may list 0 or more commit hashes (separated by whitespace) to '
        'request that these commits (and only these) '
        'be assigned to you for this review session')
    return _prelaunch_checklist(calling_filename, True, parser)


def prelaunch_checklist_close(calling_filename):
    parser = argparse.ArgumentParser()
    return _prelaunch_checklist(calling_filename, False, parser)


def _prelaunch_checklist(calling_filename, is_session_starting, parser):

    # make sure this is called as finick/start.py (use os.sep). this way we can count on CWD for finding config
    # config integrity check. (older than start of session to prevent mid-session reconfig).
    # are we on the right branch? (check this when False==is_session_starting. on start we will check out the branch)
    # do a git-whoami and make sure we have an email

    args = parser.parse_args()

    all_cwd_inis = glob.glob('*ini')

    if len(all_cwd_inis) != 1:
        # eventually we will allow the INI file to be passed as an argument
        raise FinickError(
            "you must have exactly one (and only one) ini file in the CWD")

    return finicky.parse_config.FinickConfig(all_cwd_inis[0], args)


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

    # the config will compute whether the debtor is the reviewer or otherwise, based on settings/flags:
    todos_n_pleases = db_handle.generate_todos_for(finick_config.todo_debtor)

    wrapper_helper = RowPrinterForSessionStart(finick_config, assignments,
                                               todos_n_pleases)
    return wrapper_helper


def finick_close_session_nothing_to_review(finick_config, db_handle):

    # when this is called there shouldn't be any NOW rows. no NOW markers to remove, right?
    db_handle.flush_back_to_disk()

    finicky.gitting.git_perform_maintenance_commit(finick_config)


def finick_open_session(finick_config, db_handle):

    if finick_config.opt_nosession:
        raise FinickError(
            'Call to api open_session despite the no-session flag being set.')

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
    summary_map, work_count = db_handle.merge_completed_assignments(
        assign_fhandle)

    # mark ##__forefront__## position in reviews file

    db_handle.flush_back_to_disk()

    # we can leave the on-disk assignments file alone. user might want to keep it.

    if work_count < 1:
        raise FinickError(
            'Session-end failed. (see possible remedies below).\n\n' +
            'Details: merging your assignment file resulted in ZERO ' +
            'changes to the db_file.' +
            '\n\nPossible remedies: if you completed ZERO reviews, ' +
            'you should \'abort\' the session instead of trying to ' +
            '\'end\' it.  Run the abort command instead.\n\t' +
            'If you did complete some reviews, then the \'' +
            finick_config.str_finish +
            '\' might have already succeeded. Review your git logs ' +
            'manually, and either use \'git push\' or \'git reset\' ' +
            'to manually put the repo into the correct state.')
    else:
        # in addition to the summary_map, we must prepare a TODO-map for the printer, too:
        prior_todo_map = {}
        for committer in summary_map:
            prior_todo_map[committer] = db_handle.generate_todos_for(committer)

        # prepare email messages. (do this BEFORE the final git commands, so we have this even if git fails)
        summary_printer = RowPrinterSessionEndSummary(
            finick_config, summary_map, prior_todo_map)
        summary_printer.prepare_email_messages()

        # send email (email to remind todo items. todo items past certain date?)
        sessionend_email_body = 'session ended'

        # commit session-end message, push all to origin reviews branch
        finicky.gitting.git_perform_session_completion_commit(finick_config,
                                                              work_count)

        # now that stuff did indeed get pushed, send the emails.
        # (if git commands failed, the user can fall back on files saved during prepare_email_messages)
        summary_printer.send_prepared_email_messages()

        # push whatever possible to zero branch


def finick_abort_current_assignments(finick_config, db_handle):

    db_handle.abort_current_assignments(finick_config)

    db_handle.flush_back_to_disk()

    # we can leave the on-disk assignments file alone. user might want to keep it.

    # commit session-abort message, push all to origin reviews branch
    finicky.gitting.git_perform_session_abort_commit(finick_config)
