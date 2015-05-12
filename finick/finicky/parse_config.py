


class FinickConfig(object):

    def __init__(self, file_location):
        self.__branch = ''
        self.__purgeweeks = -1
        self.__ourepochstart = 0
        self.__str_start = ''
        self.__str_abort = ''
        self.__str_finish = ''
        self.__str_maint = ''



    def _fail_setter(self, value):
        raise Exception("FinickConfig objects are immutable")

    branch     = property(lambda s : s.__branch,        _fail_setter)

    purgeweeks = property(lambda s : s.__purgeweeks,    _fail_setter)

    startepoch = property(lambda s : s.__ourepochstart, _fail_setter)

    str_start  = property(lambda s : s.__str_start,     _fail_setter)

    str_abort  = property(lambda s : s.__str_abort,     _fail_setter)

    str_finish = property(lambda s : s.__str_finish,    _fail_setter)

    str_maint  = property(lambda s : s.__str_maint,     _fail_setter)


