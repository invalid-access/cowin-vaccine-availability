import requests
import sys
from urllib.parse import urljoin

import arrow

import config
import slack_utils


BASE_URL = "https://cdn-api.co-vin.in"


def make_covin_request(request_url, params=None) -> requests.Response:
    num_retries = 3
    response = requests.get(
        request_url,
        params=params,
        headers={"Accept": "application/json", "Accept-Language": "en-US"}
    )

    while num_retries > 0:
        num_retries -= 1
        if response.ok:
            break

    response.raise_for_status()
    return response


def get_all_states():
    relative_url = "api/v2/admin/location/states"
    request_url = urljoin(BASE_URL, relative_url)
    response = make_covin_request(request_url)
    resp_json = response.json()
    states_dict = {
        state["state_id"]: state["state_name"]
        for state in resp_json["states"]
    }

    print("-------- STATES MAP --------")
    for key, value in states_dict.items():
        print(f"{key} ->> {value}")


def get_all_districts_for_state(state_id):
    relative_url = f"api/v2/admin/location/districts/{state_id}"
    request_url = urljoin(BASE_URL, relative_url)
    response = make_covin_request(request_url)
    resp_json = response.json()
    districts_dict = {
        district["district_id"]: district["district_name"]
        for district in resp_json["districts"]
    }
    print("-------- DISTRICTS MAP --------")
    for key, value in districts_dict.items():
        print(f"{key} ->> {value}")


def parse_slot_results(response: requests.Response):
    resp_json = response.json()
    centers = resp_json.get("centers")
    if not centers:
        print("No centers found")
        return

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

    if config.CENTER_FILTER:
        whitelisted_centers = [int(i) for i in config.CENTER_FILTER.split(",")]
        centers_with_available_slots = {
            k: v for k, v in centers_with_available_slots.items()
            if int(k) in whitelisted_centers
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


def check_slot_availability_by_district(district_id):
    relative_url = "api/v2/appointment/sessions/public/calendarByDistrict"
    request_url = urljoin(BASE_URL, relative_url)
    start_date = arrow.utcnow().to("Asia/Kolkata")
    count = 0
    while count < 15:
        curr_date = start_date.shift(days=count)
        print(f"Checking for date: {curr_date}")
        response = make_covin_request(
            request_url=request_url,
            params={"district_id": district_id, "date": curr_date.strftime("%d-%m-%Y")}
        )
        parse_slot_results(response)
        count += 1


def check_slot_availability_by_pincode(pincode: str):
    relative_url = "api/v2/appointment/sessions/public/calendarByPin"
    request_url = urljoin(BASE_URL, relative_url)
    start_date = arrow.utcnow().shift(days=-1).to("Asia/Kolkata")
    count = 0
    while count < 15:
        curr_date = start_date.shift(days=count)
        print(f"Checking for date: {curr_date}")
        response = make_covin_request(
            request_url=request_url,
            params={"pincode": pincode, "date": curr_date.strftime("%d-%m-%Y")},
        )
        parse_slot_results(response)
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
    print("---------- START -----------")
    if config.ZIPCODE:
        check_slot_availability_by_pincode(config.ZIPCODE)
        sys.exit(0)

    if config.DISTRICT_ID:
        check_slot_availability_by_district(config.DISTRICT_ID)
        sys.exit(0)

    print("One of ZIPCODE or DISTRICT_ID must be specified in config")

    # Gets slot availability for district 392 and notifies if slots are available.
    # check_slot_availability_by_district("392")

    # Get slot availability for pincode 400706 and notifies if slots are available.
    # check_slot_availability_by_pincode("400706")

    # Prints all states (id and name map) - Useful to fetch state_id to list districts
    # get_all_states

    # Prints all districts in state 21 (id and name map)
    # get_all_districts_for_state(21)
