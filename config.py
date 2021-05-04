import os

NOTIFIED_FOR_18_PLUS = False
NOTIFIED_FOR_45_PLUS = False

# Search Parameters
ZIPCODE = os.environ.get("ZIPCODE", None)
DISTRICT_ID = os.environ.get("DISTRICT_ID", None)
CENTER_FILTER = os.environ.get("CENTERS", None)

# Config on what ages to notify for
CHECK_FOR_18_YRS = os.environ.get("CHECK_FOR_18_YRS", True)
CHECK_FOR_45_YRS = os.environ.get("CHECK_FOR_18_YRS", True)

# Slack config
SLACK_ACCESS_TOKEN = os.environ.get("SLACK_ACCESS_TOKEN", None)
SLACK_CHANNEL_ID = os.environ.get("SLACK_CHANNEL_ID", None)
SLACK_USER_ID = os.environ.get("SLACK_USER_ID", None)
