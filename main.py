'''
--------Asim's Simple Smart Solutions----------------

Python Program for namaz timings alert

Version 1.0 - 11.11.2021

Coded By: Asim Abbas(asim1911@hotmail.com)
          Electrical Engineer
          
Hardware Included:
1. Raspberry Pi 3
2. HDMI display
3. AUX cable to play azan sound


**************************************************************************

CONFIDENTIAL
_________

The application is provided for the purpose of calculating namaz (prayer times)
for the Masjid in Sudenburg, Magdeburg, Germany

**************************************************************************

'''

raspberryOS = True        # Setting to true if raspberry pi OS otherwise false

# Setting the kivy environment variable
# (https://kivy.org/doc/stable/guide/environment.html)

if raspberryOS:
    import os
    os.environ["KIVY_GL_BACKEND"]="gl"
    os.environ["KIVY_WINDOW"]="egl_rpi"
    os.environ["KIVY_BCM_DISPMANX_ID"]="2"

## Kivy configuration
from kivy.config import Config
Config.set('graphics', 'width', '1280')
Config.set('graphics', 'height', '1024')
Config.set('kivy', 'exit_on_escape', '1')

## Importing kivy libraries
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.core.window import Window
from kivy.uix.scatter import Scatter
from kivy.uix.textinput import TextInput
from kivy.clock import Clock, ClockEvent
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.graphics.context_instructions import Color
from kivy.graphics.vertex_instructions import Rectangle
from kivy.properties import ListProperty, ObjectProperty, NumericProperty

import re                                   # for splitting of strings
import datetime                             # for calculating date and time
import math                                 # for ceil and floor
import time as tm                           # for calculating time span
from datetime import date, timedelta, datetime, time
from numpy_ringbuffer import RingBuffer

import numpy as np
import prayerTimes as pT
import pygame


# Writing the log file with date and time in file name
_write2file = True                                         # Flag to check if write to file or not
_fileName   = '/home/pi/namazTimes/log'+str(date.today())+'.txt'
if _write2file:
    with open(_fileName, 'a+') as filehandle:
        logMsg = str(datetime.now().strftime("%d-%m-%Y %H:%M:%S")) + str('Starting the prayer times system \n\n')
        filehandle.write(logMsg)
        
# Class communicating with SMART.kv file in folder
class NAMAZTIMESWidget(BoxLayout):
    
    def __init__(self,**kwargs):

        self._updateGUI_ClockEvent                                  = []    # Clock triggering
        self._updateTime                                            = 1     # Time in seconds after which new value will be received
        self._updateTimeNamaz                                       = 15    # Time counter (multiple of updateTime) after which the namaz time should be updated
        self._timeCounter                                           = 0     # Time counter to measure the elapsedTime
        self._firstStart                                            = True  # Flag to check if its the first start  

        ## Prayer Settings
        self._longitude                                             = 11.62916  # Longitude of Magdeburg Germany
        self._latitude                                              = 52.12773  # Latitude of Magdeburg Germany
        self._gmt                                                   = 1         # GMT zone of Germany (It differs in Winter and Summer, Winter = +1, Summer = +2)
        self._summerTime                                            = date.today()
        self._winterTime                                            = date.today()
        self._isSummer                                              = True  # Flag to check if its summer or winter time

        self._azaanTimesToday                                       = []    # Array of azan times calculated - Today
        self._azaanTimesTomorrow                                    = []    # Array of azan times calculated - Tomorrow
        self._azaanTimes                                            = []    # Array of azaan times calculated
        self._jamaatTimes                                           = []    # Array of jamaat times calculated
        self._prayerTimesOBJ                                        = []    # Object of prayerTimes module

        ## Jamaat Settings - Jamaat after x minutes
        self._fajarJamaat                                           = 30    # Fajar jamaat after 30 minutes of azaan
        self._delayJamaatMinutes_5                                  = 5     # Jamaat after 5 minutes maximum
        self._delayJamaatMinutes_10                                 = 10    # Jamaat after 10 minutes
        self._roundOffMinutes                                       = 5     # roundOff the jamaat timing to the nearest roundOff minutes
        self._roundOffMinutesMaghrib                                = 5     # roundOff maghrib to nearest 5 minutes because time is very short

        ## Jumma Khutba Timings
        self._jummaSummerTime1                                      = "13:45" # Jumma time for summer
        self._jummaSummerTime2                                      = "14:30" # Jumma time for summer
        self._jummaWinterTime1                                      = "12:20" # Jumma time for Winter
        self._jummaWinterTime2                                      = "13:10" # Jumma time for Winter

        ## Alarm/notification settings
        self._oldDate                                               = date.today()  # record of old date
        self._notificationPopup                                     = []            # notification popup
        self._isNotification                                        = False         # flag that if notification is active
        self._notificationStartTime                                 = tm.time()   # start time of notification
        self._notificationShowTime                                  = 120           # notification show time in seconds

        ## AzanFlags
        self._azaanFlags                                            = {'fajr': False, 'dhuhr': False, 'asr': False, 'maghrib': False, 'isha': False}
        
        return super(NAMAZTIMESWidget, self).__init__(**kwargs)
    
# Configuration of scheduling events
    def showMainscreen(self, *args):
        
        # Calling in function so that system will write configuration first
        self.configurePrayerTimes()
        
        # Getting ultrasonic data after a specific inteval
        self._updateGUI_ClockEvent = Clock.schedule_interval(self.updateGUI, self._updateTime)

    '''
    Show popup displaying the name of the current azan time
    '''
    def notifyPopup(self, imageName):

        imgSource = ""

        # Name of the image to be loaded
        if imageName == 'fajr':
            imgSource = '/home/pi/namazTimes/fajrNotify.png'
        elif imageName == 'dhuhr':
            imgSource = '/home/pi/namazTimes/dhuhrNotify.png'
        elif imageName == 'asr':
            imgSource = '/home/pi/namazTimes/asrNotify.png'
        elif imageName == 'maghrib':
            imgSource = '/home/pi/namazTimes/maghribNotify.png'
        elif imageName == 'isha':
            imgSource = '/home/pi/namazTimes/ishaNotify.png'
        
        self._notificationPopup = Popup(title='Notification',
                                        content=Image(source = imgSource),
                                        size_hint=(None, None), size=(600,600), auto_dismiss = False)
        
        # Open the notification
        self._notificationPopup.open()
        self._isNotification                = True
        self._notificationStartTime         = tm.time()

        # play azan sound
        self.playAzan()

        # writing to log file
        if _write2file:
            logMsg = str(datetime.now().strftime("%d-%m-%Y %H:%M:%S")) + str(' : Notification for ') + str(imageName) + str('\n')
            with open(_fileName, 'a+') as filehandle:
                filehandle.write(logMsg)
        
    '''
    Play azan sound
    '''
    def playAzan(self, *args):
        
        # azan alarm
        pygame.mixer.init()
        pygame.mixer.music.load('/home/pi/namazTimes/hayyaAllalSalah.mp3')
        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy() == True:
            continue

    '''
    Check if its azan time then play the azan sound
    '''
    def notifyAzan(self, *args):

        currTime = datetime.now().strftime("%H:%M")
        
        if not self._firstStart:
            if not self._azaanFlags['fajr']:
                if self.isAzanTime(str(self._azaanTimes['fajr']), str(currTime)):
                    self._azaanFlags['fajr'] = True
                    self.notifyPopup('fajr')

            if not self._azaanFlags['dhuhr']:
                if self.isAzanTime(str(self._azaanTimes['dhuhr']), str(currTime)):
                    self._azaanFlags['dhuhr'] = True
                    self.notifyPopup('dhuhr')

            if not self._azaanFlags['asr']:
                if self.isAzanTime(str(self._azaanTimes['asr']), str(currTime)):
                    self._azaanFlags['asr'] = True
                    self.notifyPopup('asr')

            if not self._azaanFlags['maghrib']:
                if self.isAzanTime(str(self._azaanTimes['maghrib']), str(currTime)):
                    self._azaanFlags['maghrib'] = True
                    self.notifyPopup('maghrib')
                    
            if not self._azaanFlags['isha']:
                if self.isAzanTime(str(self._azaanTimes['isha']), str(currTime)):
                    self._azaanFlags['isha'] = True
                    self.notifyPopup('isha')

    '''
    Check if time is matched
    '''
    def isAzanTime(self, scheduledTime, currTime):
        isTime = False

        azan        = re.split(':', str(scheduledTime))
        curr        = re.split(':', str(currTime))

        if (int(azan[0]) == int(curr[0])) and (int(azan[1]) == int(curr[1])):
            print('Azan')
            isTime = True
        
        return isTime    
        
# Update the App GUI     
    def updateGUI(self, *args):

        self._timeCounter = self._timeCounter + 1

        self.notifyAzan()

        # If notification is open then wait and close it
        if self._isNotification:
            if tm.time() - self._notificationStartTime >= self._notificationShowTime:
                self._notificationPopup.dismiss()
                self._isNotification = False
        
        _today                                              = date.today()
        _yearToday                                          = _today.year
        _monthToday                                         = _today.month
        _dayToday                                           = _today.day

        _tomorrow                                           = _today + timedelta(1)
        _yearTomorrow                                       = _tomorrow.year;
        _monthTomorrow                                      = _tomorrow.month;
        _dayTomorrow                                        = _tomorrow.day;

        self._summerTime                                    = date(_yearToday, 3 , 28) # 28 March
        self._winterTime                                    = date(_yearToday, 10 , 31) # 31 October

        currentTime                                         = datetime.now().strftime("%H:%M:%S")
        currentDate                                         = date(_yearToday,_monthToday,_dayToday)

        if self._summerTime <= _today <= self._winterTime:
            self._isSummer      = True
            self._gmt           = 2
        else: # Winter Time
            self._isSummer      = False
            self._gmt           = 1

        # if new day then reset all flags
        if self._oldDate != _today:
            self._oldDate               = _today
            self._azaanFlags['fajr']    = False
            self._azaanFlags['dhuhr']   = False
            self._azaanFlags['asr']     = False
            self._azaanFlags['maghrib'] = False
            self._azaanFlags['isha']    = False
            
        '''
        Update date and time of the GUI
        '''
        self.ids.timeAzan_Label.text                            = str(currentTime)
        self.ids.dateAzan_Label.text                            = str(currentDate)

        self.ids.timeJamaat_Label.text                          = str(currentTime)
        self.ids.dateJamaat_Label.text                          = str(currentDate)

        self.ids.timeJummaJamaat_Label.text                     = str(currentTime)
        self.ids.dateJummaJamaat_Label.text                     = str(currentDate)

        self.ids.timeClock_Label.text                           = str(currentTime)

        
        if self._firstStart or (self._timeCounter % self._updateTimeNamaz) == 0:
            self._firstStart = False

            if (self._timeCounter % self._updateTimeNamaz) == 0:
                self._timeCounter = 0
                
            # Calculate today's and tomorrows azaan times
            self._azaanTimesToday                = self._prayerTimesOBJ.get_times(date(_yearToday,_monthToday,_dayToday), (self._latitude, self._longitude), self._gmt)
            self._azaanTimesTomorrow             = self._prayerTimesOBJ.get_times(date(_yearTomorrow,_monthTomorrow,_dayTomorrow), (self._latitude, self._longitude), self._gmt)
            

            # Calculate jamaat times
            self._azaanTimes                    = self._azaanTimesToday
            self._jamaatTimes                   = self.compute_prayerJamaat_times()
            
            # Move to the next screen
            self.ids.carousel.load_next()

            # Updating the times
            self.ids.fajarAzan_Time.text        = str(self._azaanTimes['fajr'])
            self.ids.zuharAzan_Time.text        = str(self._azaanTimes['dhuhr'])
            self.ids.asrAzan_Time.text          = str(self._azaanTimes['asr'])
            self.ids.maghribAzan_Time.text      = str(self._azaanTimes['maghrib'])
            self.ids.eshaaAzan_Time.text        = str(self._azaanTimes['isha'])

            self.ids.fajarJamaat_Time.text        = str(self._jamaatTimes['fajr'])
            self.ids.zuharJamaat_Time.text        = str(self._jamaatTimes['dhuhr'])
            self.ids.asrJamaat_Time.text          = str(self._jamaatTimes['asr'])
            self.ids.maghribJamaat_Time.text      = str(self._jamaatTimes['maghrib'])
            self.ids.eshaaJamaat_Time.text        = str(self._jamaatTimes['isha'])

            if self._isSummer:
                self.ids.jummaJamaat_Time1.text          = self._jummaSummerTime1
                self.ids.jummaJamaat_Time2.text          = self._jummaSummerTime2
            else:
                
                self.ids.jummaJamaat_Time1.text          = self._jummaWinterTime1
                self.ids.jummaJamaat_Time2.text          = self._jummaWinterTime2

    '''
     Compute the jamaat (Iqama) times of all the 5 prayers based on the jamaat times after the azaan

     If jamaat time of today's prayer has passed then update the time to tomorrow's time
    '''
    def compute_prayerJamaat_times(self):
        ## FAJR    
        fajrAzan        = re.split(':', self._azaanTimesToday['fajr'])    
        fajrTime        = time(int(fajrAzan[0]),int(fajrAzan[1]))
        fajrJamaat      = ((datetime.combine(date.today(),fajrTime)))
        fajrRounded     = self.roundTime(fajrJamaat, self._fajarJamaat, self._roundOffMinutes)
        
        if datetime.now() > fajrRounded:
            fajrAzan        = re.split(':', self._azaanTimesTomorrow['fajr'])
            fajrTime        = time(int(fajrAzan[0]),int(fajrAzan[1]))
            fajrJamaat      = ((datetime.combine(date.today(),fajrTime)))
            fajrRounded     = self.roundTime(fajrJamaat, self._fajarJamaat, self._roundOffMinutes)
            fajr            = fajrRounded.strftime('%H:%M')

            self._azaanTimes['fajr']    =  self._azaanTimesTomorrow['fajr']
        else:
            fajr = fajrRounded.strftime('%H:%M')

        ## DHUHR
        dhuhrAzan       = re.split(':', self._azaanTimesToday['dhuhr'])
        dhuhrTime       = time(int(dhuhrAzan[0]),int(dhuhrAzan[1]))
        dhuhrJamaat     = ((datetime.combine(date.today(),dhuhrTime)))
        dhuhrRounded    = self.roundTime(dhuhrJamaat, self._delayJamaatMinutes_10, self._roundOffMinutes)

        if datetime.now() > dhuhrRounded:
            dhuhrAzan       = re.split(':', self._azaanTimesTomorrow['dhuhr'])
            dhuhrTime       = time(int(dhuhrAzan[0]),int(dhuhrAzan[1]))
            dhuhrJamaat     = ((datetime.combine(date.today(),dhuhrTime)))
            dhuhrRounded    = self.roundTime(dhuhrJamaat, self._delayJamaatMinutes_10, self._roundOffMinutes)
            dhuhr           = dhuhrRounded.strftime('%H:%M')

            self._azaanTimes['dhuhr']    =  self._azaanTimesTomorrow['dhuhr']
        else:
            dhuhr = dhuhrRounded.strftime('%H:%M')

        ## ASR
        asrAzan         = re.split(':', self._azaanTimesToday['asr'])
        asrTime         = time(int(asrAzan[0]),int(asrAzan[1]))
        asrJamaat       = ((datetime.combine(date.today(),asrTime)))
        asrRounded      = self.roundTime(asrJamaat, self._delayJamaatMinutes_10, self._roundOffMinutes)

        if datetime.now() > asrRounded:
            asrAzan         = re.split(':', self._azaanTimesTomorrow['asr'])
            asrTime         = time(int(asrAzan[0]),int(asrAzan[1]))
            asrJamaat       = ((datetime.combine(date.today(),asrTime)))
            asrRounded      = self.roundTime(asrJamaat, self._delayJamaatMinutes_10, self._roundOffMinutes)
            asr           = asrRounded.strftime('%H:%M')

            self._azaanTimes['asr']    =  self._azaanTimesTomorrow['asr']
        else:
            asr           = asrRounded.strftime('%H:%M')

        ## MAGHRIB
        maghribAzan     = re.split(':', self._azaanTimesToday['maghrib'])
        maghribTime     = time(int(maghribAzan[0]),int(maghribAzan[1]))
        maghribJamaat   = ((datetime.combine(date.today(),maghribTime)))
        maghribRounded  = self.roundTime(maghribJamaat, self._delayJamaatMinutes_5, self._roundOffMinutesMaghrib)

        if datetime.now() > maghribRounded:
            maghribAzan     = re.split(':', self._azaanTimesTomorrow['maghrib'])
            maghribTime     = time(int(maghribAzan[0]),int(maghribAzan[1]))
            maghribJamaat   = ((datetime.combine(date.today(),maghribTime)))
            maghribRounded  = self.roundTime(maghribJamaat, self._delayJamaatMinutes_5, self._roundOffMinutesMaghrib)
            maghrib         = maghribRounded.strftime('%H:%M')

            self._azaanTimes['maghrib']    =  self._azaanTimesTomorrow['maghrib']
        else:
            maghrib         = maghribRounded.strftime('%H:%M')

        ## ISHA
        ishaAzan        = re.split(':', self._azaanTimesToday['isha'])
        ishaTime        = time(int(ishaAzan[0]),int(ishaAzan[1]))
        ishaJamaat      = ((datetime.combine(date.today(),ishaTime)))
        ishaRounded     = self.roundTime(ishaJamaat, self._delayJamaatMinutes_10, self._roundOffMinutes)

        if datetime.now() > ishaRounded:
            ishaAzan        = re.split(':', self._azaanTimesTomorrow['isha'])
            ishaTime        = time(int(ishaAzan[0]),int(ishaAzan[1]))
            ishaJamaat      = ((datetime.combine(date.today(),ishaTime)))
            ishaRounded     = self.roundTime(ishaJamaat, self._delayJamaatMinutes_10, self._roundOffMinutes)
            isha            = ishaRounded.strftime('%H:%M')

            self._azaanTimes['isha']    =  self._azaanTimesTomorrow['isha']
        else:
            isha            = ishaRounded.strftime('%H:%M')

        return {
            'fajr': fajr, 'dhuhr': dhuhr, 'asr': asr, 'maghrib': maghrib, 'isha': isha
        }
        

# round off the jamaat time to the nearest self._roundOffMinutes
    def roundTime(self, dt, delayJamaat, roundOf):

        approx = math.ceil((dt.minute + delayJamaat)/roundOf)*roundOf
        dt = dt.replace(minute=0)
        dt += timedelta(seconds=(approx)*60)

        roundedTime = dt

        return roundedTime

# Reseting the GUI
    def resetGUI(self, *args):
        pass

# Configuration of settings of the prayer times
    def configurePrayerTimes(self, *args):

        self._prayerTimesOBJ                 = pT.PrayTimes('Makkah')
        self._prayerTimesOBJ.time_format     = '24h'

        self._prayerTimesOBJ.adjust({'asr': 'Hanafi'})

        calculationMethod       = str('Calculation: Umm Al-Qura University Makkah')
        asrMethod               = str('Asr: Hanafi')

        self.ids.methodAzan_Label.text          = calculationMethod
        self.ids.asrMethodAzan_Label.text       = asrMethod
        
     

# Main App class
# Starting the mainscreen update as App loads
# Simple Smart Solutions (SSS) SMARTApp
class NAMAZTIMESApp(App):
    def build(self):
        #global _updateGUI_ClockEvent
        
        NAMAZTIMESW = NAMAZTIMESWidget()
        
        # Start the mainscreen as the Display is turned ON
        self._updateGUI_ClockEvent = Clock.schedule_once(NAMAZTIMESW.showMainscreen)

        return NAMAZTIMESW
       

if __name__ == "__main__":
    NAMAZTIMESApp().run()
