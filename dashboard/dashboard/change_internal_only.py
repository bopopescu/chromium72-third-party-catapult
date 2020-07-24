# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging

from google.appengine.ext import deferred
from google.appengine.ext import ndb

from dashboard.common import datastore_hooks
from dashboard.models import graph_data


QUEUE_NAME = 'migrate-queue'
PAGE_LIMIT = 5000


@ndb.synctasklet
def UpdateBots(main_bots, internal_only):
  """Change internal_only for many Bots in parallel.

  This is not called anywhere because admins run this in dev_console.
  The Bots' TestMetadata and Anomalies are also updated.
  """
  yield [UpdateBotAsync(main, bot, internal_only)
         for main, bot in main_bots]


@ndb.synctasklet
def UpdateBotSync(main, bot, internal_only):
  """Change a Bot's internal_only.

  This is not called anywhere because admins run this in dev_console.
  The Bot's TestMetadata and Anomalies are also updated.
  """
  yield UpdateBotAsync(main, bot, internal_only)


@ndb.tasklet
def UpdateBotAsync(main, bot, internal_only):
  """Change a Bot's internal_only.

  The Bot's TestMetadata and Anomalies are also updated.
  """
  bot_entity = yield ndb.Key('Main', main, 'Bot', bot).get_async()
  bot_entity.internal_only = internal_only
  yield bot_entity.put_async()
  for kind in ['TestMetadata', 'Anomaly']:
    deferred.defer(_UpdateEntities, kind, main, bot, _queue=QUEUE_NAME)


def _UpdateEntities(kind, main, bot, start_cursor=None):
  """Update `internal_only` flags of `kind` entities to match their Bot.
  """
  datastore_hooks.SetPrivilegedRequest()
  internal_only = graph_data.Bot.GetInternalOnlySync(main, bot)

  query = ndb.Query(kind=kind).filter(
      ndb.GenericProperty('main_name') == main,
      ndb.GenericProperty('bot_name') == bot,
      ndb.GenericProperty('internal_only') == (not internal_only))
  entities, next_cursor, more = query.fetch_page(
      PAGE_LIMIT, start_cursor=start_cursor)
  for entity in entities:
    entity.internal_only = internal_only
  ndb.put_multi(entities)

  logging.info('updated %d entities', len(entities))
  if more and next_cursor:
    logging.info('continuing')
    deferred.defer(_UpdateEntities, kind, main, bot, next_cursor,
                   _queue=QUEUE_NAME)
  else:
    logging.info('complete')
