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
import os
from html.parser import HTMLParser

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
                try:
                    self.dosync()
                except Exception as e:
                    print(f"Error occurred while fetching MFA code from email: {e}")
                    # Optionally print a stack trace for more details
                    # import traceback
                    # traceback.print_exc()

    # The method that gets called when a new email arrives. 
    # Replace it with something better.
    def dosync(self):
        os.system('clear') 
        print("\n\n\n\n\n\n\n\n+=-*+=-*+=-*+=-*+=-*+=-*+=-*+=-*+=-*+=-*+=-*+=-*+=-*+=-*+=-*+=-*+=-*+=-*\n")
        time.sleep(.2)
#        print ("Got an event!")
        resp_code, mail_count = M.select(mailbox=source_folder, readonly=False)

        # mail_count is returned a single element list with a binary value of the count
        # int(mail_count[0]) converts this to a useful printable value

        # print(source_folder," mail count: ",int(mail_count[0]),"\n")
        
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

            for part in message.walk():
                # print ("Content type is: ", part.get_content_type())
                # print ("\n\nPART:\n",part,"\n\n")
                if part.get_content_type() == "text/html":
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
print("HOST: ",HOST)

# Had to do this stuff in a try-finally, since some testing 
# went a little wrong.....
try:
    M = imaplib2.IMAP4_SSL(HOST)
    M.login(USERNAME,PASSWORD)
    # We need to get out of the AUTH state, so we just select 
    # the INBOX.
    M.select(source_folder)
    # Start the Idler thread
    idler = Idler(M)
    idler.start()
    # Because this is just an example, exit after 1 minute.
    time.sleep(100*60)
finally:
    # Clean up.
    idler.stop()
    idler.join()
    M.close()
    # This is important!
    M.logout()
