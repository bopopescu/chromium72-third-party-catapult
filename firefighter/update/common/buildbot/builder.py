# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import urllib

from common.buildbot import builds
from common.buildbot import network


def Builders(main_name):
  builder_data = network.FetchData(network.BuildUrl(
      main_name, 'json/builders'))
  return sorted(Builder(main_name, builder_name, builder_info)
                for builder_name, builder_info in builder_data.iteritems())


class Builder(object):

  def __init__(self, main_name, name, data):
    self._main_name = main_name
    self._name = name
    self._url = network.BuildUrl(
        main_name, 'builders/%s' % urllib.quote(self.name))
    self._builds = builds.Builds(main_name, name, self._url)

    self.Update(data)

  def __lt__(self, other):
    return self.name < other.name

  def __str__(self):
    return self.name

  def Update(self, data=None):
    if not data:
      data = network.FetchData(network.BuildUrl(
          self.main_name, 'json/builders/%s' % urllib.quote(self.name)))
    self._state = data['state']
    self._pending_build_count = data['pendingBuilds']
    self._current_builds = frozenset(data['currentBuilds'])
    self._cached_builds = frozenset(data['cachedBuilds'])
    self._subordinates = frozenset(data['subordinates'])

  @property
  def main_name(self):
    return self._main_name

  @property
  def name(self):
    return self._name

  @property
  def url(self):
    return self._url

  @property
  def state(self):
    return self._state

  @property
  def builds(self):
    return self._builds

  @property
  def pending_build_count(self):
    return self._pending_build_count

  @property
  def current_builds(self):
    """Set of build numbers currently building.

    There may be multiple entries if there are multiple build subordinates.
    """
    return self._current_builds

  @property
  def cached_builds(self):
    """Set of builds whose data are visible on the main in increasing order.

    More builds may be available than this.
    """
    return self._cached_builds

  @property
  def available_builds(self):
    return self.cached_builds - self.current_builds

  @property
  def last_build(self):
    """Last completed build."""
    return max(self.available_builds)

  @property
  def subordinates(self):
    return self._subordinates
