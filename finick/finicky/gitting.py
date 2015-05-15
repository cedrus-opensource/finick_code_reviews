
from __future__ import print_function
from __future__ import division # py3 style. division promotes to floating point.
from __future__ import unicode_literals
from __future__ import absolute_import

import finicky.parse_config
from finicky.error import FinickError

import subprocess
import datetime

_quietness = ''  # empty string means the ABSENCE of the quiet flag. absence means NO suppressed git stderr

def _dec_assign_to_globals(F):
    def wrapper(*args):
        finick_config = args[0]
        finicky.parse_config.AssertType_FinickConfig( finick_config )

        if finick_config.verbosity >= 1:
            finicky.gitting._quietness = ' ' # verbosity is ENABLED. we do not use the quiet flag
        else:
            finicky.gitting._quietness = ' -q ' # verbosity was at ZERO, so apply quietness

        return F(*args)

    return wrapper

@_dec_assign_to_globals
def git_establish_session_readiness( finick_config ):

    finicky.parse_config.AssertType_FinickConfig( finick_config )

    _git_exec_and_return_stdout( 'git checkout ' + _quietness + finick_config.branch, finick_config.repopath )

    # the next command needs git 1.6.3 or newer, per http://stackoverflow.com/questions/1417957/show-just-the-current-branch-in-git
    results = _git_exec_and_return_stdout( 'git rev-parse --abbrev-ref HEAD', finick_config.repopath )

    if results.rstrip() != finick_config.branch:
        raise FinickError("Unable to start code-review session. Could not check out the required git branch.")

    _git_exec_and_return_stdout( 'git pull ' + _quietness + ' origin ' + finick_config.branch, finick_config.repopath )

    # if we are starting one session, there must not be any other session in progress (even from other INI file)
    # check for a currently-open, in-progress review session.
    # if one is in progress, our version 0.0 code can give up.
    # eventually, rather than give up, move our local HEAD to just prior/after that session, and start our session there

    # for now, either an exception was thrown, or else all went well:
    return True


@_dec_assign_to_globals
def git_repo_contains_committed_file( finick_config, which_file ):

    finicky.parse_config.AssertType_FinickConfig( finick_config )

    # this can be a false positive if the file is on disk, but has been deleted from the repo
    results = _git_exec_and_return_stdout( 'git log -1 --oneline ' + which_file, finick_config.repopath )

    problem_01 = 0 == len(results)

    # (addresses the false positive mentioned above)
    # this returns an empty string even if we got a false positive earlier.
    # (we don't use ls-files alone, because it gives a false positive if you staged a file but never committed it)
    results = _git_exec_and_return_stdout( 'git ls-files ' + which_file, finick_config.repopath )

    problem_02 = 0 == len(results)

    return not ( problem_01 or problem_02 )



def _git_exec_and_return_stdout( command_string, repo_path ):

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
        git_process = subprocess.Popen(
            command_string,
            shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=repo_path
            )

        git_output_bytes, git_errors_bytes = git_process.communicate()
        git_output = git_output_bytes.decode('utf-8')
        git_errors = git_errors_bytes.decode('utf-8')

        # one example of git output that goes to STDERR:
        # if you run 'git checkout XXX' while on XXX, the stderr is:
        #    Already on 'XXX'
        # Furthermore, according the git mailing list, they use STDERR for 'verbose' messages,
        # that are not always errors. that is intentional on their part.
        if len(git_errors) > 0:
            print ( today_datestr + 'stderr calling git (' + command_string + ') from path \'' + str(repo_path) + '\':' )
            print ( git_errors )
        else:
            print ( str( today_datestr +
                         'no git stderr in \'' + str(repo_path) + '\' (' + command_string + ')' ) )

        # according to the git devs, return code is the proper indicator of success (not checking stderr)
        if git_process.returncode != 0:
            err_msg = str( 'return code ' + str(git_process.returncode) + ' calling git (' +
                           command_string + ') from path \'' + str(repo_path) + '\'' )
            raise FinickError( err_msg )

    except:
        print ( today_datestr + 'python exception calling git (' + command_string + ') from path \'' + str(repo_path) + '\'' )
        raise # re-throw the same exception that got us here in the first place

    return git_output
