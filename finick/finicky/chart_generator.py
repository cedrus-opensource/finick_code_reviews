from __future__ import print_function
from __future__ import division  # py3 style. division promotes to floating point.
from __future__ import unicode_literals
from __future__ import absolute_import

from finicky.db_row import AssertType_DbRow, DbRow
from finicky.parse_config import AssertType_FinickConfig
from finicky.error import FinickError


class ChartGenerator(object):
    def __init__(self, finick_config, assignments):
        self.__finick_config = finick_config
        self.__assignmentlist = assignments

        AssertType_FinickConfig(self.__finick_config)

        for a in self.__assignmentlist:
            AssertType_DbRow(a)

    def draw_charts(self):

        # defer these imports until the last possible moment:
        import numpy
        import matplotlib.pyplot

        matplotlib.pyplot.clf()

        # there will be len(bar_anchors) qty of bars, sitting at these x points:
        bar_anchors = [3, 10, 12]

        # height of green portion of the bar:
        green_portion = [13, 26, 39]

        bottom_0 = [0, 0, 0]

        # units out of total height that will be yellow:
        yellow_portion = [2, 20, 0]

        bottom_1 = [x + y for x, y in zip(bottom_0, green_portion)]

        red_portion = [5, 5, 20]

        bottom_2 = [x + y for x, y in zip(bottom_1, yellow_portion)]

        blue_portion = [4, 4, 4]

        bottom_3 = [x + y for x, y in zip(bottom_2, red_portion)]

        bar_width = 0.35

        p1 = matplotlib.pyplot.bar(bar_anchors,
                                   green_portion,
                                   bar_width,
                                   color='aqua')

        p2 = matplotlib.pyplot.bar(bar_anchors,
                                   yellow_portion,
                                   bar_width,
                                   color='yellow',
                                   bottom=bottom_1)

        p3 = matplotlib.pyplot.bar(bar_anchors,
                                   red_portion,
                                   bar_width,
                                   color='red',
                                   bottom=bottom_2)

        p4 = matplotlib.pyplot.bar(bar_anchors,
                                   blue_portion,
                                   bar_width,
                                   color='blue',
                                   bottom=bottom_3)

        matplotlib.pyplot.ylabel('This side\nsecond line')  # it seems the ylabel is 90-degree rotated as you would want
        matplotlib.pyplot.title('Title goes here\nsecond line')

        # sequence of tick positions, then a sequence of tick labels:
        matplotlib.pyplot.xticks(bar_anchors, ['asomethinglong', 'b**', 'c'])

        # sequence of tick positions, then a sequence of tick labels:
        matplotlib.pyplot.yticks([0, 10, 20, 30, 40, 50],
                                 ['t-0', 't-10', 't-20', 't-30', 't-40', 't-50'
                                                     ])

        matplotlib.pyplot.show()

        matplotlib.pyplot.close()
