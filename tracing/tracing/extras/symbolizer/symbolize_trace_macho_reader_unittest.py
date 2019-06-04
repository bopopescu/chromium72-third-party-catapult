#!/usr/bin/env python
# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import sys
import unittest

from . import symbolize_trace_macho_reader


class AtosRegexTest(unittest.TestCase):
  def testRegex(self):
    if sys.platform != "darwin":
      return
    file_name = "/System/Library/Frameworks/IOKit.framework/Versions/A/IOKit"
    result = symbolize_trace_macho_reader.ReadMachOTextLoadAddress(file_name)
    self.assertNotEqual(None, result)

    file_name = "/System/Library/Frameworks/Cocoa.framework/Versions/A/Cocoa"
    result = symbolize_trace_macho_reader.ReadMachOTextLoadAddress(file_name)
    self.assertNotEqual(None, result)


if __name__ == '__main__':
  unittest.main()
