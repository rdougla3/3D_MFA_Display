#
#	this script is calld by .bashrc to monitor MFA_Mail execution and 
#	restart if needed.
#
#   OZINDFW 29 March 2025
#

if pgrep -f "MFA_Mail.py" >/dev/null 
then
	echo "MFA_Mail Already Running"
	exit
else
	source mfa_env/bin/activate
	python MFA_Mail.py & 
	logger "MFA_Mail starting" 
	echo
	echo "MFA_Mail starting"
	date
	echo
fi
while [ true ] 
do
	if pgrep -f "MFA_Mail.py" >/dev/null 
	then 
		sleep 5
	else 
		echo
		echo "MFA_Mail not running, restarting " 
		date 
		echo
		logger "MFA_Mail not running, restarting " 
		source mfa_env/bin/activate
		python MFA_Mail.py &
	fi
done;
