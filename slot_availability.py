import requests
import sys
from urllib.parse import urljoin

import arrow

import config
import slack_utils


BASE_URL = "https://cdn-api.co-vin.in"


def get_slots_for_pincode(url, pincode, curr_date):
    response = requests.get(
        url,
        params={"pincode": pincode, "date": curr_date},
        headers={"Accept": "application/json", "Accept-Language": "en-US"}
    )
    response.raise_for_status()
    resp_json = response.json()
    centers = resp_json.get("centers")
    if not centers:
        print("No centers found in the given pincode")
        sys.exit(-1)

    centers_with_available_slots = {
        center["center_id"]: {
            "name": center["name"],
            "available_capacity": center["sessions"][0]["available_capacity"],
            "min_age_limit": center["sessions"][0]["min_age_limit"],
            "vaccine": center["sessions"][0]["vaccine"],
        }
        for center in centers
        if center.get("sessions") and center["sessions"][0]["available_capacity"] > 0
    }

    if not config.NOTIFIED_FOR_18_PLUS and config.CHECK_FOR_18_YRS:
        centers_with_slots_for_18_plus = {
            k: v for k, v in centers_with_available_slots.items() if v["min_age_limit"] == 18
        }
        if centers_with_slots_for_18_plus:
            notify(centers_with_slots_for_18_plus)
            config.NOTIFIED_FOR_18_PLUS = True

    if not config.NOTIFIED_FOR_45_PLUS and config.CHECK_FOR_45_YRS:
        centers_with_slots_for_45_plus = {
            k: v for k, v in centers_with_available_slots.items() if v["min_age_limit"] == 45
        }
        if centers_with_slots_for_45_plus:
            notify(centers_with_slots_for_45_plus)
            config.NOTIFIED_FOR_45_PLUS = True

    if config.NOTIFIED_FOR_18_PLUS and config.NOTIFIED_FOR_45_PLUS:
        sys.exit(0)


def check_slot_availability(pincode: str):
    relative_url = "api/v2/appointment/sessions/calendarByPin"
    request_url = urljoin(BASE_URL, relative_url)
    start_date = arrow.utcnow().to("Asia/Kolkata")
    count = 0
    while count < 15:
        curr_date = start_date.shift(days=count)
        print(f"Checking for date: {curr_date}")
        get_slots_for_pincode(
            url=request_url, pincode=pincode, curr_date=curr_date.strftime("%d-%m-%Y")
        )
        count += 1


def notify(centers_dict):
    send_message_for_vaccine_slots(centers_dict)


def send_message_for_vaccine_slots(centers_dict):
    slack_access_token = config.SLACK_ACCESS_TOKEN
    if not slack_access_token:
        print("Skipping slack alert as no access token found in config")
        return

    min_age = list(centers_dict.values())[0]['min_age_limit']

    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"Vaccination slots for age {min_age} plus are available in following centers"
            }
        }
    ]

    for center_id, center_metadata in centers_dict.items():
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "plain_text",
                    "text": f"{center_metadata['name']} -> {center_metadata['available_capacity']} -> {center_metadata['vaccine']}"
                }
            ]
        })

    slack_channel_ids = []
    if config.SLACK_CHANNEL_ID:
        slack_channel_ids = [config.SLACK_CHANNEL_ID]

    slack_user_ids = []
    if config.SLACK_USER_ID:
        slack_user_ids = [config.SLACK_USER_ID]

    slack_utils.send_message(
        access_token=slack_access_token,
        text=f"Vaccination slots for age {min_age} plus are open!",
        blocks=blocks,
        slack_channel_ids=slack_channel_ids,
        slack_user_ids=slack_user_ids,
    )


if __name__ == "__main__":
    check_slot_availability(config.ZIPCODE)
