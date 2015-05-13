
import ConfigParser

class FinickConfig(object):

    def __init__(self, file_location):
        self.__is_ok = False

        self.__branch = ''
        self.__purgeweeks = -1
        self.__ourepochstart = 0
        self.__str_start = ''
        self.__str_abort = ''
        self.__str_finish = ''
        self.__str_maint = ''

        self._initialize_from_file( file_location )



    def _fail_setter(self, value):
        raise Exception("FinickConfig objects are immutable")

    is_ok      = property(lambda s : s.__is_ok,         _fail_setter)

    branch     = property(lambda s : s.__branch,        _fail_setter)

    purgeweeks = property(lambda s : s.__purgeweeks,    _fail_setter)

    startepoch = property(lambda s : s.__ourepochstart, _fail_setter)

    str_start  = property(lambda s : s.__str_start,     _fail_setter)

    str_abort  = property(lambda s : s.__str_abort,     _fail_setter)

    str_finish = property(lambda s : s.__str_finish,    _fail_setter)

    str_maint  = property(lambda s : s.__str_maint,     _fail_setter)


    def _initialize_from_file( self, file_location ):

        cf = ConfigParser.ConfigParser()
        cf.read( file_location )

        self.__branch = cf.get('GitReviews','MainReviewBranch')
        self.__purgeweeks = int(cf.get('GitReviews','WeeksTilPurge'))
        self.__ourepochstart = int(cf.get('GitReviews','BeginningOfTime'))
        self.__str_start = cf.get('GitReviews','CommitStringStartSession')
        self.__str_abort = cf.get('GitReviews','CommitStringAbortSession')
        self.__str_finish = cf.get('GitReviews','CommitStringFinishSession')
        self.__str_maint = cf.get('GitReviews','CommitStringMaintWithoutSession')


        # todo: we need to sanity check this more thoroughly before setting to true
        self.__is_ok = True
