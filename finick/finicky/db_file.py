
import finicky.gitting


def db_integrity_check_open( finick_config ):

    _db_integrity_check( finick_config, False )

def db_integrity_check_close( finick_config ):

    # reviews file should now be properly upgraded already.
    # last line in DB file should be file version info
    _db_integrity_check( finick_config, True )


def _db_integrity_check( finick_config, session_is_closing ):

    finicky.parse_config.AssertType_FinickConfig( finick_config )
    pass

def db_open_session( finick_config ):

    finicky.parse_config.AssertType_FinickConfig( finick_config )

    # upgrade file format if needed.
    # purge older, completed data
    # add new stuff to forward end of file (last line should always be file version info).

    # generate assignments for this session.
    # emit a reminder message about todo items
    # if there are no assignments for whoami, then we are done! (we can still commit changes to DB file)

