from typing import List, Optional

from slack import WebClient
from slack.errors import SlackApiError


def _fetch_open_slack_conversations(client: WebClient, slack_user_ids: List[str]):
    return client.conversations_open(users=slack_user_ids)


def _join_slack_conversation(client: WebClient, channel: str):
    return client.conversations_join(channel=channel)


def _post_slack_message(
    client: WebClient,
    channel: str,
    text: str,
    blocks: List[dict]
):

    return client.chat_postMessage(
        channel=channel,
        text=text,
        blocks=blocks,
    )


def send_message(
    access_token: str,
    text: str,
    blocks: List[dict],
    # At least one of slack_channel_ids and slack_user_ids needs to be specified
    slack_channel_ids: Optional[List[str]] = None,
    slack_user_ids: Optional[List[str]] = None,
):

    if not text and not blocks:
        return

    channel: str = slack_channel_ids[0] if slack_channel_ids else ""
    client = WebClient(token=access_token)

    try:
        if slack_user_ids:
            # Use conversations.open Slack API to get channel IDs from slack_user_ids
            response = _fetch_open_slack_conversations(
                client=client,
                slack_user_ids=slack_user_ids
            )
            channel = response["channel"]["id"]

        # Use chat.postMessage Slack API to post message to named #channel or group conversation
        return _post_slack_message(
            client=client,
            channel=channel,
            text=text,
            blocks=blocks,
        )
    except SlackApiError as e:
        if e.response["error"] == "not_in_channel":
            try:
                # Attempt to join and post message
                _join_slack_conversation(client=client, channel=channel)
                return _post_slack_message(
                    client=client,
                    channel=channel,
                    text=text,
                    blocks=blocks,
                )
            except SlackApiError:
                print("Received not_in_channel error, and join+retry attempt failed")
        else:
            print(f"First send attempt failed with an unexpected error: {e}")
