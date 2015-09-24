from __future__ import print_function
from __future__ import division  # py3 style. division promotes to floating point.
from __future__ import unicode_literals
from __future__ import absolute_import

from finicky.db_row import AssertType_DbRow, DbRow
from finicky.parse_config import AssertType_FinickConfig
from finicky.error import FinickError

import random


class CalendarBucket(object):
    def __init__(self, date_obj, commits_list, targeted_dev):
        self.__datetime_obj = date_obj
        self.__developer = targeted_dev
        self.__commits_in_bucket_author = []
        self.__commits_in_bucket_reviewer = []

        dr = DbRow.dummyinstance()
        self.__oopsish_author = [dr.TYPE_OOPS, dr.TYPE_TODO]
        self.__oopsish_rviewr = [dr.TYPE_OOPS, dr.TYPE_TODO, dr.TYPE_PLS]

        self.__hoorayish_author = [dr.TYPE_OK, dr.TYPE_FIXD, dr.TYPE_PLS]
        self.__hoorayish_rviewr = [dr.TYPE_OK, dr.TYPE_FIXD]

        self.__pending = [dr.TYPE_WAIT]

        for commit in commits_list:
            if commit.committer.lower() == self.__developer.lower():
                self.__commits_in_bucket_author.append(commit)

            #note: do _NOT_ use 'elif' !! self-review is possible.
            # (meaning something where committer is 'a' could also have reviewer is 'a')
            if commit.reviewer.lower() == self.__developer.lower():
                self.__commits_in_bucket_reviewer.append(commit)

    def _count_filtered_by_types(self, what_to_filter, list_of_types):
        rslt = 0
        for commit in what_to_filter:
            if commit.row_type in list_of_types:
                rslt += 1

        return rslt

    def get_bucket_label(self):

        return self.__datetime_obj.strftime("%Y-%m-%d")

    def get_oopsish_by_author(self):

        return self._count_filtered_by_types(self.__commits_in_bucket_author,
                                             self.__oopsish_author)

    def get_hoorayish_by_author(self):

        return self._count_filtered_by_types(self.__commits_in_bucket_author,
                                             self.__hoorayish_author)

    def get_waitcount_authored_by(self):

        return self._count_filtered_by_types(self.__commits_in_bucket_author,
                                             self.__pending)

    def get_oopsish_by_reviewer(self):

        return self._count_filtered_by_types(self.__commits_in_bucket_reviewer,
                                             self.__oopsish_rviewr)

    def get_hoorayish_by_reviewer(self):

        return self._count_filtered_by_types(self.__commits_in_bucket_reviewer,
                                             self.__hoorayish_rviewr)


class ChartGenerator(object):
    def __init__(self, finick_config, commits_map):
        self.__finick_config = finick_config
        self.__aggregated_commit_lists = commits_map

        AssertType_FinickConfig(self.__finick_config)

        # each map key should be a date, and the mapped value is a list:
        for map_key, val in self.__aggregated_commit_lists.items():
            for list_item in val:
                AssertType_DbRow(list_item)

    def _stats_by_mapkey_buckets(self,
                                 plotter,
                                 y_bottom_int,
                                 bar_width,
                                 bar_anchors,
                                 portions_a,
                                 colorname_a,
                                 portions_b,
                                 colorname_b,
                                 portions_c=[],
                                 colorname_c=''):
        """
        Making a STACKED BAR CHART.
        """

        how_many_bars = len(portions_a)
        bottom_0 = []

        for i in range(0, how_many_bars):
            bottom_0 += [y_bottom_int]

        bottom_1 = [x + y for x, y in zip(bottom_0, portions_a)]

        bottom_2 = [x + y for x, y in zip(bottom_1, portions_b)]

        if len(portions_c) > 0:
            sum_portions = [
                x + y + z
                for x, y, z in zip(portions_a, portions_b, portions_c)
            ]
        else:
            sum_portions = [x + y for x, y in zip(portions_a, portions_b)]

        high_bar = max(sum_portions) + y_bottom_int

        p1 = plotter.bar(bar_anchors,
                         portions_a,
                         bar_width,
                         color=colorname_a,
                         bottom=bottom_0)

        p2 = plotter.bar(bar_anchors,
                         portions_b,
                         bar_width,
                         color=colorname_b,
                         bottom=bottom_1)

        if len(portions_c) > 0:
            p3 = plotter.bar(bar_anchors,
                             portions_c,
                             bar_width,
                             color=colorname_c,
                             bottom=bottom_2)

        return high_bar

    def draw_charts(self):

        # defer these imports until the last possible moment:
        import numpy
        import matplotlib.pyplot

        target_developer = 'fake@fake.com'

        barportion_0 = []  # oops as an author
        barportion_1 = []  # hooray by author
        barportion_2 = []  # still un-reviewed for this author

        oops_author_color = 'orangered'
        hooray_author_color = 'palegreen'
        unreviewed_color = '#DDDDDD'  # light grey

        rviewr_barportion_0 = []  # oops *caught* while reviewing
        rviewr_barportion_1 = []  # hoorays granted while reviewing

        oops_reviewer_color = 'gold'
        hooray_reviewer_color = 'khaki'

        zoom_multiplier_auth = 1  # adjust this (upwards) if items reviewed dwarfs (dominates) items authored
        zoom_multiplier_rvwr = 1  # adjust this (up) if items authored dominates the chart

        matplotlib.pyplot.clf()
        bar_width = 2
        xlabel_shift = bar_width + 1

        bar_anchors = []
        # for labeling along the x axis:
        wlabels = []
        label_right_anchors = []

        # the keys are DATES. we want to SORT chronologically:
        for map_key in sorted(self.__aggregated_commit_lists):

            bucket = CalendarBucket(map_key,
                                    self.__aggregated_commit_lists[map_key],
                                    target_developer)

            bucket_num = len(bar_anchors)
            bar_anchors += [(bucket_num + 1) * 5]
            wlabels += [bucket.get_bucket_label()]
            label_right_anchors += [((bucket_num + 1) * 5) + xlabel_shift]

            # height of portion 0 of the bar:
            barportion_0 += [bucket.get_oopsish_by_author() *
                             zoom_multiplier_auth]

            # units out of total height that be the color or portion 1:
            barportion_1 += [bucket.get_hoorayish_by_author() *
                             zoom_multiplier_auth]

            barportion_2 += [bucket.get_waitcount_authored_by() *
                             zoom_multiplier_auth]

            rviewr_barportion_0 += [bucket.get_oopsish_by_reviewer() *
                                    zoom_multiplier_rvwr]

            rviewr_barportion_1 += [bucket.get_hoorayish_by_reviewer() *
                                    zoom_multiplier_rvwr]

        high_bar = self._stats_by_mapkey_buckets(
            matplotlib.pyplot, 0, bar_width, bar_anchors, barportion_0,
            oops_author_color, barportion_1, hooray_author_color, barportion_2,
            unreviewed_color)

        high_bar += 3

        matplotlib.pyplot.axhline(high_bar)

        label_position_for_lower_row = high_bar / 2

        new_high_bar = self._stats_by_mapkey_buckets(
            matplotlib.pyplot, high_bar, bar_width, bar_anchors,
            rviewr_barportion_0, oops_reviewer_color, rviewr_barportion_1,
            hooray_reviewer_color)

        label_position_for_upper_row = high_bar + (
            (new_high_bar - high_bar) / 2)

        # if we need a 90-degree rotated ylabel:
        #matplotlib.pyplot.ylabel('This side\nsecond line')

        matplotlib.pyplot.title('Code Reviews by and for ' + target_developer)

        # sequence of tick positions, then a sequence of tick labels:
        matplotlib.pyplot.xticks(label_right_anchors,
                                 wlabels,
                                 rotation=60,
                                 ha='right')

        # gca means to 'get current axes':
        ax = matplotlib.pyplot.gca()
        for t in ax.xaxis.get_major_ticks():
            t.tick1On = False  # a hack-around to hide ticks (while keeping tick labels)
            t.tick2On = False  # a hack-around to hide ticks (while keeping tick labels)

        # sequence of tick positions, then a sequence of tick labels:
        matplotlib.pyplot.yticks(
            [label_position_for_upper_row, label_position_for_lower_row
             ], [target_developer + ' as reviewer\n(code reading)',
                 target_developer + ' as committer\n(code authoring)'])

        # be careful: it will save right over any preexisting file:
        matplotlib.pyplot.savefig(target_developer + '.png',
                                  dpi=300,
                                  bbox_inches='tight',
                                  pad_inches=0.75)

        #matplotlib.pyplot.show()

        matplotlib.pyplot.close()
