import requests
import sys
from urllib.parse import urljoin

import arrow

import config
import db_utils
import slack_utils


BASE_URL = "https://cdn-api.co-vin.in"


def make_covin_request(request_url, params=None) -> requests.Response:
    num_retries = 3
    response = requests.get(
        request_url,
        params=params,
        headers={
            "Accept": "application/json", 
            "Accept-Language": "en-US",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36"
        }
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

    available_sessions_with_center_info = [
        {
            "center_id": center["center_id"],
            "name": center["name"],
            "pincode": center["pincode"],
            "session_id": session["session_id"],
            "available_capacity": session["available_capacity"],
            "slot_date": session["date"],
            "min_age_limit": session["min_age_limit"],
            "vaccine": session["vaccine"],
        }
        for center in centers
        for session in center.get("sessions") or []
        if session["available_capacity"] > 0
    ]

    if not config.NOTIFIED_FOR_18_PLUS and config.CHECK_FOR_18_YRS:
        sessions_with_slots_for_18_plus = [
            s for s in available_sessions_with_center_info
            if int(s["min_age_limit"]) == 18
        ]
        if sessions_with_slots_for_18_plus:
            notify(sessions_with_slots_for_18_plus)
            config.NOTIFIED_FOR_18_PLUS = True

    if not config.NOTIFIED_FOR_45_PLUS and config.CHECK_FOR_45_YRS:
        sessions_with_slots_for_45_plus = [
            s for s in available_sessions_with_center_info
            if int(s["min_age_limit"]) == 45
        ]
        if sessions_with_slots_for_45_plus:
            notify(sessions_with_slots_for_45_plus)
            config.NOTIFIED_FOR_45_PLUS = True

    if config.NOTIFIED_FOR_18_PLUS and config.NOTIFIED_FOR_45_PLUS:
        sys.exit(0)


def check_slot_availability_by_district(district_id):
    relative_url = "api/v2/appointment/sessions/public/calendarByDistrict"
    request_url = urljoin(BASE_URL, relative_url)
    curr_date = arrow.utcnow().to("Asia/Kolkata")
    response = make_covin_request(
        request_url=request_url,
        params={"district_id": district_id, "date": curr_date.strftime("%d-%m-%Y")}
    )
    parse_slot_results(response)


def check_slot_availability_by_pincode(pincode: str):
    relative_url = "api/v2/appointment/sessions/public/calendarByPin"
    request_url = urljoin(BASE_URL, relative_url)
    curr_date = arrow.utcnow().to("Asia/Kolkata")
    response = make_covin_request(
        request_url=request_url,
        params={"pincode": pincode, "date": curr_date.strftime("%d-%m-%Y")},
    )
    parse_slot_results(response)


def notify(sessions_list):
    send_message_for_vaccine_slots(sessions_list)


def send_message_for_vaccine_slots(sessions_list):
    print(sessions_list)
    slack_access_token = config.SLACK_ACCESS_TOKEN
    if not slack_access_token:
        print("Skipping slack alert as no access token found in config")
        return

    min_age = sessions_list[0]['min_age_limit']

    send_info = db_utils.get_send_info()

    whitelisted_centers = []
    if config.PREFERRED_CENTER_FILTER:
        whitelisted_centers = [int(i) for i in config.PREFERRED_CENTER_FILTER.split(",")]

    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"Vaccination slots for age {min_age} plus are available in following centers"
            }
        }
    ]

    preferred_center_blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"Vaccination slots for age {min_age} plus are available in following centers"
            }
        }
    ]

    for session_info in sessions_list:
        # Add to send_info it doesn't exist
        session_id = session_info["session_id"]
        if session_id not in send_info:
            send_info[session_id] = {
                "num_sends": 0
            }

        last_send_info = send_info[session_id]
        if last_send_info["num_sends"] > 5:
            last_send_dt = arrow.get(last_send_info["last_send_dt"])
            if arrow.utcnow() < last_send_dt.shift(hours=1):
                # Don't send notifications for a session more than 5 times in a 1 hour window.
                continue

            # Reset num_sends as rate limit doesn't apply here.
            send_info[session_id] = {
                "num_sends": 0
            }

        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "plain_text",
                    "text": f"{session_info['name']}({session_info['pincode']}) -> {session_info['available_capacity']} -> {session_info['vaccine']} -> {session_info['slot_date']}"
                }
            ]
        })

        if whitelisted_centers and int(session_info["center_id"]) in whitelisted_centers:
            preferred_center_blocks.append({
                "type": "context",
                "elements": [
                    {
                        "type": "plain_text",
                        "text": f"{session_info['name']}({session_info['pincode']}) -> {session_info['available_capacity']} -> {session_info['vaccine']} -> {session_info['slot_date']}"
                    }
                ]
            })

        send_info[session_id] = {
            "last_send_dt": str(arrow.utcnow()),
            "num_sends": send_info[session_id]["num_sends"] + 1,
            "center_name": session_info["name"],
        }

    if len(blocks) == 1:
        print(f"No new notifications to send for {min_age}. Returning.")
        return

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

    if len(preferred_center_blocks) > 1 and config.PREFERRED_CENTER_SLACK_ACCESS_TOKEN:
        slack_utils.send_message(
            access_token=config.PREFERRED_CENTER_SLACK_ACCESS_TOKEN,
            text=f"Vaccination slots for age {min_age} plus are open!",
            blocks=preferred_center_blocks,
            slack_channel_ids=slack_channel_ids,
            slack_user_ids=slack_user_ids,
        )

    db_utils.set_send_info(send_info)


if __name__ == "__main__":
    print(f"---------- START {arrow.utcnow().to('Asia/Kolkata')} -----------")
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
