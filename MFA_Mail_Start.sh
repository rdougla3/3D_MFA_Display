#
#	this script is calld by .bashrc to monitor MFA_Mail_OAUTH execution and 
#	restart if needed.
#
#   OZINDFW 29 March 2025
#

if pgrep -f "MFA_Mail_OAUTH.py" >/dev/null 
then
	echo "MFA_Mail_OAUTH Already Running"
	exit
else
	source mfa_env/bin/activate
	python MFA_Mail_OAUTH.py & 
	logger "MFA_Mail_OAUTH starting" 
	echo
	echo "MFA_Mail_OAUTH starting"
	date
	echo
fi
while [ true ] 
do
	if pgrep -f "MFA_Mail_OAUTH.py" >/dev/null 
	then 
		sleep 5
	else 
		echo
		echo "MFA_Mail_OAUTH not running, restarting " 
		date 
		echo
		logger "MFA_Mail_OAUTH not running, restarting " 
		source mfa_env/bin/activate
		python MFA_Mail_OAUTH.py &
	fi
done;
