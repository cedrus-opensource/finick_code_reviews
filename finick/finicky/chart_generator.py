from __future__ import print_function
from __future__ import division  # py3 style. division promotes to floating point.
from __future__ import unicode_literals
from __future__ import absolute_import

from finicky.db_row import AssertType_DbRow, DbRow
from finicky.parse_config import AssertType_FinickConfig
from finicky.error import FinickError

import random


class WeekGroup(object):
    def get_week_label(self):
        try:
            self.aa += 1
        except:
            self.aa = 0

        return 'week-' + str(self.aa)

    def get_oopsish_by_author(self, author):
        return random.randint(0, 100)

    def get_hoorayish_by_author(self, author):
        return random.randint(0, 100)

    def get_waitcount_authored_by(self, author):
        return random.randint(0, 100)

    def get_oopsish_by_reviewer(self, author):
        return random.randint(0, 100)

    def get_hoorayish_by_reviewer(self, author):
        return random.randint(0, 100)


class ChartGenerator(object):
    def __init__(self, finick_config, assignments):
        self.__finick_config = finick_config
        self.__assignmentlist = assignments

        AssertType_FinickConfig(self.__finick_config)

        for a in self.__assignmentlist:
            AssertType_DbRow(a)

    def _stats_by_week(self,
                       plotter,
                       y_bottom_int,
                       bar_width,
                       bar_anchors,
                       portions_a,
                       portions_b,
                       portions_c=[]):
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
                         color='green',
                         bottom=bottom_0)

        p2 = plotter.bar(bar_anchors,
                         portions_b,
                         bar_width,
                         color='orange',
                         bottom=bottom_1)

        if len(portions_c) > 0:
            p3 = plotter.bar(bar_anchors,
                             portions_c,
                             bar_width,
                             color='red',
                             bottom=bottom_2)

        return high_bar

    def draw_charts(self):

        # defer these imports until the last possible moment:
        import numpy
        import matplotlib.pyplot

        target_developer = 'kh'

        green_portion = []
        yellow_portion = []
        red_portion = []

        gold_portion = []
        black_portion = []

        matplotlib.pyplot.clf()
        bar_width = 1

        bar_anchors = []
        # for labeling along the x axis:
        wlabels = []

        # simulate 12 weeks
        for each_week_num in range(0, 12):

            # this is just 'faking it' for now:
            wg = WeekGroup()

            bar_anchors += [(each_week_num + 1) * 5]
            wlabels += [wg.get_week_label()]

            # height of green portion of the bar:
            green_portion += [wg.get_oopsish_by_author(target_developer)]

            # units out of total height that will be yellow:
            yellow_portion += [wg.get_hoorayish_by_author(target_developer)]

            red_portion += [wg.get_waitcount_authored_by(target_developer)]

            # height of green portion of the bar:
            gold_portion += [wg.get_oopsish_by_reviewer(target_developer)]

            # units out of total height that will be yellow:
            black_portion += [wg.get_hoorayish_by_reviewer(target_developer)]

        high_bar = self._stats_by_week(matplotlib.pyplot, 0, bar_width,
                                       bar_anchors, green_portion,
                                       yellow_portion, red_portion)

        high_bar += 15

        matplotlib.pyplot.axhline(high_bar)

        label_position_for_lower_row = high_bar / 2

        new_high_bar = self._stats_by_week(matplotlib.pyplot, high_bar,
                                           bar_width, bar_anchors,
                                           gold_portion, black_portion)

        label_position_for_upper_row = high_bar + (
            (new_high_bar - high_bar) / 2)

        # if we need a 90-degree rotated ylabel:
        #matplotlib.pyplot.ylabel('This side\nsecond line')

        matplotlib.pyplot.title('Code Reviews by and for ' + target_developer)

        # sequence of tick positions, then a sequence of tick labels:
        matplotlib.pyplot.xticks(bar_anchors, wlabels)

        # sequence of tick positions, then a sequence of tick labels:
        matplotlib.pyplot.yticks(
            [label_position_for_upper_row, label_position_for_lower_row
             ], [target_developer + ' as reviewer\ncode reading',
                 target_developer + ' as committer\ncode authoring'])

        # be careful: it will save right over any preexisting file:
        matplotlib.pyplot.savefig(target_developer + '.png',
                                  dpi=300,
                                  bbox_inches='tight',
                                  pad_inches=0.75)

        #matplotlib.pyplot.show()

        matplotlib.pyplot.close()
