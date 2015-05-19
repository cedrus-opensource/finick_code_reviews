from __future__ import print_function
from __future__ import division  # py3 style. division promotes to floating point.
from __future__ import unicode_literals
from __future__ import absolute_import

from finicky.error import FinickError

import datetime


class DbRow(object):
    @classmethod
    def create_from_string(cls, string_to_parse, file_comment):
        return cls(False, string_to_parse, file_comment)

    @classmethod
    def create_from_gitting_tuple(cls, gitt_tuple):
        # our tuples come directly from git output. so there is never a file_comment
        return cls(False, '', '', gitt_tuple)

    def _fail_setter(self, value):
        raise FinickError(
            "The value you are trying to assign to in DbRow is read-only.")

    def __init__(self, is_dummy,
                 string_to_parse='',
                 file_comment='',
                 gitt_tuple=None):

        self.__ACTION_COMMENT_CHAR = '#'

        self.__TYPE_ERRORTYPE = -1
        # yapf: disable
        self.__TYPE_OK   =  1  # reviewer approved/accepted the commit
        self.__TYPE_OOPS =  2  # reviewer rejected the commit
        self.__TYPE_WAIT =  3  # not yet reviewed. awaiting review.
        self.__TYPE_TFIX =  4  # when a reviewer marks TFIX, this means both approval AND the commit closes a todo
        self.__TYPE_TODO =  5  # reviewer defers the commit, contingent upon further items being addressed
        self.__TYPE_HIDE =  6  # a commit that is 'null' for reviewing purposes. hidden/excluded from the process.
        self.__TYPE_NOW  =  7  # assigned for review during the current active session
        self.__TYPE_PLS  =  8  # (short for 'please'). like todo, only we accept the commit, but with further requests for later.
        self.__TYPE_PFIX =  9  # means both approval and the commit closes a PLS ('please' request)
        self.__TYPE_RVRT = 10  # a revert/reversal that is accepted and addresses a prior OOPS
        # yapf: enable

        self.__creator = ''  # this variable is intended only for debugging/tracing

        self.__file_comment = file_comment
        self.__committer = ''
        self.__commit_hash = ''
        # see comments in gitting.py about our timezone issues. again,
        # for now, date strings are just a 'courtesy', not hard data.
        self.__commit_datestr = ''
        self.__rowtype = self.__TYPE_ERRORTYPE
        self.__reviewer = ''
        self.__todo_refs = []
        self.__action_comment = ''
        # at some point we might need more structure, like a forefront DATETIME object:
        self.__forefront_string = ''

        if gitt_tuple is not None:
            self.__creator = 'create_from_gitting_tuple'
            self._initialize_from_tuple(gitt_tuple)
        elif False == is_dummy:
            self.__creator = 'create_from_string'
            self._initialize_from_string(string_to_parse)
            pass

    # yapf: disable

    TYPE_OK    = property(lambda s : s.__TYPE_OK,    _fail_setter)

    TYPE_OOPS  = property(lambda s : s.__TYPE_OOPS,  _fail_setter)

    TYPE_WAIT  = property(lambda s : s.__TYPE_WAIT,  _fail_setter)

    TYPE_TFIX  = property(lambda s : s.__TYPE_TFIX,  _fail_setter)

    TYPE_TODO  = property(lambda s : s.__TYPE_TODO,  _fail_setter)

    TYPE_HIDE  = property(lambda s : s.__TYPE_HIDE,  _fail_setter)

    TYPE_NOW   = property(lambda s : s.__TYPE_NOW,   _fail_setter)

    TYPE_PLS   = property(lambda s : s.__TYPE_PLS,   _fail_setter)

    TYPE_PFIX  = property(lambda s : s.__TYPE_PFIX,  _fail_setter)

    TYPE_RVRT  = property(lambda s : s.__TYPE_RVRT,  _fail_setter)


    row_type   = property(lambda s : s.__rowtype,    _fail_setter)

    commithash = property(lambda s : s.__commit_hash, _fail_setter)

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

            for _i_ in range(0, 5):
                car_cdr = car_cdr[CDR].split(None, 1)
                row_parts.append(car_cdr[CAR])
                if car_cdr[CDR].startswith(self.__ACTION_COMMENT_CHAR):
                    row_parts.append(car_cdr[CDR])
                    break

        except IndexError:
            # we arrive here for lines that do not possess the maximum 7 columns
            pass

        len_of_row_parts = len(row_parts)

        if len_of_row_parts < 4 or len_of_row_parts > 7:
            err_str = 'Unable to parse columns in this row: [' + string_to_parse + ']'
            raise FinickError(err_str)

        self.__committer = row_parts[0]
        self.__commit_hash = row_parts[1]
        # see comments in gitting.py about our timezone issues. again,
        # for now, date strings are just a 'courtesy', not hard data.
        self.__commit_datestr = row_parts[2]
        self.__rowtype = self._convert_string_to_rowtype_constant(
            row_parts[3], string_to_parse)

        # note: in order to have a comment, we MUST have a reviewer! even if the reviewer is '..nobody..'
        if len_of_row_parts >= 5:
            self.__reviewer = row_parts[4]

        if len_of_row_parts >= 6:
            # we now can have either 1 more value or 2.
            # if 2, then we have todo_refs and a comment.
            # if 1, then it could be EITHER todo_refs or a comment
            if len_of_row_parts == 7:
                self.__todo_refs = row_parts[5].split(',')
                self.__action_comment = row_parts[6]
            else:
                if row_parts[5].startswith(self.__ACTION_COMMENT_CHAR):
                    self.__action_comment = row_parts[5]
                else:
                    self.__todo_refs = row_parts[5].split(',')

    def _initialize_from_tuple(self, gitt_tuple):
        # the tuple came from gitting.git_retrieve_history.
        # this is a 3-tuple with a oneline_gitlog string, then a bool, then a comment string.
        # the bool represents whether this row should be a HIDE row (excluded from being reviewed)

        # warning: knowledge about using '\b\ as the delim is duplicated in gitting.py
        COL_DELIM = '\b'
        wants_to_hide = gitt_tuple[1]
        action_comment_string = gitt_tuple[
            2
        ]  # at this point it should _NOT_ have __ACTION_COMMENT_CHAR yet!

        c_hash, committer_eml, date_string, ignored_subject = gitt_tuple[0].split(
            COL_DELIM)

        self.__committer = committer_eml
        self.__commit_hash = c_hash
        if len(action_comment_string) > 0:
            self.__action_comment = self.__ACTION_COMMENT_CHAR + ' ' + action_comment_string

        if wants_to_hide:
            self.__rowtype = self.__TYPE_HIDE
        else:
            self.__rowtype = self.__TYPE_WAIT

        # we expect 'date_string' to be in RFC2822 style
        # Tue, 2 Feb 2010 22:22:56 +0000

        shorter_d_str = date_string[:-6]  # strptime cannot handle the utc offset

        date_obj = datetime.datetime.strptime(shorter_d_str,
                                              "%a, %d %b %Y %H:%M:%S")  # %z")

        # see comments in gitting.py about our timezone issues. again,
        # for now, date strings are just a 'courtesy', not hard data.
        self.__commit_datestr = date_obj.strftime("%Y-%m-%d_%H:%M:%S")

    def set_forefront_marker(self, forefront_marker_string):
        if self.__forefront_string != '':
            print(
                'Warning: setting forefront info on a DbRow that already had such info.')

        self.__forefront_string = forefront_marker_string

    def _convert_rowtype_constant_to_string(self, rowtype_int):
        if rowtype_int == self.__TYPE_OK:
            return 'OK'
        elif rowtype_int == self.__TYPE_OOPS:
            return 'OOPS'
        elif rowtype_int == self.__TYPE_WAIT:
            return 'WAIT'
        elif rowtype_int == self.__TYPE_TFIX:
            return 'TFIX'
        elif rowtype_int == self.__TYPE_TODO:
            return 'TODO'
        elif rowtype_int == self.__TYPE_HIDE:
            return 'HIDE'
        elif rowtype_int == self.__TYPE_NOW:
            return 'NOW'
        elif rowtype_int == self.__TYPE_PLS:
            return 'PLS'
        elif rowtype_int == self.__TYPE_PFIX:
            return 'PFIX'
        elif rowtype_int == self.__TYPE_RVRT:
            return 'RVRT'
        else:
            err = 'Invalid row type: ' + str(rowtype_int)
            raise FinickError(err)

    def _convert_string_to_rowtype_constant(self, rowtype_string, linetext):
        if rowtype_string == 'OK':
            return self.__TYPE_OK
        elif rowtype_string == 'OOPS':
            return self.__TYPE_OOPS
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
        elif rowtype_string == 'PLS':
            return self.__TYPE_PLS
        elif rowtype_string == 'PFIX':
            return self.__TYPE_PFIX
        elif rowtype_string == 'RVRT':
            return self.__TYPE_RVRT
        else:
            err = 'Invalid row type: ' + rowtype_string + ', on row: [' + linetext + ']'
            raise FinickError(err)

    def write_to_diskfile(self, the_file):
        # the_file is expected to be a TextIOBase (from io)

        EMAIL_COL_WIDTH = 27  # later this should be in the config
        TYPE_COL_WIDTH = 7

        if self.__file_comment != '':
            the_file.write(self.__file_comment + '\n')

        row_text = ''

        row_text += (self.__committer + ' ' +
                     (' ' * (EMAIL_COL_WIDTH - len(self.__committer) - 1)))

        row_text += (self.__commit_hash + '   ')

        # see comments in gitting.py about our timezone issues. again,
        # for now, date strings are just a 'courtesy', not hard data.
        row_text += (self.__commit_datestr + '   ')

        rowtype_str = self._convert_rowtype_constant_to_string(self.__rowtype)
        row_text += (rowtype_str + ' ' +
                     (' ' * (TYPE_COL_WIDTH - len(rowtype_str) - 1)))

        reviewer_output = self.__reviewer

        # next comes the reviewer. BUT:
        # note: in order to have a comment, we MUST have a reviewer! even if the reviewer is '..nobody..'
        if self.__action_comment != '':
            if self.__reviewer == '':
                # comment is nonempty but __reviewer was empty. fix that:
                reviewer_output = '..nobody..'

        row_text += (reviewer_output + ' ' +
                     (' ' * (EMAIL_COL_WIDTH - len(reviewer_output) - 1)))

        # refs, with commas (short hashes?)
        for tr in self.__todo_refs:
            row_text += (tr + ',')

        if len(self.__todo_refs) > 0:
            row_text += ('   ')

        # note: in order to have a comment, we MUST have a reviewer! even if the reviewer is '..nobody..'
        if self.__action_comment != '':
            if not self.__action_comment.startswith(
                self.__ACTION_COMMENT_CHAR):
                raise FinickError(
                    'We always expect __ACTION_COMMENT_CHAR to have been prepended by now.')

        row_text += (self.__action_comment)

        # we could do more sanity checking here. make sure what we are
        # about to save parses back as something equal to self

        # end this row
        row_text = row_text.rstrip()
        the_file.write(row_text + '\n')

        if self.__forefront_string != '':
            the_file.write(self.__forefront_string + '\n')
