import os, sys, re, csv, netmiko, time, signal
from getpass import getpass
from tqdm import tqdm
from colorama import Fore, Back, init, deinit

# Initiating COLORAMA
init()

# Creating variable for netmiko exception
netmiko_exceptions = (OSError, netmiko.ssh_exception.NetmikoTimeoutException, netmiko.ssh_exception.NetmikoAuthenticationException)

# CTRL+C Keyboard Interrupt
signal.signal(signal.SIGINT, signal.SIG_DFL)

# Checking bulkstatsschema.csv
def bulkstatsschema_csv():
  while True:
    try:
      check_filename = re.compile(r"^[cC]:.+\.csv$")
      dir = os.getcwd()
      filebulk = "bulkstatsschema.csv"
      filename = input(f"\nPlease type the name or complete path of the file? [bulkstatsschema.csv] ")
      if filename == "" or filename == filebulk:
        filepath = f"{dir}\\{filebulk}"
      elif check_filename.match(filename):
        filepath = f"{filename}"
      else:
        filepath = f"{dir}\\{filename}"
      csvfile = open(f"{filepath}")
      break
    except (OSError, FileNotFoundError):
      print()
      print(f"File does not exist in the folder below. Please type the complete path.\n")
      print(f"{filepath}")
      print()
      continue
  return csvfile



# Creating the device dictionary
def device_dictionary():
  print("\n==================================== Enter the device credentials below:")
  time.sleep(1)
  device_list = []
  device_dict = {}
  validate_ip = re.compile(r"((([0-9]|[1-9][0-9]|1[0-9][0-9]|2[0-4][0-9]|25[0-5])\.){3}([1-2]?[0-9][0-9]),?){1,}")
  while True:
    ip_address = input("Enter the ip address of the device: ")
    if not validate_ip.match(ip_address):
      print("Wrong ip address. Please type again.")
      continue
    else:
      username = input("Enter the username of the device: ")
      password = getpass()
      password_retype = getpass("Retype your password: ")
      print()
      if username == "" or password == "":
        print("One of the values are empty. Please, enter a username and password.\n")
        continue
      elif password != password_retype:
        print("Passwords didn't match. Try again.\n")
        continue
      else:
        break
  ip_address = ip_address.split(",")
  for ip in ip_address:
    device_dict["ip"] = ip
    device_dict["username"] = username
    device_dict["password"] = password
    device_dict["device_type"] = "cisco_xe"
    device_list.append(device_dict)

  return device_list

# Declaring variables
bulkstat_file_read = bulkstatsschema_csv()
bulkstat_file = list(csv.reader(bulkstat_file_read))
devices = device_dictionary()

# Get bulkstatsschema file version
accum = 0
for line in bulkstat_file:
  if accum == 0:
    bulkstatfile_version = line[0][7:]
    break

# Connecting to device.
try:
  connection = netmiko.ConnectHandler(**devices[0], global_delay_factor=2.0)
  cmd = connection.send_command("show bulkstats schema", delay_factor=2.0)
  cmd = cmd.split("\n")
except netmiko_exceptions:
  print("Authentication failed. Check username and password and try again.\n")
  exit()

# Pick the file format
which_file = r"Schemas for"
list_of_ip_in_file = []
list_of_file = []
list_of_server =[]
for line in cmd:
  if "Primary" in line:
    list_of_ip_in_file.append(line[17:-33])
  if which_file in line:
    list_of_file.append(line[32:-40])
  if "matrix" in line:
    list_of_server.append(line[72:-44])

while True:
  print(f"""
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
Options Available:
{list_of_file[0]} -> {list_of_ip_in_file[0]}
{list_of_file[1]} -> {list_of_ip_in_file[1]}
{list_of_file[2]} -> {list_of_ip_in_file[2]}
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

Which file you desire? Choose one of the above: [File1, File 1...] """, end ="")
  file_schema = input()
  if (file_schema == "") or not (re.compile(f"^(\w+)?\s?([1-{len(list_of_file)}])$").match(file_schema)):
    print(f"\nThe file you entered does not exist or cannot be empty. Please type again.")
    time.sleep(2)
    continue
  else:
    re_file_schema = re.compile("^(\w+)?\s?(\d)$")
    file_schema = f"------------------- Schemas for File {re_file_schema.match(file_schema).groups()[1]}----------------------------------------"

file_header = "File Header:"
file_version = r"Version-"

# Get device file version
for position in cmd:
  if file_schema == position:
    pos_index_file = cmd.index(file_schema)
  elif file_version in position:
    version = position[35:48]

# Splitting the numbers for versions variable
re_version = re.compile(r"^(\w+)-(\d+\.\d+)")
device_version_group = re_version.match(version).groups()[1]
bulkstatfile_version_group = re_version.match(bulkstatfile_version).groups()[1]
print(f"\n- The version configured on device is: {device_version_group} \n- The bulkstatschema file version is: {bulkstatfile_version_group}\n")

# Creating a csv file from command "show bulkstats schema"
filename = devices[0]["ip"]+"_bulkstat.csv"
print("Gathering compliance schemas information...\n")
with open(filename, "w") as file:
  for line in cmd[pos_index_file+3:]:
    if "---" not in line:
      file.writelines(",".join(line[50:].split(",")).strip() + "\n")
    else:
      break

# Validating the schemas and counter from bulkstatsschema's file and device
init_bulkstat = 0
count_schema = 0
device_file = open(filename)
device_file = csv.reader(device_file)
with open(f"{devices[0]['ip']}-compliance.txt", "w") as file:
  for line_device_file in device_file:
    try:
      for line_bulkstat_file in bulkstat_file:
        if init_bulkstat >= 3:
          try:
            if line_device_file[2] == line_bulkstat_file[2]:
              count_schema = 0
              for i in range(len(line_bulkstat_file)-1):
                if (line_bulkstat_file[2:][i] == line_device_file[2:][i]):
                  pass
                else:
                  if (count_schema == 0):
                    file.write(f"""Schema is: {line_bulkstat_file[2]}""")
                    file.write(f"""
                    =======================================================
                    Counters in this schema didn't match
                    Bulkstat counter is: {line_bulkstat_file[2:][i]}
                    Device Counter is: {line_device_file[2:][i]}
                    =======================================================\n""")
                    count_schema += 1
                  else:
                    file.write(f"""
                    =======================================================
                    Counters in this schema didn't match
                    Bulkstat counter is: {line_bulkstat_file[2:][i]}
                    Device Counter is: {line_device_file[2:][i]}
                    =======================================================\n""")  
          except IndexError:
            pass
        else:
          init_bulkstat += 1
    except IndexError:
      continue
    init_bulkstat = 0

print(f"The file has been saved as {devices[0]['ip']}-compliance.txt in the same directory.\n")