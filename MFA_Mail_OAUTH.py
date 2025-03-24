import base64
import os
import re
import time
from datetime import datetime, timedelta, timezone
from typing import List

from google.cloud import pubsub_v1
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

PROJECT_ID = 'bambu-mfa-with-oauth'
TOPIC_ID = 'bambu-mfa-emails'
SUBSCRIPTION_ID = 'bambu-mfa-emails-sub'
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

STACK_SIZE = 5
CODE_DURATION = 5

class Notification:
    id: str
    time: time
    code: int
    body: str
    def __init__(self, id_=None, time_=None, code_=None, body_=None):
        self.id = id_
        self.time = time_
        self.code = code_
        self.body = body_

class FixedStack:
    stack: List[Notification]
    def __init__(self, stack):
        self.stack = []
    def push(self, data: Notification):
        self.stack.append(data)
        if len(self.stack) > STACK_SIZE:
            self.stack.reverse(); self.stack.pop(); self.stack.reverse()
    def remove(self, notification):
        return self.stack.remove(notification)

notificationStack = FixedStack([])

def callback(message: pubsub_v1.subscriber.message.Message) -> None:
    print(f"Received {message}.")
    t = message.publish_time

    try:
        result = gmail.users().messages().list(userId="me", maxResults=1).execute()
        mail_id = result.get('messages').pop().get('id')
        raw = gmail.users().messages().get(userId="me", id=mail_id, format='raw').execute()
        body = raw.get('snippet')

        codeStr = re.search("Your verification code is: \\d\\d\\d\\d\\d\\d", body).group()
        code = re.search("\\d\\d\\d\\d\\d\\d", codeStr).group()

        mins_old = (datetime.now(timezone.utc) - t).total_seconds() / 60
        notification = Notification(mail_id, t, code, body)
        if mins_old < CODE_DURATION:
            notificationStack.push(Notification(mail_id, t, code, body))
            print_notifications()

    except:
        pass

    message.ack()

def main():
    connect_oauth()

    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(PROJECT_ID, SUBSCRIPTION_ID)

    streaming_pull_future = subscriber.subscribe(subscription_path, callback=callback)
    print(f"Listening for messages on {subscription_path}..\n")

    # This is our loop, which calls callback() whenever there is a push notification for an email.
    with subscriber:
        try:
            # When `timeout` is not set, result() will block indefinitely,
            # unless an exception is encountered first.
            streaming_pull_future.result()
            print()
        except TimeoutError:
            streaming_pull_future.cancel()  # Trigger the shutdown.
            streaming_pull_future.result()  # Block until the shutdown is complete.


def connect_oauth():
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    try:
        # Call the Gmail API
        service = build("gmail", "v1", credentials=creds)
        global gmail
        gmail = service

    except HttpError as error:
        print(f"An error occurred: {error}")


def print_notifications():
    RED = '\033[91m'
    YELLOW = '\033[33m'
    GREEN = '\033[92m'
    RESET = '\033[0m'
    os.system('cls' if os.name == 'nt' else 'clear')
    # Coalesce
    for notification in notificationStack.stack:
        any_mach = len(list(filter(lambda n: n.id == notification.id, notificationStack.stack))) > 1
        if any_mach:
            notificationStack.stack.remove(notification)
    print("\n\n\n\n\n\n\n\n+=-*+=-*+=-*+=-*+=-*+=-*+=-*+=-*+=-*+=-*+=-*+=-*+=-*+=-*+=-*+=-*+=-*+=-*\n")
    for notification in notificationStack.stack:
        # Pop old notifications
        mins_old = (datetime.now(timezone.utc) - notification.time).total_seconds() / 60
        if mins_old > CODE_DURATION:
            notificationStack.remove(notification)

        else:
            color = GREEN if mins_old < 2 else YELLOW if mins_old < 4 else RED
            print("\n Code: ", notification.code, "\t\tTime: ", f"{color}{datetime.strftime(notification.time, '%H:%M %B %d %Y')}{RESET}","\n\n")

    print("\n\n\n\n\n\n\n\n+=-*+=-*+=-*+=-*+=-*+=-*+=-*+=-*+=-*+=-*+=-*+=-*+=-*+=-*+=-*+=-*+=-*+=-*\n")

if __name__=="__main__":
    main()