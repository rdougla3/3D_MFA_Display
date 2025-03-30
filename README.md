# 3D_MFA_Display

Python script that monitors a push IMAP account for multifactor authentication (MFA) codes and displays them on the console.

The imaplib2 is on PyPi and the docs are (currently) here: https://imaplib2.readthedocs.io/en/latest/index.html

Displays 5 most recent codes, color coding them for expiration 
* GREEN = recent
* YELLOW = aging
* RED = under a minute to expiration
* blanks those no longer valid.

