# -*- coding: utf-8 -*-
"""
Created on Tue May 19 10:50:13 2020

@author: ngmai1
"""

# from re import X
from PyQt5.QtWidgets import (QWidget, QMainWindow, QTextEdit, QAction, QFileDialog, QApplication, QMessageBox)
from PyQt5.QtPrintSupport import (QPrinter,QPrintDialog)

# QTextEdit, QAction, QFileDialog, QApplication, QMessageBox)
from PyQt5.QtCore import *
from PyQt5.QtCore import QThread, pyqtSignal, QTimer, QPoint, QDateTime, QRect#, pyqtRemoveInputHook, pyqtRestoreInputHook
from PyQt5.QtGui import QImage, QPixmap, QPainter, QRegion, QFont, QColor, QPen
from PyQt5 import (QtWidgets, QtGui, QtCore) #uic
from  matplotlib.backends.backend_qt5agg  import  ( NavigationToolbar2QT  as  NavigationToolbar )
from PIL import Image
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import math
import sys
import os
import time
import pandas as pd
import string
# import getpass
import mysql.connector
from datetime import datetime
# from pandas.io import sql
from sqlalchemy import create_engine
#import random
import datetime
import numpy as np
import shutil
# from ui_dept import Ui_MainWindow
from ui_dept2 import Ui_MainWindow
# from ui_gps import Ui_GPSWindow
from ui_gps2 import Ui_GPSWindow
import serial
import time
import serial.tools.list_ports
import io
import  random
# from pyproj import Proj
import math
# p = Proj(proj='utm',zone=48,ellps='WGS84', preserve_units=False)

cwd = os.getcwd()
preset=pd.read_excel('pre_setting.xlsx')
print(preset)
kn_plc=1 #cần kết nối đến PLC
kn_gps=1 # cần kết nối đến gps
kn_len=1 # can ket noi den len
ser=serial.Serial()
ser_gps=serial.Serial()
ser_len=serial.Serial()
setting=1
set_gps=1
set_len=1
dept="0"
gps_longitude=''
gps_latitude=''
thread_plc=0
thread_gps_n=0
projectname=preset.iloc[0,2]
vesselname=preset.iloc[0,3]
fromtubin=preset.iloc[0,0]
totubin=preset.iloc[0,1]
ttcable='...'
crcable='...'
gposition=str(preset.iloc[0,0])+'-'
cgps=0
x=0
y=0
list_com=[]
engine_ttp = create_engine('mysql+mysqlconnector://ttpdept:plcgpsd@localhost:3308/ttp', echo=False)
mydb=mysql.connector.connect(host="localhost",port='3308', user='ttpdept', passwd='plcgpsd', database="ttp")
myCursor=mydb.cursor()
tb_list=pd.read_sql('select * from location_detail where project="TPD2" and tuabin="'+str(fromtubin)+'";',engine_ttp)
x0=0
y0=0
try:
    if len(tb_list)>0:
        x0=float(tb_list.iloc[0,4])
        y0=float(tb_list.iloc[0,3])
except:
    print('wrong coodinate for tuabin')
if fromtubin=="WTG0":
    x0=694058
    y0=1136332
if fromtubin=="WTG00":
    x0=694056
    y0=1136353
tb_list=pd.read_sql('select * from location_detail where project="TPD2" and tuabin="'+str(totubin)+'";',engine_ttp)
x1=0
y1=0
try:
    if len(tb_list)>0:
        x1=float(tb_list.iloc[0,4])
        y1=float(tb_list.iloc[0,3])
except:
    print('wrong coodinate for tuabin')
a=0
b=0
d='0'
if x0>0 and y0>0 and x1>0 and y1>0:
    if x0==x1:
        a=1
        b=0
    elif y0==y1:
        a=0
        b=y0
    else:
        a=(y1-y0)/(x1-x0)
        b=y0-a*x0
    
pulley_para=pd.read_sql('select port from port_setting where device="R_pulley";',engine_ttp)
R_p=float(pulley_para.iloc[0,0])/100
# cwd = os.getcwd()
# solverdir = 'pulp\\solverdir\\cbc\\win\\64\\cbc.exe'  # extracted and renamed CBC solver binary
# solverdir = os.path.join(cwd, solverdir)



class MyWindow(QtWidgets.QMainWindow):
    
    def __init__(self):
        super(MyWindow, self).__init__()
        
        self.setWindowFlags(QtCore.Qt.WindowMinimizeButtonHint|QtCore.Qt.WindowMaximizeButtonHint)
        self.setWindowIcon(QtGui.QIcon('hp.ico'))
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.init_event()
        
    def init_event(self):
        global kn_gps
        global kn_plc
        self.load_form()
        print('event')
        if kn_plc==0:
            print('Alert robot connected')
            self.ui.lbl_d_stt.setText('Connected!')
            # QMessageBox.about(self, 'Thông báo','PLC chưa được kết nối!\nVui lòng kiểm tra lại PLC và kết nối lại')

        if kn_gps==0:
            print('alert GPS not yet connect')
            # QMessageBox.about(self, 'Thông báo','GPS chưa được kết nối!\nVui lòng kiểm tra lại module GPS và kết nối lại')
        self.ui.tabWidget.currentChanged.connect(self.tab_change)
        self.ui.menu_GPS_Window.triggered.connect(self.menu_gps_window)
        self.ui.bt_depth_save.clicked.connect(self.depth_save_setting)
        self.ui.bt_depth_reset.clicked.connect(self.reset_position)
        self.ui.bt_home.clicked.connect(self.active_homepage)
        self.ui.bt_rf_com_plc.clicked.connect(self.refresh_com_port_plc)
        self.ui.bt_reconnect_plc.clicked.connect(self.reconnect_plc)
        self.ui.bt_reconnect_len.clicked.connect(self.reconnect_len)
        self.ui.bt_rf_com_len.clicked.connect(self.rf_com_len)
        self.menu_gps_window()
        self.save_my_sql=sql_save()        
        self.save_my_sql.signal.connect(self.save_mysql_signal)
        self.save_my_sql.start()

    def rf_com_len(self):
        global list_com
        ports = serial.tools.list_ports.comports()
        available_ports = []
        for p in ports:
            available_ports.append(p.device)
        print(available_ports)
        list_com=available_ports
        c=self.ui.cb_len_com.count()
        try:
            while c>=0:
                self.ui.cb_len_com.removeItem(c)
                c=c-1
        except:
            print('refresh combo box')
        for port in available_ports:
            self.ui.cb_len_com.addItem(port)
        print('import port ok')

    def reconnect_len(self):
        global ser_len
        global kn_len
        global set_len
        self.ui.bt_reconnect_len.setEnabled(False)
        com=str(self.ui.cb_len_com.currentText())
        print(com)
        try:
        # if True:
            print('on try')
            ser_r = serial.Serial(
            port=com, # PLC
            baudrate=9600,
            parity=serial.PARITY_EVEN,
            bytesize=serial.SEVENBITS,
            stopbits=serial.STOPBITS_ONE
            )
            if (ser_r.isOpen() == False):
                ser_r.timeout = 10
                ser_r.open()
            # if True:
            print ('The Port is Open ')
                #timeout in seconds

            a=':010310000001FA\r\n'.encode('ascii')
            ser_r.write(a)
            print('write check signal')
            c=0
            buffer=''
            while c<10:
                print(c)
                if ser_r.in_waiting > 0:
                    print('read line')
                    buffer = ser_r.readline()
                    break
                time.sleep(0.01)
                c=c+1
            print(buffer)
            buffer=buffer.decode('utf-8')
            if ':01' in buffer:
                QMessageBox.about(self, 'Alert','lenght measure have been connected!')
                set_len=0
                ser_len=ser_r
                self.ui.bt_reconnect_len.setEnabled(False)
                kn_len=0
                sql_update_len_com='update port_setting set port="'+com+'" where device="MET";'
                mydb=mysql.connector.connect(host='localhost', user='ttpdept', passwd='plcgpsd', database="ttp")
                myCursor=mydb.cursor()
                myCursor.execute(sql_update_len_com)
                mydb.commit()
                myCursor.close()
                mydb.close()
                self.ui.lbl_l_stt.setText('len measeurement connected')
            else:
                QMessageBox.about(self, 'Alert','Wrong COM port')
                set_len=2
                kn_len=1
                self.ui.bt_reconnect_plc.setEnabled(True)
        except:
            QMessageBox.about(self, 'Alert','connection loss!\nPlease check again.')
            set_len=2
            kn_len=1
            self.ui.bt_reconnect_len.setEnabled(True)

    def reconnect_plc(self):
        global ser
        global kn_plc
        global setting
        self.ui.bt_reconnect_plc.setEnabled(False)
        com=str(self.ui.cb_plc_com.currentText())
        print(com)
        try:
        # if True:
            print('on try')
            ser_r = serial.Serial(
            port=com, # PLC
            baudrate=9600,
            parity=serial.PARITY_EVEN,
            bytesize=serial.SEVENBITS,
            stopbits=serial.STOPBITS_ONE
            )
            if (ser_r.isOpen() == False):
                ser_r.timeout = 10
                ser_r.open()
            # if True:
            print ('The Port is Open ')
                #timeout in seconds

            a=':010310000001FA\r\n'.encode('ascii')
            ser_r.write(a)
            print('write check signal')
            c=0
            buffer=''
            while c<10:
                print(c)
                if ser_r.in_waiting > 0:
                    print('read line')
                    buffer = ser_r.readline()
                    break
                time.sleep(0.01)
                c=c+1
            print(buffer)
            buffer=buffer.decode('utf-8')
            if ':01' in buffer:
                QMessageBox.about(self, 'Alert','Robot have been connected!')
                print(buffer)
                print('robot phan hoi chuoi check')
                setting=1
                ser=ser_r
                self.ui.bt_reconnect_plc.setEnabled(False)
                kn_plc=0
                self.load_plc_infor()
                sql_update_plc_com='update port_setting set port="'+com+'" where device="PLC";'
                mydb=mysql.connector.connect(host='localhost', user='ttpdept', passwd='plcgpsd', database="ttp")
                myCursor=mydb.cursor()
                myCursor.execute(sql_update_plc_com)
                mydb.commit()
                myCursor.close()
                mydb.close()
                self.ui.lbl_d_stt.setText('connected')
            else:
                QMessageBox.about(self, 'Alert','Wrong COM port')
                setting=2
                self.ui.bt_reconnect_plc.setEnabled(True)
        except:
            QMessageBox.about(self, 'Alert','connection loss!\nPlease check again.')
            setting=2
            kn_plc=1
            self.ui.bt_reconnect_plc.setEnabled(True)

    def active_homepage(self):
        self.ui.tabWidget.setCurrentIndex(0)
    def refresh_com_port_plc(self):
        global list_com
        ports = serial.tools.list_ports.comports()
        available_ports = []
        for p in ports:
            available_ports.append(p.device)
        print(available_ports)
        list_com=available_ports
        c=self.ui.cb_plc_com.count()
        try:
            while c>=0:
                self.ui.cb_plc_com.removeItem(c)
                c=c-1
        except:
            print('refresh combo box')
        for port in available_ports:
            self.ui.cb_plc_com.addItem(port)
        print('import port ok')

    def tab_change(self):
        global setting
        global kn_plc
        current_index=self.ui.tabWidget.currentIndex()
        if setting!=2:
            if current_index==1:
                setting=1
                time.sleep(0.2)

            if current_index==0:
                setting=0
                time.sleep(0.2)
                # if kn_plc==0:
                #     self.read_plc=read_D(550)        
                #     self.read_plc.signal.connect(self.read_plc_signal)
                #     self.read_plc.start()

    def main_read_D(self,addr):
        hex_a=str(hex(addr))[2:]
        if len(hex_a)==1:
            hex_a='100'+hex_a
        if len(hex_a)==2:
            hex_a='10'+hex_a
        if len(hex_a)==3:
            hex_a='1'+hex_a
        # print(hex_a)
        lc=5+int('0x'+hex_a[:2],0)+int('0x'+hex_a[-2:],0)
        # print(lc)
        crc=lc^0xFFFF
        crc=crc+1
        cmd=(':0103'+hex_a+'0001'+hex(crc)[-2:]).upper()+'\r\n'
        
        print(cmd.encode('ascii'))
        print('finish encode')
        return cmd.encode('ascii')

    def main_write_D(self,addr,value):
        hex_a=str(hex(addr))[2:]
        if len(hex_a)==1:
            hex_a='100'+hex_a
        if len(hex_a)==2:
            hex_a='10'+hex_a
        if len(hex_a)==3:
            hex_a='1'+hex_a
        print(hex_a)
        hex_v=str(hex(value))[2:]
        hex_v=("0000"+hex_v)[-4:]
        lc=7+int('0x'+hex_a[:2],0)+int('0x'+hex_a[-2:],0)+int('0x'+hex_v[:2],0)+int('0x'+hex_v[-2:],0)
        # print(lc)
        crc=lc^0xFFFF
        crc=crc+1
        cmd=(':0106'+hex_a+hex_v+hex(crc)[-2:]).upper()+'\r\n'
        print(cmd.encode('ascii'))
        # print('finish encode')
        return cmd.encode('ascii')    

    def main_write_M(self,addr,value):
        hex_a=str(hex(addr))[2:]
        if len(hex_a)==1:
            hex_a='080'+hex_a
        if len(hex_a)==2:
            hex_a='08'+hex_a
        print(hex_a)
        if value=="ON":
            hex_v="FF00"
        else:
            hex_v="0000"
        lc=6+int('0x'+hex_a[:2],0)+int('0x'+hex_a[-2:],0)+int('0x'+hex_v[:2],0)+int('0x'+hex_v[-2:],0)
        # print(lc)
        crc=lc^0xFFFF
        crc=crc+1
        cmd=(':0105'+hex_a+hex_v+hex(crc)[-2:]).upper()+'\r\n'
        print(cmd.encode('ascii'))
        # print('finish encode')
        return cmd.encode('ascii')    

    def save_mysql_signal(self):
        # time.sleep(0.01)
        print('data saved')
    #     self.save_my_sql=sql_save()        
    #     self.save_my_sql.signal.connect(self.save_mysql_signal)
    #     self.save_my_sql.start()
    def load_plc_infor(self):
        print('load_plc_infor')
        global kn_plc
        global ser
        global setting
        if kn_plc!=1:
            print('read D410, HEIGHT')
            data=self.main_read_D(410)
            print('data write',data)
            ser.write(data)
            print('finish write line')
            ascii='0000000'
            d410=0
            i=0
            try:
                while True:
                    if ser.in_waiting > 0:
                        buffer = ser.readline()
                        # buffer=buffer[:7]
                        print('buffer=', buffer)
                        ascii = buffer.decode('utf-8')
                        value=ascii[-8:-4]
                        print('value= ', value)
                        d410=int(str(value),16)
                        print('D410= ',d410)
                        break
                # self.ui.lbl_height.setText(str(d410))
            except:
                print('connection lost!!!')
                self.ui.lbl_d_stt.setText('connection lost!!!')
                self.ui.bt_reconnect_plc.setEnabled(True)
                return
            self.ui.lbl_d_stt.setText('Connected')
            self.ui.bt_reconnect_plc.setEnabled(False)

            # read plc data
            # time.sleep(0.02)
            # print('read D490, Max_Dept')
            # data=self.main_read_D(490)
            # ser.write(data)
            # ascii='0000000'
            # d490=0
            # while True:
            #     if ser.in_waiting > 0:
            #         buffer = ser.readline()
            #         # buffer=buffer[:7]
            #         # print('buffer=', buffer)
            #         ascii = buffer.decode('utf-8')
            #         value=ascii[-8:-4]
            #         # print('value= ', value)
            #         d490=int(str(value),16)
            #         print('D490= ',d490)
            #         break
            # self.ui.lbl_max_depth.setText(str(d490))
            # md=str(int(round(int(d490)/2,0)))
            # self.ui.lbl_middle_dept.setText(md)
            # read plc data _ bar length
            time.sleep(0.02)
            data=self.main_read_D(460)
            ser.write(data)
            ascii='0000000'
            d460=0
            while True:
                if ser.in_waiting > 0:
                    buffer = ser.readline()
                    # buffer=buffer[:7]
                    # print('buffer=', buffer)
                    ascii = buffer.decode('utf-8')
                    value=ascii[-8:-4]
                    # print('value= ', value)
                    d460=int(str(value),16)
                    print('D460= ',d460)
                    break
            self.ui.lineEdit_d_bar_length.setText(str(d460))
            # read plc data _ bar height
            time.sleep(0.02)
            data=self.main_read_D(410)
            ser.write(data)
            ascii='0000000'
            d410=0
            while True:
                if ser.in_waiting > 0:
                    buffer = ser.readline()
                    # buffer=buffer[:7]
                    # print('buffer=', buffer)
                    ascii = buffer.decode('utf-8')
                    value=ascii[-8:-4]
                    # print('value= ', value)
                    d410=int(str(value),16)
                    print('D410= ',d410)
                    break
            self.ui.lineEdit_d_height.setText(str(d410))
            # read plc data _ bar height
            # time.sleep(0.02)
            data=self.main_read_D(466)
            ser.write(data)
            ascii='0000000'
            d466=0
            while True:
                if ser.in_waiting > 0:
                    buffer = ser.readline()
                    # buffer=buffer[:7]
                    # print('buffer=', buffer)
                    ascii = buffer.decode('utf-8')
                    value=ascii[-8:-4]
                    # print('value= ', value)
                    d466=int(str(value),16)
                    print('D466= ',d466)
                    break
            self.ui.lineEdit_d_angle.setText(str(d466))
            print("read D510")
            time.sleep(0.02)
            data=self.main_read_D(510)
            print('write data to PLC',data)
            ser.write(data)
            ascii='0000000'
            d510=0
            while True:
                if ser.in_waiting > 0:
                    buffer = ser.readline()
                    # buffer=buffer[:7]
                    print('buffer=', buffer)
                    ascii = buffer.decode('utf-8')
                    value=ascii[-8:-4]
                    # print('value= ', value)
                    d510=int(str(value),16)
                    print('D510= ',d510)
                    break
            self.ui.lineEdit_d_angle.setText(str(d466))
            # time.sleep(0.02)
            # current_index=self.ui.tabWidget.currentIndex()
            # if current_index==0:
        else:
            print('load infor PLC not yet connected')
        setting=0
        self.read_plc=read_D(550)        
        self.read_plc.signal.connect(self.read_plc_signal)
        self.read_plc.start()
        print('read_plc signal send')
    
    def load_form(self):
        global ser
        global setting
        global kn_plc
        global kn_gps
        global ser_gps
        global set_gps
        global list_com
        global R_p
        self.ui.lineEdit_R_pulley.setText(str(R_p))
        self.refresh_com_port_plc()
        print('loading information...')
        plc_port=pd.read_sql('select port from port_setting where device="PLC";',engine_ttp)
        com=plc_port.iloc[0,0]
        print(com)
        # print(list_com)
        if com not in list_com:
            kn_plc=1
            print('plc com not in list')
            self.ui.lbl_d_stt.setText('Connection loss!!!')
        else:
            try:
                ser = serial.Serial(
                port=com, # PLC
                baudrate=9600,
                parity=serial.PARITY_EVEN,
                bytesize=serial.SEVENBITS,
                stopbits=serial.STOPBITS_ONE
                )
                if (ser.isOpen() == False):
                    print ('The Port is Open ')
                        #timeout in seconds
                    ser.timeout = 10
                    ser.open()
                kn_plc=0

            except:
                kn_plc=1
                setting=2
        # self.refresh_com_port_plc()
        print('loading plc information...')
        self.load_plc_infor()

        print('loading lenght information...')
        len_port=pd.read_sql('select port from port_setting where device="MET";',engine_ttp)
        com=len_port.iloc[0,0]
        print(com)
        # print(list_com)
        if com not in list_com:
            kn_plc=1
            print('len com not in list')
            self.ui.lbl_l_stt.setText('LEN measurement Connection loss!!!')
        else:
            try:
                ser_len = serial.Serial(
                port=com, # PLC
                baudrate=9600,
                parity=serial.PARITY_EVEN,
                bytesize=serial.SEVENBITS,
                stopbits=serial.STOPBITS_ONE
                )
                if (ser_len.isOpen() == False):
                    print ('The Port is Open ')
                        #timeout in seconds
                    ser_len.timeout = 10
                    ser_len.open()
                kn_len=0

            except:
                kn_len=1
                set_len=2
        # self.refresh_com_port_plc()
        print('loading len information...')


        # self.menu_gps_window()
        # self.save_my_sql=sql_save()        
        # self.save_my_sql.signal.connect(self.save_mysql_signal)
        # self.save_my_sql.start()


    def read_plc_signal(self,d550,d510,curdate,curtime):
        global setting
        global dept
        dept=str(d550)
        self.ui.lbl_d_dept_trench.setText(str(d550))
        angle=int(d510)
        pic='sim/0d.jpg'
        if angle%2==1:
            angle=angle+1
        if angle>60:
            pic='sim/60d.jpg'
        else:
            pic='sim/'+str(angle)+'d.jpg'
        self.ui.pic_box.setPixmap(QtGui.QPixmap(pic))
        self.ui.lbl_d_date.setText(curdate)
        self.ui.lbl_d_time.setText(curtime)
        global gps_latitude
        global gps_longitude
        global ttcable
        global crcable
        global fromtubin
        global totubin
        global projectname
        global vesselname
        global gposition
        global d
        self.ui.lbl_d_current_laying_cable.setText(crcable)
        self.ui.lbl_d_total_laying_cable.setText(ttcable)
        self.ui.lbl_d_longitude.setText(gps_longitude)
        self.ui.lbl_d_latitude.setText(gps_latitude)
        self.ui.lbl_d_project_name.setText(projectname)
        self.ui.lbl_d_vessel_name.setText(vesselname)
        self.ui.lbl_d_from.setText(fromtubin)
        self.ui.lbl_d_to.setText(totubin)
        self.ui.lbl_d_position.setText(gposition)
        self.ui.lbl_d_distantce.setText(d)
        # time.sleep(0.05)
        # if setting==0:
        #     self.read_plc=read_D(550)        
        #     self.read_plc.signal.connect(self.read_plc_signal)
        #     self.read_plc.start()
    def depth_save_setting(self):
        global setting
        print('save data')
        if setting==1:
            # write plc data
            time.sleep(0.02)
            value=100
            c_value=self.ui.lineEdit_d_bar_length.text()
            try:
                value=int(c_value)
            except:
                value=100
            data=self.main_write_D(460,value)
            print(data)
            ser.write(data)
            ascii='0000000'
            d460=0
            while True:
                if ser.in_waiting > 0:
                    buffer = ser.readline()
                    # buffer=buffer[:7]
                    # print('buffer=', buffer)
                    ascii = buffer.decode('utf-8')
                    value=ascii[-8:-4]
                    # print('value= ', value)
                    d460=int(str(value),16)
                    print('D460= ',d460)
                    break
            # self.ui.lineEdit_bar_length.setText(str(d460))

            time.sleep(0.02)
            value=50
            c_value=self.ui.lineEdit_d_height.text()
            try:
                value=int(c_value)
            except:
                value=50
            data=self.main_write_D(410,value)
            print(data)
            ser.write(data)
            ascii='0000000'
            d410=0
            while True:
                if ser.in_waiting > 0:
                    buffer = ser.readline()
                    # buffer=buffer[:7]
                    # print('buffer=', buffer)
                    ascii = buffer.decode('utf-8')
                    value=ascii[-8:-4]
                    # print('value= ', value)
                    d410=int(str(value),16)
                    print('D410= ',d410)
                    break
            self.ui.lineEdit_d_height.setText(str(d410))
            # time.sleep(0.02)
            value=90
            c_value=self.ui.lineEdit_d_angle.text()
            try:
                value=int(c_value)
            except:
                value=90
            data=self.main_write_D(466,value)
            print(data)
            ser.write(data)
            ascii='0000000'
            d466=0
            while True:
                if ser.in_waiting > 0:
                    buffer = ser.readline()
                    # buffer=buffer[:7]
                    # print('buffer=', buffer)
                    ascii = buffer.decode('utf-8')
                    value=ascii[-8:-4]
                    # print('value= ', value)
                    d466=int(str(value),16)
                    print('D466= ',d466)
                    break
            self.ui.lineEdit_d_angle.setText(str(d466))
            # refresh display
            # print('read D410, HEIGHT')
            # time.sleep(0.2)
            # print('read after write')
            # data=self.main_read_D(410)
            # ser.write(data)
            # # print('finish write line')
            # ascii='0000000'
            # d410=0
            # while True:
            #     if ser.in_waiting > 0:
            #         buffer = ser.readline()
            #         # buffer=buffer[:7]
            #         # print('buffer=', buffer)
            #         ascii = buffer.decode('utf-8')
            #         value=ascii[-8:-4]
            #         # print('value= ', value)
            #         d410=int(str(value),16)
            #         print('D410= ',d410)
            #         break
            # self.ui.lbl_height.setText(str(d410))
            # read plc data
            # time.sleep(0.02)
            # # print('read D490, Max_Dept')
            # data=self.main_read_D(490)
            # ser.write(data)
            # ascii='0000000'
            # d490=0
            # while True:
            #     if ser.in_waiting > 0:
            #         buffer = ser.readline()
            #         # buffer=buffer[:7]
            #         # print('buffer=', buffer)
            #         ascii = buffer.decode('utf-8')
            #         value=ascii[-8:-4]
            #         # print('value= ', value)
            #         d490=int(str(value),16)
            #         print('D490= ',d490)
            #         break
            # self.ui.lbl_max_depth.setText(str(d490))
            QMessageBox.about(self, 'Attention!!!','system have been updated')




    
    def reset_position(self):
        global setting
        global thread_plc
        if setting==1:
            while True:
                if thread_plc==1:
                    msg='Robot busy! please wait a moment'
                    QMessageBox.about(self, 'Attention!!!',msg)
                else:
                    break
            self.ui.bt_depth_reset.setEnabled(False)
            print('reset position')
            setting=1
            time.sleep(0.2)
            cmd=self.main_write_M(1,"ON")
            print(cmd)
            ser.write(cmd)
            ascii='0000000'
            M1=0
            while True:
                if ser.in_waiting > 0:
                    buffer = ser.readline()
                    # buffer=buffer[:7]
                    print('buffer=', buffer)
                    ascii = buffer.decode('utf-8')
                    value=ascii[-8:-4]
                    # print('value= ', value)
                    M1=int(str(value),16)
                    print('M1= ',M1)
                    break
            print('finish reset')
            msg='Position have been reset! Click OK to back to main display'
            QMessageBox.about(self, 'Attention',msg)
            self.ui.bt_depth_reset.setEnabled(True)
            self.ui.tabWidget.setCurrentIndex(0)

    def menu_gps_window(self):
        return
        self.u_gui=GPS_GUI(104)
        self.u_gui.show()
        

    def close_window(self):
        self.close()


class sql_save(QtCore.QThread):

    signal=pyqtSignal(str)
    def __init__(self):
        super(sql_save, self).__init__()
    def run(self):
        global dept
        global gps_latitude
        global gps_longitude
        global setting
        global set_gps
        global kn_gps
        global kn_plc
        global x
        global y
        while True:
            if kn_gps==0 or kn_plc==0:
                mydb=mysql.connector.connect(host='localhost', user='ttpdept', passwd='plcgpsd', database="ttp")
                myCursor=mydb.cursor()
                sql=('insert into data_log (timeupdate,dept,longitude,latitude,set_plc,set_gps,kn_plc,kn_gps,x_co,y_co) '
                    +'values (now(),"'+str(dept)+'","'+str(gps_longitude)+'","'+str(gps_latitude)+'","'+str(setting)
                    +'","'+str(set_gps)+'","'+str(kn_plc)+'","'+str(kn_gps)+'","'+str(x)+'","'+str(y)+'");')
                myCursor.execute(sql)
                mydb.commit()
                myCursor.close()
                mydb.close()
                time.sleep(2)
                self.signal.emit("ok")


class len_handle(QtCore.QThread):
    signal=pyqtSignal(str,str,str,str)
    def __init__(self,nv):
        super(len_handle,self).__init__()
        self.nv=nv
    def run(self):
        while True:
            curdate=datetime.datetime.now().strftime('%y-%m-%d')
            curtime=datetime.datetime.now().strftime('%H:%M:%S')
            self.signal.emit(str(260),str(690),curdate,curtime)
            if kn_len==0 and set_len==0:
                print('read len data')
            time.sleep(0.5)





class read_D(QtCore.QThread):

    signal=pyqtSignal(str,str,str,str)
    def __init__(self,reg):
        super(read_D, self).__init__()
        self.reg=reg
    
    def cmd_read_D(self,addr):
        hex_a=str(hex(addr))[2:]
        if len(hex_a)==1:
            hex_a='100'+hex_a
        if len(hex_a)==2:
            hex_a='10'+hex_a
        if len(hex_a)==3:
            hex_a='1'+hex_a
        # print(hex_a)
        lc=5+int('0x'+hex_a[:2],0)+int('0x'+hex_a[-2:],0)
        # print(lc)
        crc=lc^0xFFFF
        crc=crc+1
        cmd=(':0103'+hex_a+'0001'+hex(crc)[-2:]).upper()+'\r\n'
        print(cmd.encode('ascii'))
        # print('finish encode')
        return cmd.encode('ascii')


    def run(self):
        global ser
        global kn_plc
        global setting
        global thread_plc
        while True:
            curdate=datetime.datetime.now().strftime('%y/%m/%d')
            curtime=datetime.datetime.now().strftime('%H:%M:%S')
            d550=0
            d510=0
            if setting==0 and kn_plc==0:
                thread_plc=1
                try:
                    
                    data=self.cmd_read_D(550)
                    print('read D550 , DEPT ',data)
                    ser.write(data)
                    ascii='0000'
                    d550=0
                    while True:
                        if ser.in_waiting > 0:
                            buffer = ser.readline()
                            # buffer=buffer[:7]
                            print('buffer=', buffer)
                            ascii = buffer.decode('utf-8')
                            print(ascii)
                            value=ascii[-8:-4]
                            print('value= ', value)
                            d550=int(str(value),16)
                            print('D550= ',d550)
                            break
                    # time.sleep(0.02)
                    time.sleep(0.02)
                    print('read D510, angle')
                    data=self.cmd_read_D(510)
                    print('read angle ',data)
                    ser.write(data)
                    ascii='0000'
                    d510=0
                    while True:
                        if ser.in_waiting > 0:
                            buffer = ser.readline()
                            # buffer=buffer[:7]
                            print('buffer=', buffer)
                            ascii = buffer.decode('utf-8')
                            value=ascii[-8:-4]
                            # print('value= ', value)
                            d510=int(str(value),16)
                            print('D510= ',d510)
                            break
                    com='finised read data from plc'
                    print(com)
                except:
                    print('a small error')
            thread_plc=0
            self.signal.emit(str(d550),str(d510),curdate,curtime)
            time.sleep(0.5)


class GPS_GUI(QtWidgets.QMainWindow):
    signal = QtCore.pyqtSignal(int)
    def __init__(self, pre):
        super(GPS_GUI, self).__init__()
        self.ui=Ui_GPSWindow()
        self.ui.setupUi(self)
        self.setWindowFlags(QtCore.Qt.WindowMinimizeButtonHint|QtCore.Qt.WindowMaximizeButtonHint)
        self.setWindowIcon(QtGui.QIcon('hp.ico'))
        self.toolbar = NavigationToolbar(self.ui.MplWidget.canvas,self)
        self.ui.lbl_g_longitude.setText('')
        self.ui.lbl_g_latitude.setText('')
        # self.left = 10
        # self.top = 10
        # self.width = 1920
        # self.height = 1080
        # self.setGeometry(self.left, self.top, self.width, self.height)
        # self . addToolBar ( NavigationToolbar (self.ui.MplWidget.canvas,self))
        self.addToolBar(self.toolbar)
        self.ui.bt_rf_com_gps.clicked.connect(self.load_gps_port)
        self.ui.bt_reconnect_gps.clicked.connect(self.reconnect_gps)
        self.start_gps()
        self.load_gps()
        # self.draw_point('10.258','106.809')

    def start_gps(self):
        global kn_gps
        global set_gps
        global ser_gps
        ports = serial.tools.list_ports.comports()
        available_ports = []
        for p in ports:
            available_ports.append(p.device)
        print(available_ports)
        list_com=available_ports
        gps_port=pd.read_sql('select port from port_setting where device="GPS";',engine_ttp)
        com=gps_port.iloc[0,0]
        print(com)
        if com not in list_com:
            kn_gps=1
            set_gps=1
            print('com GPS not in list')
            self.ui.lbl_g_stt.setText('GPS connection loss!!!')
        else:
            try:
                ser_gps = serial.Serial(
                    port=com, # PLC
                    baudrate=9600,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    bytesize=serial.EIGHTBITS,
                    timeout=10)
                if (ser_gps.isOpen() == False):
                    print ('The Port GPS is Open ')
                        #timeout in seconds
                    ser_gps.timeout = 10
                    ser_gps.open()
                c=0
                ok=0
                while c<100:
                    val = ser_gps.readline()                # read complete line from serial output
                    val=str(val.decode('utf-8'))
                    time.sleep(0.01)
                    data=val.split(',')
                    # print(data[0])
                    if data[0]=='$GNGLL':
                        ok=1
                        break
                    c=c+1
                if ok==1:
                    self.ui.lbl_g_stt.setText('GPS Connected')
                    self.ui.bt_reconnect_gps.setEnabled(False)
                    set_gps=0
                    kn_gps=0
                    self.load_gps()
                    print('gps connected')
                    self.ui.tabWidget.setCurrentIndex(0)
                else:
                    kn_gps=1
                    set_gps=1
                    # self.ui.bt_reconnect_gps.setEnable(True)
                    self.ui.bt_reconnect_gps.setEnabled(True)
            except:
                kn_gps=1
                set_gps=1

    def draw_point(self,lat,lon):
        global p
        global x
        global y
        global fromtubin
        global totubin
        global tb_list
        print(lat,lon)
        if lon!='' and lat!='':
            try:
            # if 1>0:
                x,y=p(float(lat),float(lon))
                print(x,y)
                x=float(x)
                y=float(y)
                if x>691865 and x<704765 and y>1128820 and y<1137940:
                    global x0
                    global y0
                    global gposition
                    if x0>0 and y0>0:
                        khoangcach2=(x-x0)*(x-x0)+(y-y0)*(y-y0)
                        khoangcach=math.floor(math.sqrt(khoangcach2))
                        gposition=fromtubin+'-'+str(khoangcach)
                    self.ui.MplWidget.canvas.axes.clear () 
                    self.ui.MplWidget.canvas.axes.imshow(self.img,aspect='auto',extent=([691865,704765,1128820,1137940]))
                    self.ui. MplWidget . canvas . axes . set_title ( 'map tracking' ) 
                    # self.ui.MplWidget.canvas.axes.arrow(x,y,8,8,head_width = 60,width = 10,ec ='cyan')
                    self.ui.MplWidget.canvas.axes.scatter(x,y, color='blue')
                    self.axins = self.ui.MplWidget.canvas.axes.inset_axes([0.65, 0.65, 0.33, 0.33])
                    self.axins.imshow(self.img,aspect='auto',extent=([691865,704765,1128820,1137940]))
                    self.axins.set_xlim(x-50, x+50)
                    self.axins.set_ylim(y-50, y+50)
                    self.axins.set_xticklabels('')
                    self.axins.set_yticklabels('')
                    # self.scat2=self.axins.arrow(x,y,8,8,head_width = 60,width = 10,ec ='cyan')
                    self.scat2=self.axins.scatter(x,y,s=15*15,color='blue')
                    self.zoom=self.ui.MplWidget.canvas.axes.indicate_inset_zoom(self.axins)
                    print('draw point gps')
                    self.ui. MplWidget . canvas . draw ()
                    # self.ui.MplWidget.canvas.flush_events()
                    self.ui.lbl_g_stt.setText("location updated")
                else:
                    self.ui.lbl_g_stt.setText("loc. Out of Map")
            except:
            # else:
                print('draw location error')
        else:
            print('gps not yet read location')

    
    def update_graph(self):
        self.ui.MplWidget.canvas.axes.clear () 
        self.img=mpimg.imread('./cap/tongthe_r2.png')
        self.ui.MplWidget.canvas.axes.imshow(self.img,aspect='auto',extent=([691865,704765,1128820,1137940]))
        self.ui. MplWidget . canvas . axes . set_title ( 'map tracking' ) 
        self.ui. MplWidget . canvas . draw ()
        print("finish draw")

    def load_gps_port(self):
        global list_com
        ports = serial.tools.list_ports.comports()
        available_ports = []
        for p in ports:
            available_ports.append(p.device)
        print(available_ports)
        c=self.ui.cb_gps_com.count()
        try:
            while c>=0:
                self.ui.cb_gps_com.removeItem(c)
                c=c-1
        except:
            print('refresh combo box')
        for port in available_ports:
            self.ui.cb_gps_com.addItem(port)
        print('import port ok')
    
    def reconnect_gps(self):
        global ser_gps
        global kn_gps
        global set_gps
        # self.ui.bt_reconnect_gps.setEnabled(False)
        com=str(self.ui.cb_gps_com.currentText())
        print(com)
        try:
            ser_2 = serial.Serial(
                port=com, # GPS
                baudrate=9600,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS,
                timeout=10)
            if (ser_2.isOpen() == False):
                print ('The Port GPS is Open ')
                    #timeout in seconds
                ser_2.timeout = 10
                ser_2.open()
            c=0
            ok=0
            while c<100:
                val = ser_2.readline()                # read complete line from serial output
                val=str(val.decode('utf-8'))
                time.sleep(0.01)
                data=val.split(',')
                # print(data[0])
                if data[0]=='$GNGLL':
                    ok=1
                    break
                c=c+1
            if ok==1:
                ser_gps=ser_2
                QMessageBox.about(self, 'Thông báo','GPS  connected!')
                self.ui.lbl_g_stt.setText('GPS Connected')
                self.ui.bt_reconnect_gps.setEnabled(False)
                set_gps=0
                kn_gps=0
                self.load_gps()
                print('gps connected')
                sql_update_gps_com='update port_setting set port="'+com+'" where device="GPS";'
                mydb=mysql.connector.connect(host='localhost', user='ttpdept', passwd='plcgpsd', database="ttp")
                myCursor=mydb.cursor()
                myCursor.execute(sql_update_gps_com)
                mydb.commit()
                myCursor.close()
                mydb.close()
                self.ui.tabWidget.setCurrentIndex(0)
            else:
                kn_gps=1
                set_gps=1
                QMessageBox.about(self, 'Thông báo','không kết nối đến được gps!\nVui lòng kiểm tra lại.')
                # self.ui.bt_reconnect_gps.setEnabled(True)
                self.ui.bt_reconnect_gps.setEnabled(True)
                self.ui.lbl_g_stt.setText('GPS connection loss!!!')
            
        except:
            kn_gps=1
            set_gps=1
            QMessageBox.about(self, 'Thông báo','không kết nối đến được gps!\nVui lòng kiểm tra lại.')
            self.ui.bt_reconnect_gps.setEnabled(True)
            self.ui.lbl_g_stt.setText('GPS connection loss!!!')


    def load_gps(self):
        global set_gps
        global thread_gps_n
        self.update_graph()
        self.load_gps_port()
        # if set_gps==0:
        print('read gps location')
        thread_gps_n=thread_gps_n+1
        time.sleep(1)
        self.gps_location=read_gps(thread_gps_n)        
        self.gps_location.signal.connect(self.gps_location_signal)
        self.gps_location.start()
        if set_gps!=0:
            print('gps not yet connected')
            self.ui.lbl_g_stt.setText('GPS Connection lost!!!')
            # QMessageBox.about(self, 'Thông báo','GPS chưa được kết nối!\nVui lòng kiểm tra lại module GPS và kết nối lại')


    def gps_location_signal(self,lo,la,curdate,curtime):
        # read_gps().stop()
        # self.gps_location.stop()
        # self.gps_location.wait()
        global set_gps
        global gps_latitude
        global gps_longitude
        global gposition
        global gps_latitude
        global gps_longitude
        global projectname
        global vesselname
        global fromtubin
        global totubin
        global dept
        global ttcable
        global crcable
        global cgps
        # lo='10744.16087'
        # la='1623.72913'
        try:
            if set_gps==0:
                if lo=='':
                    lo=''
                else:
                    lott=str(float(lo)/100)
                    print(lott)
                    alo=lott.split('.')
                    minx=(str(alo[1])[:2]+'.'+str(alo[1])[2:])
                    print(minx)
                    lomin=float(str(alo[1])[:2]+'.'+str(alo[1])[2:])/60
                    lo=(str(float(alo[0])+lomin)+"000000")[:11]
                if la=='':
                    la=''
                else:
                    latt=str(float(la)/100)
                    ala=latt.split('.')
                    lamin=float(str(ala[1])[:2]+'.'+str(ala[1])[2:])/60
                    la=(str(float(ala[0])+lamin)+"000000")[:11]
                gps_longitude=lo
                gps_latitude=la
                print('gps cv',lo,la)
                # self.draw_point(la,lo)
                # lo='10.258'
                # la='106.809'
                # self.gps_location=read_gps()        
                # self.gps_location.signal.connect(self.gps_location_signal)
                # self.gps_location.start()
                print('reconect gps')
        except:
                print('gps wrong')
                time.sleep(0.5)
                # self.gps_location=read_gps()        
                # self.gps_location.signal.connect(self.gps_location_signal)
                # self.gps_location.start()
        global p
        global x
        global y
        global a
        global b
        global d
        print(la,lo)
        if lo!='' and la!='':
            try:
            # if 1>0:
                x,y=p(float(la),float(lo))
                print(x,y)
                x=float(x)
                y=float(y)   
                dc=round(abs(a*x-y+b)/math.sqrt(a*a+1),2)
                d=str(round(dc/2))
            except:
                print('latlon error,convert xy error') 
                
        
        if cgps>20:
            try:
                if lo!='' and la!='':
                    self.draw_point(la,lo)
            except:
                print('latlon error,cannot refresh map')
            cgps=0
        else:
            cgps=cgps+1
        self.ui.lbl_g_longitude.setText(lo)
        self.ui.lbl_g_latitude.setText(la)
        self.ui.lbl_g_date.setText(curdate)
        self.ui.lbl_g_time.setText(curtime)
        self.ui.lbl_g_project_name.setText(projectname)
        self.ui.lbl_g_vessel_name.setText(vesselname)
        self.ui.lbl_g_from.setText(fromtubin)
        self.ui.lbl_g_to.setText(totubin)
        self.ui.lbl_g_total_laying_cable.setText(ttcable)
        self.ui.lbl_g_current_laying_cable.setText(crcable)
        self.ui.lbl_g_dept_trench.setText(dept)
        self.ui.lbl_g_position.setText(gposition)
        self.ui.lbl_g_distantce.setText(d)


class read_gps(QtCore.QThread):

    signal=pyqtSignal(str,str,str,str)
    def __init__(self,thread_no):
        super(read_gps, self).__init__()
        self.thread_no=thread_no
        
    def gps_location(self):
        global ser_gps
        global set_gps
        global kn_gps
        global thread_gps_n
        
        while self.thread_no==thread_gps_n:
            print('gps thread ',self.thread_no)
            curdate=datetime.datetime.now().strftime('%y/%m/%d')
            curtime=datetime.datetime.now().strftime('%H:%M:%S')
            lo=''
            la=''
            if set_gps==0 and kn_gps!=1:
                while True:
                    val = ser_gps.readline()                # read complete line from serial output
                    val=str(val.decode('utf-8'))
                    time.sleep(0.02)
                    data=val.split(',')
                    # print(data[0])
                    if data[0]=='$GNGLL':
                        lo=data[1]
                        la=data[3]
                        print(val)
                        break
            self.signal.emit(lo,la,curdate,curtime)
            time.sleep(0.5)

    def run(self):
        self.gps_location()






app=QApplication([])
app.setAttribute(Qt.AA_EnableHighDpiScaling)
application=MyWindow()
application.setWindowIcon(QtGui.QIcon('hp.ico'))
trayIcon = QtWidgets.QSystemTrayIcon(QtGui.QIcon('hp.ico'), app) 
trayIcon.show()
application.show()
sys.exit(app.exec())