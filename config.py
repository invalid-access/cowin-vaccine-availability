import os

NOTIFIED_FOR_18_PLUS = False
NOTIFIED_FOR_45_PLUS = False

# Search Parameters
ZIPCODE = os.environ.get("ZIPCODE", None)
DISTRICT_ID = os.environ.get("DISTRICT_ID", "395")

# Config on what ages to notify for
CHECK_FOR_18_YRS = os.environ.get("CHECK_FOR_18_YRS", True)
CHECK_FOR_45_YRS = os.environ.get("CHECK_FOR_45_YRS", False)
CHECK_FOR_DOSE1  = os.environ.get("CHECK_FOR_DOSE1", True)
CHECK_FOR_DOSE2  = os.environ.get("CHECK_FOR_DOSE2", False)

# Slack config
SLACK_ACCESS_TOKEN = os.environ.get("SLACK_ACCESS_TOKEN", None)
SLACK_CHANNEL_ID = os.environ.get("SLACK_CHANNEL_ID", None)
SLACK_USER_ID = os.environ.get("SLACK_USER_ID", None)

# Preferred Centers
PREFERRED_CENTER_FILTER = os.environ.get("PREFERRED_CENTER_FILTER", None)
PREFERRED_CENTER_SLACK_ACCESS_TOKEN = os.environ.get("PREFERRED_CENTER_SLACK_ACCESS_TOKEN", None)
