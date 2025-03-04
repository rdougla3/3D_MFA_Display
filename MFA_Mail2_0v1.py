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

# Configurable delay and max timeout between reconnection attempts if network fails or IMAP server disconnects
RETRY_DELAY_SECONDS = 30
MAX_RETRIES = 20


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
            self.dosync()
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
                    self.dosync()
                except Exception as e:
                    print(f"Another error occurred while fetching MFA code after reconnecting: {e}\n\nWill retry again later.")
                    pass
            except Exception as e:
                print("Failed to reconnect:", e)
 
    # The method that gets called when a new email arrives. 
    # Replace it with something better.
    def dosync(self):
        os.system('clear') 
        print("\n\n\n\n\n\n\n\n+=-*+=-*+=-*+=-*+=-*+=-*+=-*+=-*+=-*+=-*+=-*+=-*+=-*+=-*+=-*+=-*+=-*+=-*\n")
        time.sleep(.2)
        # print ("Got an event!")
        resp_code, mail_count = M.select(mailbox=source_folder, readonly=False)

        # mail_count is returned a single element list with a binary value of the count
        # int(mail_count[0]) converts this to a useful printable value

        # print(source_folder," mail count: ",int(mail_count[0]),"\n")
        
        # import random
        # if random.random() < 0.3:
        #     print("!!! Randomly closing connection inside dosync to test error handling and reconnect !!!")
        #     M.close()

        # resp_code, mails = M.search(None,"UNSEEN",'FROM','"Bambu Lab"')
        resp_code, mails = M.search(None,'FROM','"Bambu Lab"')
        # resp_code, mails = M.search(None,"ALL")

        # If zero, not all matching criteria are met.  
        if len(mails[0])>0:
            # print("resp: ",mails[0][-1],"\n")
            # print ("\n\n",type(mails),"\n\n")
            # print ("\n\n",mails,"\n\n")

            for mail_id in mails[0].decode().split()[-800:]:
                resp_code, mail_data = M.fetch(mail_id, '(RFC822)') ## Fetch mail data.
                message = email.message_from_bytes(mail_data[0][1]) ## Construct Message from mail data
                # print ("\n\nMessage:\n",message,"\n\n")
                # print(message["Subject"])

            for part in message.walk():
                print("Content type is: ", part.get_content_type())
                # print ("\n\nPART:\n",part,"\n\n")
                print("\n\n",message,"\n\n")
                if part.get_content_type() == "text/plain":
                    body = part.as_string()
                    
                    # get date and time
                    dateTimeStart = body.find("Delivery-date: ")
                    dateTime = body[dateTimeStart+20 : body.find("\n",dateTimeStart) ]
                    print("Date and Time: ",dateTime,"\n")
                    msgTime = time.strptime(dateTime,"%d %b %Y %H:%M:%S %z")
                    # print ("Message time: ",msgTime,"\n")
                    # print ("Type: ",type(msgTime),"\n")
                    
                    # print("Time Zone: ",time.strftime("%d %b %Y %H:%M:%S %z",msgTime),"\n")
                    
                    textStart = body.find("<tbody>")
                    textEnd = body.find("</tbody>")
                    # print("\nSTART:",textStart," END: ",textEnd,"\n\n")

                    # this is hackage to parse for the MFA Code that needs ceaned up and commented.
                    # it's also too reliant on a fixed message format for my taste

                    #   remove excess whitespace and replace with spaces                    
                    text = " ".join(strip_html(body[textStart:textEnd]).split())
                    
                    code = text[text.find("verification code is: ")+22:text.find("verification code is: ")+22+6]
                    print("\n\n\n\n\nCODE: ",code,"\n\n")

                    print("\n\n\n\n\n\n BODY: "," ".join(strip_html(body[textStart:textEnd]).split()),"\n\n")
                    

                    # print("\n\n\n\nDUn Dun Dun \n")
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
            print(f"Attempt {attempt+1} failed: {e}")
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

os.system('clear')
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
