# -*- coding: utf-8 -*-
import argparse

import requests

from config import TG_TOKEN, TG_WEBHOOK_MAX_CONNECTIONS, TG_WEBHOOK_URL  # pylint: disable=E0401


parser = argparse.ArgumentParser()
parser.add_argument('action', default='set', nargs='?')
parser.add_argument('--url', default=TG_WEBHOOK_URL)
parser.add_argument('--max_connections', default=TG_WEBHOOK_MAX_CONNECTIONS)
args = parser.parse_args()
print(args)

if args.action == 'set':
    url = "https://api.telegram.org/bot{0}/setWebhook?url={1}&max_connections={2}".format(
        TG_TOKEN, args.url, args.max_connections)
elif args.action == 'delete':
    url = "https://api.telegram.org/bot{0}/deleteWebhook".format(TG_TOKEN)
elif args.action == 'get':
    url = "https://api.telegram.org/bot{0}/getWebhookInfo".format(TG_TOKEN)
else:
    exit('unknown action.')

response = requests.get(url)
print(response.text)
