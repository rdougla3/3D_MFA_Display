#
#   Uses "IMAP Push" feature to watch for a email arrival.  
#   and parses that email for a pin which is subsequrntly 
#   displayed. 
#
#   OZINDFW Rich Osman 30 Nov 24 for Dallas Makerspace 3D
#

import imaplib2
import time
from threading import *
import email
import configparser
import ssl
import socket
import os
from html.parser import HTMLParser
import re
from datetime import datetime
from typing import List

# Configurable delay and max timeout between reconnection attempts if network fails or IMAP server disconnects
RETRY_DELAY_SECONDS = 30
MAX_RETRIES = 20

#number of notifications shown at one time
STACK_SIZE = 5
#how long to retain old codes
CODE_DURATION = 5

#
#  HTML stripper from https://www.slingacademy.com/article/python-ways-to-remove-html-tags-from-a-string/
#

class StripHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.result = []

    def handle_data(self, data):
        self.result.append(data)

    def get_text(self):
        return ''.join(self.result)

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


def strip_html(text):
    remover = StripHTML()
    remover.feed(text)
    return remover.get_text()


#
#
#   Idle sync code based on example at:
#   https://gist.github.com/thomaswieland/3cac92843896040b11c4635f7bf61cfb
#
#   https://github.com/jazzband/imaplib2/blob/master/imaplib2/imaplib2.py
#

#
# This is the threading object that does all the waiting on
# the event
#
class Idler(object):
    def __init__(self, conn):
        self.thread = Thread(target=self.idle)
        self.M = conn
        self.event = Event()

    def start(self):
        self.thread.start()

    def stop(self):
        # This is a neat trick to make thread end. Took me a
        # while to figure that one out!
        self.event.set()

    def join(self):
        self.thread.join()

    def idle(self):
        # Do an initial sync on startup
        self.dosync_wrapper()

        # Starting an unending loop here
        while True:
            # This is part of the trick to make the loop stop
            # when the stop() command is given
            if self.event.is_set():
                return
            self.needsync = False

            # A callback method that gets called when a new
            # email arrives. Very basic, but that's good.
            def callback(args):
                if not self.event.is_set():
                    self.needsync = True
                    self.event.set()

            # Do the actual idle call. This returns immediately,
            # since it's asynchronous.
            self.M.idle(callback=callback)
            # This waits until the event is set. The event is
            # set by the callback, when the server 'answers'
            # the idle call and the callback function gets
            # called.
            self.event.wait()
            # Because the function sets the needsync variable,
            # this helps escape the loop without doing
            # anything if the stop() is called. Kinda neat
            # solution.
            if self.needsync:
                self.event.clear()
                self.dosync_wrapper()

    # Wrapper method for dosync() to do error handling and reconnect to IMAP server if disconnected.
    # This is here rather than in idle() so that we can check for MFA codes on startup without
    # needing duplicate error handling logic.
    def dosync_wrapper(self):
        try:
            self.dosync2()
        except (imaplib2.IMAP4.abort, imaplib2.IMAP4.error, socket.error) as conn_error:
            print(f"Error occurred while fetching MFA code from email: {conn_error}")
            print("Attempting to reconnect...")
            try:
                # Reconnect and update the connection in this thread (and globally)
                new_conn = connect_imap()
                self.M = new_conn
                global M
                M = new_conn
                try:
                    self.dosync2()
                except Exception as e:
                    print(
                        f"Another error occurred while fetching MFA code after reconnecting: {e}\n\nWill retry again later.")
                    pass
            except Exception as e:
                print("Failed to reconnect:", e)

    def dosync2(self):
        time.sleep(.2)
        resp_code, mails = M.search(None, 'FROM', '"Bambu Lab"')
        # If zero, not all matching criteria are met.
        if len(mails[0]) > 0:
            #Most recent email
            dat = mails[0].decode().split()[-800:]
            mail_id = dat[len(dat) -1]

            try:
                resp_code, mail_data = M.fetch(mail_id, '(RFC822)')
                messages = email.message_from_bytes(mail_data[0][1]).as_string()
                message = messages.split("Content-Type: text/plain").pop()
                message = " ".join(strip_html(message).split())
            except:
                #message not ready. This shouldn't throw loops, but we can add a break condition
                time.sleep(1)
                return self.dosync2()

            #Parse code, time body...
            codeStr = re.search("Your verification code is:\\s+\\d\\d\\d\\d\\d\\d", message).group()
            code = re.search("\\d\\d\\d\\d\\d\\d", codeStr).group()

            date = re.search("(\\d|\\d\\d)\\s+[A-Za-z]a[A-Za-z]\\s+[0-9]+\\s+(\\d|\\d\\d):(\\d|\\d\\d):(\\d|\\d\\d)\\s-\\d\\d\\d\\d", message).group()
            t: time = time.strptime(date, "%d %b %Y %H:%M:%S %z")

            body = re.search('Welcome to Bambu Lab([\\s\\S]*)Bambu Lab', message).group()

            #Push to notification stack if newer than 5 minutes
            dt = datetime(t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec)
            mins_old = (datetime.now() - dt).total_seconds() / 60
            if mins_old < CODE_DURATION:
                notificationStack.push(Notification(mail_id, t, code, body))

            print_notifications()

def print_notifications():
    RED = '\033[91m'
    YELLOW = '\033[33m'
    GREEN = '\033[92m'
    RESET = '\033[0m'
    os.system('cls' if os.name == 'nt' else 'clear')
    print("\n\n\n\n\n\n\n\n+=-*+=-*+=-*+=-*+=-*+=-*+=-*+=-*+=-*+=-*+=-*+=-*+=-*+=-*+=-*+=-*+=-*+=-*\n")
    for notification in notificationStack.stack:

        # Pop old notifications
        t = notification.time
        dt = datetime(t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec)
        mins_old = (datetime.now() - dt).total_seconds() / 60
        if mins_old > CODE_DURATION:
            notificationStack.remove(notification)

        else:
            color = GREEN if mins_old < 2 else YELLOW if mins_old < 4 else RED
            print("\n Code: ", notification.code, "\t\tTime: ", f"{color}{time.strftime('%H:%M %B %d %Y', notification.time)}{RESET}",
                  "\n\n")
    print("\n\n\n\n\n\n\n\n+=-*+=-*+=-*+=-*+=-*+=-*+=-*+=-*+=-*+=-*+=-*+=-*+=-*+=-*+=-*+=-*+=-*+=-*\n")

# Creates a connection to the configured IMAP server
def connect_imap():
    global M
    for attempt in range(MAX_RETRIES):
        try:
            new_M = imaplib2.IMAP4_SSL(HOST)
            new_M.login(USERNAME, PASSWORD)
            new_M.select(source_folder)
            print("IMAP connection successful")
            M = new_M
            return new_M
        except (imaplib2.IMAP4.abort, imaplib2.IMAP4.error, socket.error) as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY_SECONDS)
            else:
                raise


#   2BeDo
#
#   Parse mail for PIN code
#   Display Code full screen
#   move message to "PROCESSED" folder
#
#

###########################################################################
#
#
#   Main Program
#
#
###########################################################################


config = configparser.ConfigParser()
config.read('MFA_Mail.cfg')

HOST = config['DEFAULT']['HOST']
USERNAME = config['DEFAULT']['USER']
PASSWORD = config['DEFAULT']['PASS']
source_folder = "INBOX"

os.system('cls' if os.name == 'nt' else 'clear')
print("HOST: ", HOST)

M = None
idler = None

# Had to do this stuff in a try-finally, since some testing
# went a little wrong.....
try:
    print("Connecting to email server...")
    # Create the initial IMAP connection and start the idler thread
    M = connect_imap()
    idler = Idler(M)
    idler.start()

    # Main program loop. Press Ctrl+C to exit.
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("KeyboardInterrupt received. Exiting the main loop.")
finally:
    print("Cleaning up idler and IMAP connection...")
    if idler:
        print("Stopping idler thread...")
        idler.stop()
        idler.join()
    if M:
        try:
            print("Closing IMAP connection...")
            M.close()
        except:
            pass
        try:
            print("Logging out from IMAP...")
            M.logout()
        except:
            pass