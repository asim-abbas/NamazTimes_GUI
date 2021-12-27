
https://raspberrytips.com/autostart-a-program-on-boot/#:~:text=How%20to%20auto%20start%20a%20program%201%20%E2%80%93,create%20an%20upstart%20job.%20...%20Weitere%20Artikel...
*******************************************
make autoLaunch

    
Open a terminal.
    
1. crontab -e

If’s your first time in the crontab, you need to select an editor (press 1 to Enter for nano).
You get an empty crontab file, if it is the first time:
    
# Enabling crontab script audio settings
1. XDG_RUNTIME_DIR=/run/user/user_id

# Paste a line starting with reboot, and add your script command at the end of file, like this:
2. @reboot /home/pi/namazTimes/LaunchScript.sh

user_id is the id of the user running this pi
find the user_id by running the following command in cmd:

cat /etc/passwd | grep home

Example:
pi:x:1000:1000 then 1000 is the user_id
Save and exit (CTRL+O, CTRL+X with nano).

***********************************************

If audio is not working then enable it is raspi_config

sudo raspi_config

and find 'audio' in the advanced settings and enable 'audio_jack' 