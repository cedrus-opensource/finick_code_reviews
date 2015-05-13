
import finicky.parse_config

import subprocess
import datetime

def git_establish_session_readiness( finick_config ):

    finicky.parse_config.AssertType_FinickConfig( finick_config )
    # can we pull/merge all from origin?

    results = 'no results'
    #results = _git_exec_and_return_stdout( 'git log -8', finick_config.repopath )
    print results



def _git_exec_and_return_stdout( command_string, repo_path ):

    git_log_output = ''

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
        git_log_process = subprocess.Popen(
            command_string,
            shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=repo_path
            )

        git_log_output, git_log_errors = git_log_process.communicate()

        if len(git_log_errors) > 0:
            print 'error during calls to git log:'
            print git_log_errors
        else:
            print datetime.date.today().strftime("%Y-%m-%d") + ' no git error in \'' + str(repo_path) + '\''

    except:
        print 'Failed to use \'git log\' to retrieve the most recent commits from \'' + str(repo_path) + '\''

    return git_log_output
