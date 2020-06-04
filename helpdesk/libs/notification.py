# coding: utf-8
import logging
from sentry_sdk import capture_exception

from sa_tools_core.client import Client
import requests
from helpdesk.config import SLACK_WEBHOOK_URL

logger = logging.getLogger(__name__)
notify = Client().notify


def send_slack(subject, body, truncate=True):
    body = body.replace("\n\n", "\n")
    if truncate:
        bodies = body.split('\n')
        if len(bodies) > 10:
            bodies = bodies[:3] + ["..."] + bodies[-3:]
        tmp = []
        for line in bodies:
            if len(line) > 160:
                line = "%s ..." % line[:160]
            tmp.append(line)
        bodies = tmp
        body = '\n'.join(bodies)
    text = '`%s`\n```%s```' % (subject, body)
    session = requests.Session()
    session.mount("https://", requests.adapters.HTTPAdapter(max_retries=5))
    try:
        r = session.post(SLACK_WEBHOOK_URL, json={"text": text}, timeout=3)
        r.raise_for_status()
    except Exception as e:
        capture_exception(e)