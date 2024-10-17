import serial
import time
import serial.tools.list_ports

ports = serial.tools.list_ports.comports()
available_ports = []
print('start')
for p in ports:
    available_ports.append(p.device)
    print(available_ports)
print('port qty',len(ports))