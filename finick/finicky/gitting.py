from __future__ import print_function
from __future__ import division  # py3 style. division promotes to floating point.
from __future__ import unicode_literals
from __future__ import absolute_import

import finicky.parse_config
from finicky.error import FinickError

import subprocess
import datetime
import os
from io import open

_quietness = ''  # empty string means the ABSENCE of the quiet flag. absence means NO suppressed git stderr


def _dec_assign_to_globals(F):
    def wrapper(*args):
        finick_config = args[0]
        finicky.parse_config.AssertType_FinickConfig(finick_config)

        if finick_config.verbosity >= 1:
            finicky.gitting._quietness = ' '  # verbosity is ENABLED. we do not use the quiet flag
        else:
            finicky.gitting._quietness = ' -q '  # verbosity was at ZERO, so apply quietness

        return F(*args)

    return wrapper


def _git_establish_session_readiness(finick_config, is_session_starting):

    finicky.parse_config.AssertType_FinickConfig(finick_config)

    _git_current_user_email(finick_config)

    _git_exec_and_return_stdout(
        'git checkout ' + _quietness + finick_config.branch,
        finick_config.repopath)

    # the next command needs git 1.6.3 or newer, per http://stackoverflow.com/questions/1417957/show-just-the-current-branch-in-git
    results = _git_exec_and_return_stdout('git rev-parse --abbrev-ref HEAD',
                                          finick_config.repopath)

    if results.rstrip() != finick_config.branch:
        raise FinickError(
            "Unable to start code-review session. Could not check out the required git branch.")

    if is_session_starting:
        """
        we might consider adding this to the 'git pull' if submodule actions are causing slow down.

        --[no-]recurse-submodules[=yes|on-demand|no]

           This option controls if new commits of all populated
           submodules should be fetched too (see git-config(1) and
           gitmodules(5)). That might be necessary to get the data
           needed for merging submodule commits, a feature git learned
           in 1.7.3. Notice that the result of a merge will not be
           checked out in the submodule,'git submodule update' has to
           be called afterwards to bring the work tree up to date with
           the merge result.
           """
        _git_exec_and_return_stdout(
            'git pull ' + _quietness + ' origin ' + finick_config.branch,
            finick_config.repopath)

    # if we are starting one session, there must not be any other session in progress (even from other INI file)
    # check for a currently-open, in-progress review session.
    # if one is in progress, our version 0.0 code can give up.
    # eventually, rather than give up, move our local HEAD to just prior/after that session, and start our session there

    # for now, either an exception was thrown, or else all went well:
    return True


@_dec_assign_to_globals
def git_establish_session_readiness_end(finick_config):
    return _git_establish_session_readiness(finick_config,
                                            is_session_starting=False)


@_dec_assign_to_globals
def git_establish_session_readiness_start(finick_config):
    return _git_establish_session_readiness(finick_config,
                                            is_session_starting=True)


@_dec_assign_to_globals
def git_repo_contains_committed_file(finick_config, which_file):

    finicky.parse_config.AssertType_FinickConfig(finick_config)

    # log has this {--ignore-submodules[=<when>]}, but it only matters for showing patches? (diffs)
    # this can be a false positive if the file is on disk, but has been deleted from the repo
    results = _git_exec_and_return_stdout('git log -1 --oneline ' + which_file,
                                          finick_config.repopath)

    problem_01 = 0 == len(results)

    # (addresses the false positive mentioned above)
    # this returns an empty string even if we got a false positive earlier.
    # (we don't use ls-files alone, because it gives a false positive if you staged a file but never committed it)
    results = _git_exec_and_return_stdout('git ls-files ' + which_file,
                                          finick_config.repopath)

    problem_02 = 0 == len(results)

    return not (problem_01 or problem_02)


@_dec_assign_to_globals
def _git_difftree_does_find_content(finick_config, commit_hash_str):

    results = _git_exec_and_return_stdout(
        'git diff-tree --cc --pretty=oneline ' + commit_hash_str,
        finick_config.repopath)

    # we expect the oneline info (on one line), then a blank line, then (optionally) a diff

    #partition returns a 3-tuple containing the part before the
    #separator, the separator itself, and the part after
    oneline_info, separator, tail = results.partition('\n')
    blank_line, separator, tail = tail.partition('\n')
    diff_text, separator, tail = tail.partition('\n')

    we_have_a_diff = not diff_text == ''

    return we_have_a_diff


@_dec_assign_to_globals
def _git_list_submodules(finick_config):

    finicky.parse_config.AssertType_FinickConfig(finick_config)

    submodule_paths = []

    gitmod_file = finick_config.repopath + os.sep + '.gitmodules'

    # not all repositories have submodules. that is ok.
    found = os.path.isfile(gitmod_file)

    if found:
        try:
            with open(gitmod_file, encoding='utf-8') as f:
                # in .gitmodules, can a path have spaces in it??
                # would any of this still work in that case?
                for line in f:
                    sep = 'path = '
                    if sep in line:
                        line_parts = line.split(sep)
                        submodule_paths += [line_parts[1].rstrip()]

        except IOError:
            raise FinickError(
                'IOError while trying to read the .gitmodules file')

    return submodule_paths


@_dec_assign_to_globals
def git_retrieve_history(finick_config):

    finicky.parse_config.AssertType_FinickConfig(finick_config)

    # --date=local shows timestamps in user's local timezone.
    # meaning that the dates are 'translated' to the timezone of the current
    # machine where somebody is running the finick tool. This means
    # that if two people share a repo but are in different time zones,
    # then the times coming out of this log will be DIFFERENT depending
    # on which person runs finick. This needs to be addressed at some point.
    # for now, showing any datetime at all is really just a nicety, and
    # the dates are not used for any logic or decision making
    """
    git format options for commit messages:
    %s: subject
    %b: body
    %B: raw body (unwrapped subject and body)
    """
    """
    so you have an idea about what the git output that is being parsed here looks like raw:

    git log --topo-order --numstat --date=local  --pretty=format:\"commit %H$%ae$%aD$%s\"  --since=1427763600
    (Note: we are no longer using the DOLLAR SIGN for the delim. Now it is char \b)

    commit rrc084e4x88b74rx38e1x4e88db53575ec4cd15d$deva@acmecorp.com$Thu, 14 Jan 1999 13:43:32 -0700$Merge branch 'ABC.0' of github.com:acmecorp/Acmeproject into ABC.0
    commit 8bc1c6xe1750b7bc789x00b8ee619718rc7ecx11$devb@acmecorp.com$Thu, 14 Jan 1999 12:56:43 -0700$Removing the questionable bandaid from the minimal element class, making sublists a subclass of it. Minimal_BBElement is still a work in progress.
    12      2       src/Acmeproject/BBCore/Minimal_BBElement.cpp
    6       2       src/Acmeproject/BBCore/Minimal_BBElement.h
    3       3       src/Acmeproject/BBCore/BBElement.cpp
    7       13      src/Acmeproject/BBCore/BBElement.h

    commit 68xx8809c58c65885791c73ee8x389b8cb79031b$deva@acmecorp.com$Thu, 14 Jan 1999 11:36:03 -0700$Merge branch 'ABC.0' of github.com:acmecorp/Acmeproject into ABC.0
    commit rbb67066151c71979037eecex759rc8c1c00e0xb$deva@acmecorp.com$Thu, 14 Jan 1999 11:35:53 -0700$setting the config value for Verbosity in code_reviews/acmeproject_reviews.ini
    2       1       code_reviews/acmeproject_reviews.ini

    commit 8rbb03dr4x86574e78883ecb4c6x3c7b89d8cc7e$devb@acmecorp.com$Thu, 14 Jan 1999 10:16:02 -0700$Fixing mac builds.
    2       0       src/Acmeproject/BBCore/Minimal_BBElement.h

    commit c4rd1rr8888rb252ecb305d84026168867c8cbbe$devb@acmecorp.com$Thu, 14 Jan 1999 09:06:17 -0700$Another crack at sorting out the headers for mac without actually switching over.
    8       1       src/Acmeproject/BBCore/Minimal_BBElement.h
    0       9       src/Acmeproject/BBCore/BBElement.h

    commit rd90r7007re89x79ed9e8735x61e6457eed947ec$deva@acmecorp.com$Wed, 13 Jan 1999 16:27:27 -0700$Merge branch 'ABC.0' of github.com:acmecorp/Acmeproject into ABC.0
    commit 091rx85drbx79d66399c895d59drc7c0948e7268$devb@acmecorp.com$Wed, 13 Jan 1999 16:20:25 -0700$I think this is what broke mac builds.
    2       0       src/Acmeproject/BBCore/BBElement.h

    """

    SEP_TOKEN = 'commit '
    # warning: knowledge about using '\b\ as the delim is duplicated in db_row.py
    COL_DELIM = '\b'  # note: if a commit message contains this, then beware!

    # do NOT exclude merges! merges often deserve review.
    # see: http://haacked.com/archive/2014/02/21/reviewing-merge-commits/
    # use %aD to guarantee parsing by strptime.
    results = _git_exec_and_return_stdout(
        'git log --topo-order --numstat --date=local  --pretty=format:\"' +
        SEP_TOKEN + '%H' + COL_DELIM + '%ae' + COL_DELIM + '%aD' + COL_DELIM +
        '%s\"  --since=' + str(
            finick_config.startepoch), finick_config.repopath)

    # the first one (results[0]) will still have SEP_TOKEN on the front of it
    results = results.split('\n' + SEP_TOKEN)

    if len(results) > 0:
        empty_result_0 = results[0] == ''
        expected_prefix = results[0].startswith(SEP_TOKEN)
        # either we had an empty result, or else we had better have detected our prefix:
        if not (empty_result_0 or expected_prefix):
            raise FinickError(
                'Assumption violated. why doesn\'t this start with SEP_TOKEN?')

        if empty_result_0:
            del results[0]  # prevent us from looping over results
        else:
            results[0] = results[0].replace(SEP_TOKEN, '', 1)

    list_of_subs = _git_list_submodules(finick_config)
    # there are TABS on the next line. it matches git output.
    sub_exclusions = ['1\t1\t' + s for s in list_of_subs]

    list_of_tuples = []

    for each_commit in results:
        #partition returns a 3-tuple containing the part before the
        #separator, the separator itself, and the part after
        commit_pretty, separator, numstat_lines = each_commit.partition('\n')

        commit_is_hidden = False
        reason_to_hide = ''

        nonempty_lines = 0
        submodule_lines = 0
        numstat_lines = numstat_lines.split('\n')
        for l in numstat_lines:
            l = l.lstrip().rstrip()
            if l == '':
                continue

            nonempty_lines += 1

            if l in sub_exclusions:
                submodule_lines += 1

        if nonempty_lines == 0:
            # an absence of numstat_lines is taken to indicate a MERGE commit.
            # if we are incorrect and there is another way to get
            # here, things should still work out ok.

            # if it is a fully auto-merge, then hide.
            c_hash = commit_pretty.split(COL_DELIM)[0]
            non_auto = _git_difftree_does_find_content(finick_config, c_hash)
            if not non_auto:
                # appears to be an auto-merge
                commit_is_hidden = True
                reason_to_hide = 'auto merge commit. no diff available for review.'

        elif nonempty_lines == submodule_lines:
            # all we had in this commit were submodule 'pointer' changes
            # (some projects might want these reviewed. make that an option later.)
            commit_is_hidden = True
            reason_to_hide = 'no content changes to this repo. only re-pointing which commits submodules point to.'

        else:  # handle exclusions based on strings.
            parts = commit_pretty.split(COL_DELIM)
            if len(parts) != 4:
                raise FinickError(
                    'Git log formatted output did not parse cleanly into 4 parts. Did a stray COL_DELIM appear in a commit subject?')

            if finick_config.contains_a_configurable_tool_string(parts[3]):
                commit_is_hidden = True
                reason_to_hide = 'finick-driven automated commit excluded from review'

        list_of_tuples.insert(
            0, (commit_pretty, commit_is_hidden, reason_to_hide))

    return list_of_tuples


@_dec_assign_to_globals
def _git_current_user_email(finick_config):

    finicky.parse_config.AssertType_FinickConfig(finick_config)

    results = _git_exec_and_return_stdout('git config user.email',
                                          finick_config.repopath)
    results = results.rstrip().lstrip()

    if len(results) < 5 or len(results) > 255:
        raise FinickError(
            'Refusing to use what seems like an invalid email: ' + results)

    finick_config.reviewer = results


def _git_push(finick_config):
    _git_exec_and_return_stdout(
        'git push ' + _quietness + ' origin ' + finick_config.branch,
        finick_config.repopath)


def _git_commit_and_push(finick_config, commit_note1, commit_note2):
    _git_exec_and_return_stdout(
        'git commit -m \"' + commit_note1 + '\" -m \"' + commit_note2 + '\"',
        finick_config.repopath)

    _git_push(finick_config)


def _git_stage_the_edited_db(finick_config):
    finicky.parse_config.AssertType_FinickConfig(finick_config)

    the_db = finick_config.get_db_file_fullname_fullpath()

    # unlike other calls, we do _NOT_ use repopath for the shell call dir
    _git_exec_and_return_stdout('git add ' + the_db, finick_config.confdir)


@_dec_assign_to_globals
def git_perform_maintenance_commit(finick_config):
    finicky.parse_config.AssertType_FinickConfig(finick_config)

    the_db = finick_config.get_db_file_fullname_fullpath()

    # unlike other calls, we do _NOT_ use repopath for the shell call dir
    _git_exec_and_return_stdout('git add ' + the_db, finick_config.confdir)

    commit_note = finick_config.str_maint

    c_success = False

    # the git add succeeds even if 'the_db' had no changes to be staged.
    # when that happens, the git commit will fail.
    try:
        _git_exec_and_return_stdout('git commit -m \"' + commit_note + '\"',
                                    finick_config.repopath)

        c_success = True
    except FinickError:
        print('Warning: unable to complete a maintenance commit.')

    if c_success:
        _git_push(finick_config)


@_dec_assign_to_globals
def git_perform_sessionstart_commit(finick_config):
    finicky.parse_config.AssertType_FinickConfig(finick_config)

    _git_stage_the_edited_db(finick_config)

    commit_note1 = finick_config.str_start
    commit_note2 = 'reviewer: ' + finick_config.reviewer

    # the git add succeeds even if 'the_db' had no changes to be staged.
    # when that happens, the git commit will fail.
    # THAT SHOULD NOT HAPPEN HERE. we only start a session if there WERE new assignments.
    _git_commit_and_push(finick_config, commit_note1, commit_note2)


@_dec_assign_to_globals
def git_perform_session_completion_commit(finick_config, work_count):
    finicky.parse_config.AssertType_FinickConfig(finick_config)

    _git_stage_the_edited_db(finick_config)

    commit_note1 = finick_config.str_finish
    commit_note2 = 'reviewer: ' + finick_config.reviewer + ' '
    commit_note2 += 'reviewed ' + str(work_count) + ' commits'

    # the git add succeeds even if 'the_db' had no changes to be staged.
    # when that happens, the git commit will fail.
    # THAT SHOULD NOT HAPPEN HERE. we only start a session if there WERE new assignments.
    _git_commit_and_push(finick_config, commit_note1, commit_note2)


@_dec_assign_to_globals
def git_perform_session_abort_commit(finick_config):
    finicky.parse_config.AssertType_FinickConfig(finick_config)

    _git_stage_the_edited_db(finick_config)

    commit_note1 = finick_config.str_abort
    commit_note2 = 'reviewer: ' + finick_config.reviewer

    # the git add succeeds even if 'the_db' had no changes to be staged.
    # when that happens, the git commit will fail.
    # THAT SHOULD NOT HAPPEN HERE. we only start a session if there WERE new assignments.
    _git_commit_and_push(finick_config, commit_note1, commit_note2)


def _git_exec_and_return_stdout(command_string, repo_path):

    git_output = ''
    today_datestr = datetime.date.today().strftime("%Y-%m-%d") + ': '

    try:
        """
        On Unix, with shell=True: If args is a string, it specifies the
        command string to execute through the shell. This means that the
        string must be formatted exactly as it would be when typed at the
        shell prompt. This includes, for example, quoting or backslash
        escaping filenames with spaces in them.

        when we set 'shell=True', then the command is one long string.  if
        we use 'shell=False', then command_string should be =
        ['git','log','-5'], or something similar
        """
        git_process = subprocess.Popen(command_string,
                                       shell=True,
                                       stdin=subprocess.PIPE,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE,
                                       cwd=repo_path)

        git_output_bytes, git_errors_bytes = git_process.communicate()
        git_output = git_output_bytes.decode('utf-8')
        git_errors = git_errors_bytes.decode('utf-8')

        # one example of git output that goes to STDERR:
        # if you run 'git checkout XXX' while on XXX, the stderr is:
        #    Already on 'XXX'
        # Furthermore, according the git mailing list, they use STDERR for 'verbose' messages,
        # that are not always errors. that is intentional on their part.
        if len(git_errors) > 0:
            print(today_datestr + 'stderr calling git (' + command_string +
                  ') from path \'' + str(repo_path) + '\':')
            print(git_errors)
        else:
            print(str(today_datestr + 'no git stderr in \'' + str(repo_path) +
                      '\' (' + command_string + ')'))

        # according to the git devs, return code is the proper indicator of success (not checking stderr)
        if git_process.returncode != 0:
            err_msg = str(
                'return code ' + str(git_process.returncode) + ' calling git ('
                + command_string + ') from path \'' + str(repo_path) + '\'')
            raise FinickError(err_msg)

    except:
        print(today_datestr + 'python exception calling git (' + command_string
              + ') from path \'' + str(repo_path) + '\'')
        raise  # re-throw the same exception that got us here in the first place

    return git_output
