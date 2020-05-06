import time
import json
import growattServer
import requests
import serial
import os.path

# Enable logging
DEBUG = 0

# PVOutput.org details
PVO_API='XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX'  # Your PVOutput.org API key
PVO_SYSID='XXXXXXX'                                   # Testing ID
# --------------------

# server.growatt details
GROWATT_USERNAME="XXXXXXX"  # Your server.growatt username
GROWATT_PASSWORD="XXXXXXX"  # Your server.growatt password
# --------------------

# Open Weather Map details
units       = 'metric'
latitude    = 'XXXXXXX'
longitude   = 'XXXXXXX'
app_id      = 'XXXXXXXXXXXXXXXXXXXXXXXXXXXX'
# --------------------

def logging (logdata):
    Date = time.strftime('%Y_%m_%d')
    Time = time.strftime('%R')
    logfile_name = "/home/jory/logfiles/" + str(Date) + "_logfile.txt"
    f = open(logfile_name, 'a')
    f.write("%s %s %s\r\n" % (Date,Time,logdata))
    f.close
    return

#-------------------get_temperature-------------------#
def get_temperature():
  url = 'https://api.openweathermap.org/data/2.5/weather?units=%s&lat=%s&lon=%s&appid=%s' % (units,latitude,longitude,app_id)
  
  # Get the data from open weather map.
  response = requests.get(url)

  if (response.status_code == 200):
    json_res = response.json()
    Temperature = float(json_res["main"]["temp"])

    #print the received json object
    #print(json.dumps(json_res,indent=4))

    #Round temperature to nearest 0.5 otherwise PVOutput graph is very shaky
    Temperature= round(Temperature * 2) / 2

  return (Temperature)
#-----------------------------------------------------#


#------------------post_add_status--------------------#
def post_add_status(): # may raise exceptions
    
    Date = time.strftime('%Y%m%d')
    Time = time.strftime('%R')
    Temperature = get_temperature()

    print ("d:", Date)
    print ("t:", Time)
    print ("v1:", EnergyGeneration,"Watt Hours")
    print ("v2:",PowerGeneration,"Watts")
    print ("v3:",EnergyConsumptionToday,"Watt Hours") 
    print ("v4:", PowerConsumption,"Watts")
    print ("v5:", Temperature,"Celcius")
    print ("v6:", VoltageString1,"Volts")

    TempLog = "EnergyGeneration: " + str(EnergyGeneration) +  " WH"
    logging(TempLog)
    TempLog = "PowerGeneration: " + str(PowerGeneration) +  " Watts"
    logging(TempLog)
    TempLog = "EnergyConsumptionToday: " + str(EnergyConsumptionToday) +  " WH"
    logging(TempLog)
    TempLog = "PowerConsumption: " + str(PowerConsumption) +  " Watts"
    logging(TempLog)
    TempLog = "Temperature: " + str(Temperature) +  " Temp"
    logging(TempLog)
    TempLog = "VoltageString1: " + str(VoltageString1) +  " Voltage"
    logging(TempLog)

    url = 'https://pvoutput.org/service/r2/addstatus.jsp'
    headers = {
        'X-Pvoutput-SystemId': str(PVO_SYSID),
        'X-Pvoutput-Apikey': str(PVO_API)
    }
    params = {
        'd': Date,
        't': Time,
        'v1': EnergyGeneration,
        'v2': PowerGeneration,
        'v3': EnergyConsumptionToday,
        'v4': PowerConsumption,
        'v5': Temperature,
        'v6': VoltageString1
    }
    logging("Posting data to PV Output")
    #resp = requests.post(url, headers=headers, data=params, timeout=10)
    
    TempLog = "ResponceCode of PV Output: " + str(resp.status_code)
    logging(TempLog)
    
    
    return
#-----------------------------------------------------#


#-----------------read_p1_meter_data------------------#
def read_p1_meter_data():
    #print ("Read DSMR P1")
    #print ("Control-C to stop")

    #Set COM port config
    ser = serial.Serial()
    ser.baudrate = 9600
    ser.bytesize=serial.SEVENBITS
    ser.parity=serial.PARITY_EVEN
    ser.stopbits=serial.STOPBITS_ONE
    ser.xonxoff=0
    ser.rtscts=0
    ser.timeout=20
    ser.port="/dev/ttyUSB0"

    #Open COM port
    try:
        ser.open()
    except:
        sys.exit ("Error by opening %s. Program stopped."  % ser.name)      

    # Initialize
    # stack is the array where the p1 data is stored
    p1_counter=0
    stack=[]
    
    p1_meter_name = '/ISk5\\2ME382-1004' #add here your own name to filer out the wrong data

    while p1_counter < 20:
        p1_line=''
        #Read 1 line
        try:
            p1_raw = ser.readline()
        except:
            sys.exit ("Serial port %s can not be read. Program stopped." % ser.name )      
        #p1_str=str(p1_raw)             #for python 2
        p1_str=str(p1_raw, "utf-8")     #for python 3

        p1_line=p1_str.strip()

        stack.append(p1_line)
        # uncomment the next line to see the data in the console
        #print (p1_line)

        p1_counter = p1_counter +1
        if (stack[0][0:18] != p1_meter_name):
            p1_counter = 0
            stack.clear()

    #Initialize
    # stack_counter is mijn tellertje voor de 20 weer door te lopen. Waarschijnlijk mag ik die p1_counter ook gebruiken
    stack_counter=0
    global EnergyConsumption 
    global PowerConsumption

    while stack_counter < 20:
        # Off Peak rate, used Current 1-0:1.8.1
        if stack[stack_counter][0:9] == "1-0:1.8.1":
            if (DEBUG):
                print ("Used Current in Off-Peak     ", int(float(stack[stack_counter][10:19])*1000),"Watt Hour")
            EnergyConsumption = int(float(stack[stack_counter][10:19])*1000)
        # Peak rate, used Current 1-0:1.8.2
        elif stack[stack_counter][0:9] == "1-0:1.8.2":
            if (DEBUG):
                print ("Used Current in Peak     ", int(float(stack[stack_counter][10:19])*1000),"Watt Hour")
            EnergyConsumption = EnergyConsumption + int(float(stack[stack_counter][10:19])*1000)
        # Off peak rate, Returned Power 1-0:2.8.1
        elif stack[stack_counter][0:9] == "1-0:2.8.1":
            if (DEBUG):
                print ("Returned Power in Off-Peak   ", int(float(stack[stack_counter][10:19])*1000),"  Watt Hour")
            ReturnedPower = int(float(stack[stack_counter][10:19])*1000)
        # Peak rate, Returned Power 1-0:2.8.2
        elif stack[stack_counter][0:9] == "1-0:2.8.2":
            if (DEBUG):
                print ("Returned Power in Peak ", int(float(stack[stack_counter][10:19])*1000),"Watt Hour")
            ReturnedPower = ReturnedPower + int(float(stack[stack_counter][10:19])*1000)
        # Current power draw: 1-0:1.7.0
        elif stack[stack_counter][0:9] == "1-0:1.7.0":
            if (DEBUG):
                print ("Current power draw    ", int(float(stack[stack_counter][10:17])*1000), " W")
            PowerConsumption = int(float(stack[stack_counter][10:17])*1000)
        # Current power returned: 1-0:1.7.0
        elif stack[stack_counter][0:9] == "1-0:2.7.0":
            if (DEBUG):
                print ("Current power returned  ", int(float(stack[stack_counter][10:17])*1000), " W")
        # Gasmeter: 0-1:24.3.0
        elif stack[stack_counter][0:10] == "0-1:24.3.0":
            if (DEBUG):
                print ("Gas                     ", int(float(stack[stack_counter+1][1:10])*1000), " dm3")
        else:
            pass
        stack_counter = stack_counter +1

    if (DEBUG):
        print ("Returned Power: ",ReturnedPower, "Watt Hour") 
    if (DEBUG):
        print ("PowerConsumption: ",PowerConsumption, "Watts")

    #Close port and show status
    try:
        ser.close()
    except:
        sys.exit ("Oops %s. Program stopped." % ser.name )     
    return 

#-------------read_daily_stored_data----------------#
def read_daily_stored_data():

    global EnergyConsumptionToday
    Today = int(time.strftime("%-d", time.localtime()))
    if os.path.isfile('/home/jory/settings/daily_energy.json'):
        print ("File exist")
    else:
        print ("File not exist create file with json object")
        with open('/home/jory/settings/daily_energy.json', 'w') as json_new_file:
            my_details = {
                "day": Today,
                "energy": EnergyConsumption
            }
            json.dump(my_details, json_new_file)
    with open('/home/jory/settings/daily_energy.json', 'r+') as json_file:
        DailyEnergy = json.load(json_file)
        # uncomment to print the readed json dump
        # print (json.dumps(DailyEnergy, indent=4))
        ReadStoredDay    = int(DailyEnergy["day"])
        ReadStoredEnergy = int(DailyEnergy["energy"])
        #print(ReadStoredDay , ReadStoredEnergy)
        if (ReadStoredDay != Today):
            open("daily_energy.json", "w").close()
            EnergyConsumptionToday = EnergyConsumption - ReadStoredEnergy 
            json_file.seek(0)
            my_details = {
                "day": Today,
                "energy": EnergyConsumption
            }
            json.dump(my_details, json_file)
            json_file.truncate()
        else:
            EnergyConsumptionToday = EnergyConsumption - ReadStoredEnergy 
        
        #print("read_stored_data:",EnergyConsumptionToday)

    return

#---------------read_growatt_data------------------#
def read_growatt_data():
    api = growattServer.GrowattApi()

    LoginResponse  = api.login(GROWATT_USERNAME, GROWATT_PASSWORD)
    PlantInfo = api.plant_list(LoginResponse['userId'])
    PlantId = PlantInfo["data"][0]["plantId"]

    PlantDeviceList = api.device_list(PlantId)
    PlantDetails = api.inverter_detail("QJB2823328")

    global VoltageString1 
    VoltageString1 = int(PlantDetails["data"]["vpv1"])
    global CurrentString1
    CurrentString1 = int(PlantDetails["data"]["ipv1"])
    global PowerString1
    PowerString1 = int(PlantDetails["data"]["ppv1"])

    #print (json.dumps(PlantDetails, indent=4))
    #print (json.dumps(PlantDeviceList, indent=4))
    print (json.dumps(PlantInfo, indent=4))
    todayEnergy = PlantInfo['data'][0]['todayEnergy'] #get today energy
    # How to use find()
    if  (todayEnergy.find(' kWh') != -1):
        #print("Contains substring ' kWh'")
        todayEnergy = todayEnergy.replace(" kWh","") 
        todayEnergy = float(todayEnergy)*1000
    elif (todayEnergy.find(' Wh') != -1):
        #print("Contains substring ' Wh'")
        todayEnergy = todayEnergy.replace(" Wh","") 
        todayEnergy = float(todayEnergy)
    global EnergyGeneration
    EnergyGeneration = todayEnergy

    currentPower = PlantInfo['data'][0]['currentPower'] #get today energy
    # How to use find()
    if  (currentPower.find(' kW') != -1):
        #print("Contains substring ' kW'")
        currentPower = currentPower.replace(" kW","") 
        currentPower = float(currentPower)*1000
    elif (currentPower.find(' W') != -1):
        #print("Contains substring ' W'")
        currentPower = currentPower.replace(" W","") 
        currentPower = float(currentPower)
    global PowerGeneration
    PowerGeneration = currentPower
    return

read_growatt_data();
read_p1_meter_data();
read_daily_stored_data();

post_add_status();


#Parameter	Field	            Required	Format	    Unit	    Example     Since	
#d	        Date	            Yes     	yyyymmdd	date	    20100830	r1	
#t	        Time	            Yes	        hh:mm	    time	    14:12	    r1	
#v1	        Energy Generation	No          number	    watt hours	10000	    r1	
#v2	        Power Generation	No	        number	    watts	    2000	    r1	
#v3	        Energy Consumption	No	        number	    watt hours	10000	    r1	
#v4	        Power Consumption	No	        number	    watts	    2000	    r1	
#v5	        Temperature	        No	        decimal	    celsius	    23.4	    r2	
#v6	        Voltage	            No	        decimal	    volts	    210.7	    r2
#v7         donation options

#user_info = api.get_user_center_energy_data()
#print (json.dumps(user_info, indent=4))
#plant_id = plant_info["data"][0]["plantId"]
#print (json.dumps(plant_id, indent=4))
#plant_detail = api.plant_detail(plant_id, growattServer.Timespan.day, datetime.date.today())
#print (json.dumps(plant_detail, indent=4))
#new_plant_detail = api.new_plant_detail(plant_id, Timespan.day, datetime.date.today())
#print (json.dumps(new_plant_detail, indent=4))
# print(plant_detail)



#curl -d "d=20111201" -d "t=10:00" -d "v1=1000" -d "v2=150" -H "X-Pvoutput-Apikey: Your-API-Key" -H "X-Pvoutput-SystemId: Your-System-Id" https://pvoutput.org/service/r2/addstatus.jsp


