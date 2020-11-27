import serial
import httplib
import time
import RPi.GPIO as GPIO
import requests
import urllib
import os


DEBUG_MODE = 1

#GPIO SETUP
loopDetector = 11
BUZZERpin = 40
GPIO.setmode(GPIO.BOARD)
GPIO.setup(BUZZERpin, GPIO.OUT)
GPIO.setup(loopDetector, GPIO.IN, pull_up_down = GPIO.PUD_DOWN)

#BOOLEAN
boolNewRFID = False
boolSameData = False
boolOnlineMode = True
boolServerDown = False

#HTTP SERVER
IPAddress = '192.168.0.251'
conn = httplib.HTTPConnection(IPAddress, timeout=5)
HTTPURL = 'http://'+ IPAddress + '/RfidScanned/RfidScanned.php/?'

DeviceMACAddress = open('/sys/class/net/%s/address' %'eth0').read().replace('\n','')

if DEBUG_MODE:
    print 'MAC Address (eth0) : ' + DeviceMACAddress

DeviceIPAddress = ''

try:
    
    DeviceIPAddress = os.popen('ip addr show eth0').read().split('inet ')[1].split('/')[0]
    if not DEBUG_MODE:
        print 'Device IP Address (eth0) : ' + DeviceIPAddress
    EventLog = 'message : Ethernet Connection Detected = Online mode | Device MAC Address : ' + DeviceMACAddress + ' | Device IP Address : ' + DeviceIPAddress + ' | time : ' + str(time.ctime()) + '\n'
    try:
        with open('debug.dat','a+') as EventLogFile:
            EventLogFile.write(EventLog)
    except:
        if DEBUG_MODE:
            print 'File Not Found...'
    boolOnlineMode = True
    boolServerDown = False
    
except:
    
    DeviceIPAddress = os.popen('ip addr show lo').read().split('inet ')[1].split('/')[0]
    if DEBUG_MODE:
        print 'Ethernet Connection Not Detected! Switching to Offline mode...'
        print 'Device IP Address (lo) : ' + DeviceIPAddress #str(os.popen('ip addr show lo').read().split('inet ')[1].split('/')[0])
    EventLog = 'message : Ethernet Connection Not Detected = Offline mode | Device MAC Address : ' + DeviceMACAddress + ' | Device IP Address : ' + DeviceIPAddress + ' | time : ' + str(time.ctime()) + '\n'
    try:
        with open('debug.dat','a+') as requestErrorLogfile:
            requestErrorLogfile.write(EventLog)
    except:
        if DEBUG_MODE:
            print 'File Not Found...'
    boolOnlineMode = False
    boolServerDown = True

try:
    serialRFID = serial.Serial('/dev/myUSB',9600)
    print'UHF RFID Detected.'
except (serial.serialutil.SerialException,IOError):
    print'UHF RFID Not Detected.'
    
def BuzzerFunc(BuzzType):
    
    global BUZZERpin
    
    if (BuzzType == 1): #device boot up notification / validation success (UHF RFID, Short-Range RFID/QR Code)
        GPIO.output(BUZZERpin,1)
        time.sleep(0.3)
        GPIO.output(BUZZERpin,0)
        time.sleep(0.05)
        GPIO.output(BUZZERpin,1)
        time.sleep(0.3)
        GPIO.output(BUZZERpin,0)
    elif (BuzzType == 0):   #validation failed (UHF RFID, Short-Range RFID/QR Code)
        GPIO.output(BUZZERpin,1)
        time.sleep(0.15)
        GPIO.output(BUZZERpin,0)
        time.sleep(0.05)
        GPIO.output(BUZZERpin,1)
        time.sleep(0.15)
        GPIO.output(BUZZERpin,0)
        time.sleep(0.05)
        GPIO.output(BUZZERpin,1)
        time.sleep(0.15)
        GPIO.output(BUZZERpin,0)
    else:   #disconnected to server / reply from server not recognized
        GPIO.output(BUZZERpin,1)
        time.sleep(2)
        GPIO.output(BUZZERpin,0)
        
BuzzerFunc(1)
#BuzzerFunc(2)
    
    
def funcServerChecking(self):
    
    global boolOnlineMode, boolServerDown
    
    try:
        DeviceIPAddress = os.popen("ip addr show eth0").read().split("inet ")[1].split('/')[0]
        if not DEBUG_MODE:
            print "Device IP Address : " + DeviceIPAddress
        boolOnlineMode = True
        boolServerDown = False
        print "Online Mode" + "\n" + "Server Ready"
    except:
        DeviceIPAddress = os.popen("ip addr show lo").read().split("inet ")[1].split('/')[0]
        if DEBUG_MODE:
            print "Ethernet Not Connected! Switching to Offline Mode."
        boolOnlineMode = True
        boolServerDown = False
       # BuzzerFunc(0)
        print "Offline Mode" 
   # time.sleep(2)
    
    return


def funcUHF():
    
    global RFIDDecimal
    
    if serialRFID.inWaiting() :
        RFIDValue = serialRFID.read(18).encode('hex')
        RFIDDecimal = str(int(RFIDValue[26:28],16)).zfill(3) + str(int(RFIDValue[28:32],16)).zfill(5)
        serialRFID.flushInput()
        return RFIDDecimal
    else : 
        return 0
       
       
data = []
lane_name = "PortalN01"
device_name = "NTEK001"
lane_count = 0
    
try:
      
    while True:      
        
        if funcUHF() and GPIO.input(loopDetector) == GPIO.HIGH:
            
            print 'UHF RFID:' + RFIDDecimal
            #print DeviceIPAddress
            #print"Ready to read"
            try :
                #FILTERING MULTI RFID
                if data.count(RFIDDecimal) == 1:
                    print'Frequent Data.'
                    boolSameData = True
                    if len(data) > 5: #NUMBER OF DATA TO HOLD AND FILTER
                        data = [RFIDDecimal]
                        #pass
                else:
                    data.append(str(RFIDDecimal))
                    print'New Data:' + str(time.ctime())
                    boolSameData = False
                    lane_count = lane_count + 1
                print data
                
                ########---------PARAMETERS FOR HTTP POST METHOD----------#########
                
                message_id = str(lane_name) + "-" + "xxxx" + "-" + str(lane_count).zfill(7)
                params = {"LaneName" : str(device_name) , "DeviceName" : str(lane_name), "TagID" : str(RFIDDecimal), "EventTime" : str(time.ctime()), "MessageID" : str(message_id)}
                requestParams = urllib.urlencode(params)
                headers = {"Content-type": "application/x-www-form-urlencoded","Accept": "text/plain"}
                #requestParams = {'rfid' : RFIDDecimal, 'time_arrival' : str(currTime), 'lane_name' : lane_name, 'device_name' : device_name} #where {key : value}
                #print str(urllib.urlencode(requestParams))
                if boolSameData == False and boolOnlineMode == True and boolServerDown == False:
                    conn.request("POST",HTTPURL,requestParams,headers)
                    r1 = conn.getresponse()
                    data1 = r1.read()
                    #print r1.status
                    #print r1.reason
                    print 'Server Response:' + data1
                    if data1[:9].strip() == 'Verified':
                        BuzzerFunc(1)
                        print 'UHF RFID:' + RFIDDecimal + ' with' + ' Plate Number:' + data1[9:] + '\n' +' *Verified from the server.*'
                    else:
                        print 'Invalid RFID.'
                #CAN DO "elif" sequence here for local server if disconnected
                #time.sleep(0.1)
                RFIDValue = ''
                conn.close()
                
            except:
                conn.close()
                print 'Error:Request Failed!'
               # NoConn =  'No Connection at'+ '\n' + str(time.ctime()) + '\n'
                    #LOG DATA WHEN NO CONNECTION/OFFLINE
                try:
                    NoConnLog = open('NoConnectionLog.json','a+')
                    NoConnLog.write(str(params) + '\n')
                    NoConnLog.close()
                    print"Data Saved Offline" + "\n"
                except:
                    print 'No File Found : NoConnectionLog.json'
        funcServerChecking(1,)
        #time.sleep(1)
except KeyboardInterrupt:
    print "Closing System"
    #quit()
    
except Exception:
    print"System Error!" + "\n" + "Program Shutting Down!"
    
time.sleep(0.1)
conn.close()
GPIO.cleanup()
