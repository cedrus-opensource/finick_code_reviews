



import finicky.parse_config

def prelaunch_checklist_open( calling_filename ):
    _prelaunch_checklist( calling_filename, False )

def prelaunch_checklist_close( calling_filename ):
    _prelaunch_checklist( calling_filename, True )

def _prelaunch_checklist( calling_filename, please_use_db_file_datetime ):

    # make sure this is called as finick/start.py (use os.sep). this way we can count on CWD for finding config
    # config integrity check. (older than NOW).
    # are we on the right branch?
    # do a git-whoami and make sure we have an email

    print "prelaunch_checklist"
    print calling_filename
    return finicky.parse_config.FinickConfig( '' )

