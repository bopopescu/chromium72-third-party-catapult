# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import unittest

from dashboard import find_change_points
from dashboard.common import math_utils


class FindChangePointsTest(unittest.TestCase):

  def testFindChangePoints(self):
    # Simple test that the output is as expected for a clear change.
    # Tests for specific aspects of the algorithm are below.
    data = [1, 1, 2, 1, 1, 8, 8, 8, 9, 8, 9]
    series = list(enumerate(data))
    expected = [
        find_change_points.ChangePoint(
            x_value=5,
            median_before=1,
            median_after=8,
            window_start=1,
            window_end=10,
            size_before=4,
            size_after=6,
            relative_change=7,
            std_dev_before=0.4330127018922193,
            t_statistic=-24.452628375754593,
            degrees_of_freedom=6.9938793160801023,
            p_value=0.001)
    ]
    actual = find_change_points.FindChangePoints(
        series,
        max_window_size=10,
        multiple_of_std_dev=3,
        min_relative_change=0.5,
        min_absolute_change=1,
        min_steppiness=0.4,
        min_segment_size=3)
    self.assertEqual(expected, actual)

  def testFindChangePoints_EmptySeries(self):
    # For an empty series, there are certainly no change points.
    self.assertEqual([], find_change_points.FindChangePoints([]))

  def testFindSplit(self):
    # Find split returns the first index of the segment after the split.
    self.assertEqual(3, find_change_points._FindSplit([3, 2, 3, 5, 6, 5]))

    # If there are several splits that are equally interesting, or no
    # interesting splits, then the first one is returned.
    self.assertEqual(2, find_change_points._FindSplit([2, 2, 4, 4, 6, 6]))
    self.assertEqual(1, find_change_points._FindSplit([4, 4, 4, 4, 4, 4]))

  def _PassesThresholds(
      self, data, index, multiple_of_std_dev=0, min_relative_change=0,
      min_absolute_change=0, min_segment_size=0, min_steppiness=0):
    """Tests whether a split passes the thresholds with the given parameters."""
    # All of the threshold parameters are set to zero by default here, so that
    # we can test just one threshold at a time.
    return find_change_points._PassesThresholds(
        data, index,
        min_segment_size=min_segment_size,
        min_absolute_change=min_absolute_change,
        min_relative_change=min_relative_change,
        min_steppiness=min_steppiness,
        multiple_of_std_dev=multiple_of_std_dev)

  def testIsAnomalous_FiltersOnSegmentSize(self):
    sample = [1, 1, 5, 5, 5, 9, 9]
    self.assertFalse(self._PassesThresholds(sample, 2, min_segment_size=3))
    self.assertFalse(self._PassesThresholds(sample, 5, min_segment_size=3))
    self.assertTrue(self._PassesThresholds(sample, 2, min_segment_size=2))
    self.assertTrue(self._PassesThresholds(sample, 5, min_segment_size=2))

  def testIsAnomalous_FiltersOnAbsoluteChange(self):
    sample = [2, 2, 2, 4, 4, 4, 4, 8, 8, 8]
    self.assertTrue(self._PassesThresholds(sample, 7))
    self.assertTrue(self._PassesThresholds(sample, 7, min_absolute_change=4))
    self.assertFalse(self._PassesThresholds(sample, 3, min_absolute_change=4))

  def testIsAnomalous_FiltersOnRelativeChange(self):
    sample = [2, 2, 2, 6, 6, 6, 6, 10, 10, 10]
    self.assertTrue(self._PassesThresholds(sample, 3))
    self.assertTrue(self._PassesThresholds(sample, 3, min_relative_change=1))
    self.assertFalse(self._PassesThresholds(sample, 7, min_relative_change=1))

  def testIsAnomalous_FiltersOnMultipleOfStdDev(self):
    # In the first sample, the standard deviation on either side of index 5
    # is between 2 and 4. In the second sample, the standard deviation within
    # each of the two segments is 0.
    noisy = [2, 8, 5, 1, 7, 13, 19, 10, 15, 17]
    steady = [5, 5, 5, 5, 5, 15, 15, 15, 15, 15]
    self.assertTrue(self._PassesThresholds(steady, 5, multiple_of_std_dev=1))
    self.assertTrue(self._PassesThresholds(steady, 5, multiple_of_std_dev=8))
    self.assertTrue(self._PassesThresholds(noisy, 5, multiple_of_std_dev=1))
    self.assertFalse(self._PassesThresholds(noisy, 5, multiple_of_std_dev=8))

  def testIsAnomalous_MultipleOfStdDevFilter_LowOnOneSide(self):
    # The standard deviation to use is the lower of the standard deviations
    # of the two sides, so if either side doesn't have a high standard
    # deviation then an alert can be fired.
    left = [3, 2, 3, 4, 3, 5, 30, 1, 50, 10]
    right = [5, 30, 1, 50, 10, 3, 2, 3, 4, 3]
    # Note that stddev([3, 2, 3, 4, 3]) is less than 1, and the difference
    # between the medians of the two sides is 7.
    self.assertTrue(self._PassesThresholds(left, 5, multiple_of_std_dev=7))
    self.assertTrue(self._PassesThresholds(right, 5, multiple_of_std_dev=7))

  def testZeroMedian_ReturnsValuesWithMedianEqualToZero(self):
    # The _ZeroMedian function adjusts values so that the median is zero.
    self.assertEqual([0, 0, 1], find_change_points._ZeroMedian([1, 1, 2]))
    self.assertEqual([-0.5, 0.5], find_change_points._ZeroMedian([45, 46]))

  def testZeroMedian_ResultProperties(self):
    nums = [3.4, 8, 100.2, 78, 3, -4, 12, 3.14, 1024]
    zeroed_nums = find_change_points._ZeroMedian(nums)
    # The output of _ZeroMedian has the same standard deviation as the input.
    self.assertEqual(
        math_utils.StandardDeviation(nums),
        math_utils.StandardDeviation(zeroed_nums))
    # Also, the median of the output is always zero.
    self.assertEqual(0, math_utils.Median(zeroed_nums))

  def _AssertFindsChangePoints(
      self, y_values, expected_indexes, max_window_size=50, min_segment_size=6,
      min_absolute_change=0, min_relative_change=0.01, min_steppiness=0.4,
      multiple_of_std_dev=2.5):
    """Asserts that change points are found at particular indexes."""
    series = list(enumerate(y_values))
    results = find_change_points.FindChangePoints(
        series,
        max_window_size=max_window_size,
        min_segment_size=min_segment_size,
        min_absolute_change=min_absolute_change,
        min_relative_change=min_relative_change,
        min_steppiness=min_steppiness,
        multiple_of_std_dev=multiple_of_std_dev)
    actual_indexes = [a.x_value for a in results]
    self.assertEqual(expected_indexes, actual_indexes)

  def testFindChangePoints_ShortSequences(self):
    self._AssertFindsChangePoints(
        [1, 1, 1, 5, 5, 5, 5, 9, 9, 9], [3],
        max_window_size=10, min_segment_size=3)
    self._AssertFindsChangePoints(
        [1, 1, 5, 5, 5, 5, 9, 9, 9, 9], [6],
        max_window_size=10, min_segment_size=3)
    self._AssertFindsChangePoints(
        [1, 1, 1, 1, 5, 5, 5, 5, 9, 9, 9], [8],
        max_window_size=11, min_segment_size=3)
    self._AssertFindsChangePoints(
        [1, 1, 1, 5, 5, 5, 5, 9, 9, 9, 9], [3],
        max_window_size=11, min_segment_size=3)
    self._AssertFindsChangePoints(
        [1, 1, 5, 5, 5, 5, 9, 9, 9, 9, 9], [6],
        max_window_size=11, min_segment_size=3)

  def testChangePoint_CanBeMadeAndConvertedToDict(self):
    series = list(enumerate([4, 4, 4, 8, 8, 8, 8]))
    change_point = find_change_points.MakeChangePoint(series, 3)
    self.assertEqual(
        find_change_points.ChangePoint(
            x_value=3, median_before=4.0, median_after=8.0, size_before=3,
            size_after=4, window_start=0, window_end=6, relative_change=1.0,
            std_dev_before=0.0, t_statistic=float('inf'),
            degrees_of_freedom=1.0, p_value=0.001),
        change_point)
    self.assertEqual(
        {
            'x_value': 3,
            'median_before': 4.0,
            'median_after': 8.0,
            'size_before': 3,
            'size_after': 4,
            'window_start': 0,
            'window_end': 6,
            'relative_change': 1.0,
            'std_dev_before': 0.0,
            't_statistic': float('inf'),
            'degrees_of_freedom': 1.0,
            'p_value': 0.001,
        },
        change_point.AsDict())


if __name__ == '__main__':
  unittest.main()
