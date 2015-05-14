
import finicky.parse_config
from finicky.error import FinickError

import glob

def prelaunch_checklist_open( calling_filename ):
    return _prelaunch_checklist( calling_filename, False )

def prelaunch_checklist_close( calling_filename ):
    return _prelaunch_checklist( calling_filename, True )

def _prelaunch_checklist( calling_filename, please_use_db_file_datetime ):

    # make sure this is called as finick/start.py (use os.sep). this way we can count on CWD for finding config
    # config integrity check. (older than NOW).
    # are we on the right branch?
    # do a git-whoami and make sure we have an email

    all_cwd_inis = glob.glob('*ini')

    if len(all_cwd_inis) != 1:
        # eventually we will allow the INI file to be passed as an argument
        raise FinickError("you must have exactly one (and only one) ini file in the CWD")

    return finicky.parse_config.FinickConfig( all_cwd_inis[0] )

