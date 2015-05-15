from __future__ import print_function
from __future__ import division  # py3 style. division promotes to floating point.
from __future__ import unicode_literals
from __future__ import absolute_import

from finicky.error import FinickError


class DbRow(object):
    @classmethod
    def create_from_string(cls, string_to_parse, file_comment):
        return cls(False, string_to_parse, file_comment)

    def _fail_setter(self, value):
        raise FinickError(
            "The value you are trying to assign to in DbRow is read-only.")

    def __init__(self, is_dummy, string_to_parse='', file_comment=''):

        self.__TYPE_ERRORTYPE = -1
        # yapf: disable
        self.__TYPE_OK   = 1  # reviewer approved/accepted the commit
        self.__TYPE_REJ  = 2  # reviewer rejected the commit
        self.__TYPE_WAIT = 3  # not yet reviewed. awaiting review.
        self.__TYPE_TFIX = 4  # when a reviewer marks TFIX, this means both approval AND the commit closes a todo
        self.__TYPE_TODO = 5  # reviewer accepts the commit, contingent upon further items being addressed
        self.__TYPE_HIDE = 6  # a commit that is 'null' for reviewing purposes. hidden/excluded from the process.
        self.__TYPE_NOW  = 7  # assigned for review during the current active session
        # yapf: enable

        self.__file_comment = file_comment
        self.__committer = ''
        self.__commit_hash = ''
        self.__rowtype = self.__TYPE_ERRORTYPE
        self.__reviewer = ''
        self.__todo_refs = []
        self.__action_comment = ''
        # at some point we might need more structure, like a forefront DATETIME object:
        self.__forefront_string = ''

        if False == is_dummy:
            self._initialize_from_string(string_to_parse)
            pass

    # yapf: disable

    TYPE_OK    = property(lambda s : s.__TYPE_OK,    _fail_setter)

    TYPE_REJ   = property(lambda s : s.__TYPE_REJ,   _fail_setter)

    TYPE_WAIT  = property(lambda s : s.__TYPE_WAIT,  _fail_setter)

    TYPE_TFIX  = property(lambda s : s.__TYPE_TFIX,  _fail_setter)

    TYPE_TODO  = property(lambda s : s.__TYPE_TODO,  _fail_setter)

    TYPE_HIDE  = property(lambda s : s.__TYPE_HIDE,  _fail_setter)

    TYPE_NOW   = property(lambda s : s.__TYPE_NOW,   _fail_setter)


    row_type   = property(lambda s : s.__rowtype,    _fail_setter)

    # yapf: enable

    def _initialize_from_string(self, string_to_parse):
        """
        jdoe@cedrus.com    f6cc7699fb362c2777c474f3416ce0abb2c083fe   HIDE  nobody                # this is a reversal of commit xxxxxx
        jdoe@cedrus.com    7b660c3a473225f49c73e51c7b8af61e139990a0   NOW
        jdoe@cedrus.com    2228add0186febf3471914c861b3b06fd0eb8dbc   TFIX  abc@cedrus.com  ecfb335633  # good fix for todo

        TYPE_HIDE HIDE is for things that were reversals, and for this:
        CommitStringMaintWithoutSession=Cedrus_Automated_Maintenance_Commit
        """

        row_parts = []

        try:
            CAR = 0
            CDR = 1

            # pass None to make all blobs of whitespace a single separator:
            car_cdr = string_to_parse.split(None, 1)
            row_parts.append(car_cdr[CAR])

            for _i_ in range(0, 4):
                car_cdr = car_cdr[CDR].split(None, 1)
                row_parts.append(car_cdr[CAR])
                if car_cdr[CDR].startswith('#'):
                    row_parts.append(car_cdr[CDR])
                    break

        except IndexError:
            # we arrive here for lines that do not possess the maximum 6 columns
            pass

        len_of_row_parts = len(row_parts)

        if len_of_row_parts < 3 or len_of_row_parts > 6:
            err_str = 'Unable to parse columns in this row: [' + string_to_parse + ']'
            raise FinickError(err_str)

        self.__committer = row_parts[0]
        self.__commit_hash = row_parts[1]
        self.__rowtype = self._convert_string_to_rowtype_constant(
            row_parts[2], string_to_parse)

        # note: in order to have a comment, we MUST have a reviewer! even if the reviewer is '..nobody..'
        if len_of_row_parts >= 4:
            self.__reviewer = row_parts[3]

        if len_of_row_parts >= 5:
            # we now can have either 1 more value or 2.
            # if 2, then we have todo_refs and a comment.
            # if 1, then it could be EITHER todo_refs or a comment
            if len_of_row_parts == 6:
                self.__todo_refs = row_parts[4].split(',')
                self.__action_comment = row_parts[5]
            else:
                if row_parts[4].startswith('#'):
                    self.__action_comment = row_parts[4]
                else:
                    self.__todo_refs = row_parts[4].split(',')

    def set_forefront_marker(self, forefront_marker_string):
        if self.__forefront_string != '':
            print(
                'Warning: setting forefront info on a DbRow that already had such info.')

        self.__forefront_string = forefront_marker_string

    def _convert_string_to_rowtype_constant(self, rowtype_string, linetext):
        if rowtype_string == 'OK':
            return self.__TYPE_OK
        elif rowtype_string == 'REJ':
            return self.__TYPE_REJ
        elif rowtype_string == 'WAIT':
            return self.__TYPE_WAIT
        elif rowtype_string == 'TFIX':
            return self.__TYPE_TFIX
        elif rowtype_string == 'TODO':
            return self.__TYPE_TODO
        elif rowtype_string == 'HIDE':
            return self.__TYPE_HIDE
        elif rowtype_string == 'NOW':
            return self.__TYPE_NOW
        else:
            err = 'Invalid row type: ' + rowtype_string + ', on row: [' + linetext + ']'
            raise FinickError(err)
