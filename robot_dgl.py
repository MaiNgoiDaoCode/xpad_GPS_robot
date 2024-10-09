# -*- coding: utf-8 -*-
"""
Created on Tue May 19 10:50:13 2020

@author: ngmai1
"""

from re import X
from PyQt5.QtWidgets import (QWidget, QMainWindow, QTextEdit, QAction, QFileDialog, QApplication, QMessageBox)
from PyQt5.QtPrintSupport import (QPrinter,QPrintDialog)
from PyQt5.QtCore import *
from PyQt5.QtCore import QThread, pyqtSignal, QTimer, QPoint, QDateTime, QRect
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
import getpass
import mysql.connector
from datetime import datetime
from pandas.io import sql
from sqlalchemy import create_engine
import datetime
import numpy as np
import shutil
from ui_dept2 import Ui_MainWindow
from ui_gps2 import Ui_GPSWindow
import serial
import time
import serial.tools.list_ports
import io
import  random
from pyproj import Proj
import math
p = Proj(proj='utm',zone=48,ellps='WGS84', preserve_units=False)

cwd = os.getcwd()
preset=pd.read_excel('pre_setting.xlsx')
print(preset)
kn_plc=1 #cần kết nối đến bộ đo độ sâu
kn_gps=1 # cần kết nối đến gps
kn_len=1 # cần kết nối đến bộ đo chiều dài
start_len=0
start_click=0
stop_click=0
ser=serial.Serial()
ser_gps=serial.Serial()
ser_len=serial.Serial()
setting=1
set_gps=1
set_len=1
new_record=0
dept="0"
deg_dept="0"
start_save_dept=0
start_reset_dept=0
gps_longitude=''
gps_latitude=''
thread_plc=0
thread_gps_n=0
projectname=preset.iloc[0,2]
vesselname=preset.iloc[0,3]
fromtubin=preset.iloc[0,0]
totubin=preset.iloc[0,1]
gposition=str(preset.iloc[0,0])+'-'
cgps=0
x=0
y=0
list_com=[]
engine_ttp = create_engine('mysql+mysqlconnector://ttpdept:plcgpsd@localhost:3306/ttp', echo=False)
mydb=mysql.connector.connect(host="localhost", user='ttpdept', passwd='plcgpsd', database="ttp")
myCursor=mydb.cursor()
tb_list=pd.read_sql('select * from location_detail where project="TPD2" and tuabin="'+str(fromtubin)+'";',engine_ttp)
ttlen=pd.read_sql('select sum(lentt) from (select id,2*3.1416*R*deg/360/1000 as lentt from leng_log group by id) as tt;',engine_ttp)
try:
    ttcable=str(round(float(ttlen.iloc[0,0]),1))
except:
    ttcable="0"
ttlen=pd.read_sql('select sum(lentt) from (select id,2*3.1416*R*deg/360/1000 as lentt from leng_log where date_cal=date(now()) group by id) as tt;',engine_ttp)
try:
    crcable=str(round(float(ttlen.iloc[0,0]),1))
except:
    crcable="0"

x0=0
y0=0
try:
    if len(tb_list)>0:
        x0=float(tb_list.iloc[0,4])
        y0=float(tb_list.iloc[0,3])
except:
    print('wrong coodinate for tuabin')
pulley_para=pd.read_sql('select port from port_setting where device="R_pulley";',engine_ttp)
R_p=int(pulley_para.iloc[0,0])

# try to global c_value
b_value="0"
h_value="0"
d_value="0"


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
            self.ui.lbl_d_stt.setStyleSheet("color: rgb(0, 255, 0);\nbackground-color: rgba(85, 85, 127,80);")
            self.ui.lbl_d_stt.setText('Connected!')
        if kn_gps==0:
            print('alert GPS not yet connect')
        self.ui.tabWidget.currentChanged.connect(self.tab_change)
        self.ui.menu_GPS_Window.triggered.connect(self.menu_gps_window)
        self.ui.bt_depth_save.clicked.connect(self.depth_save_setting)
        self.ui.bt_depth_reset.clicked.connect(self.reset_position)
        self.ui.bt_home.clicked.connect(self.active_homepage)
        self.ui.bt_rf_com_plc.clicked.connect(self.refresh_com_port_plc)
        self.ui.bt_reconnect_plc.clicked.connect(self.reconnect_plc)
        self.ui.bt_reconnect_len.clicked.connect(self.reconnect_len)
        self.ui.bt_rf_com_len.clicked.connect(self.rf_com_len)
        self.ui.bt_START_COUNT.clicked.connect(self.start_stop_len)
        self.menu_gps_window()
        self.save_my_sql=sql_save()        
        self.save_my_sql.signal.connect(self.save_mysql_signal)
        self.save_my_sql.start()
        self.save_len=len_handle(0)        
        self.save_len.signal.connect(self.len_handle_signal)
        self.save_len.start()
        self.up_cable=sql_read_len()        
        self.up_cable.signal.connect(self.up_cable_signal)
        self.up_cable.start()
        self.ui.bt_update_pulley.clicked.connect(self.update_pulley)

    def update_pulley(self):
        global R_p
        global new_record
        try:
            R_p_n=int(self.ui.lineEdit_R_pulley.text())
            if R_p_n!=R_p:
                msg='New value of Radius!\nDo you want to update last length record and recalculate length cable?\nYes: update Radius and last record (maximum 100 round) counting.\nNo: update Radius and create new record from this comfirmation'
                qs=QMessageBox.question(self, 'Attention',msg,QMessageBox.Yes|QMessageBox.No|QMessageBox.Cancel)
                if qs==QMessageBox.Yes:
                    print('update last record also')
                    engine_ttp = create_engine('mysql+mysqlconnector://ttpdept:plcgpsd@localhost:3306/ttp', echo=False)
                    # update record only
                    print('update record only, Radius =',R_p_n)
                    cur_record=pd.read_sql('select max(id) from leng_log where date_cal=date(now());',engine_ttp)
                    if len(cur_record)>0:
                        idx=int(cur_record.iloc[0,0])
                        sql_upr='update leng_log set R='+str(R_p_n)+',timeupdate=now() where id='+str(idx)+';'
                        mydb=mysql.connector.connect(host="localhost", user='ttpdept', passwd='plcgpsd', database="ttp")
                        myCursor=mydb.cursor()
                        myCursor.execute(sql_upr)
                        mydb.commit()
                        myCursor.close()
                        mydb.close()
                    mydb=mysql.connector.connect(host="localhost", user='ttpdept', passwd='plcgpsd', database="ttp")
                    myCursor=mydb.cursor()
                    sql_c=('update port_setting set port="'+str(R_p_n)+'" where device="R_pulley";')
                    myCursor.execute(sql_c)
                    mydb.commit()
                    myCursor.close()
                    mydb.close()
                    msg='Radius of pulley from last record (maximum 100 round) have been updated!'
                    QMessageBox.about(self, 'Attention',msg)
                    R_p=R_p_n
                elif qs==QMessageBox.No:
                    print('update new line')
                    mydb=mysql.connector.connect(host='localhost', user='ttpdept', passwd='plcgpsd', database="ttp")
                    myCursor=mydb.cursor()
                    sql_c=('update port_setting set port="'+str(R_p_n)+'" where device="R_pulley";')
                    myCursor.execute(sql_c)
                    mydb.commit()
                    myCursor.close()
                    mydb.close()
                    R_p=R_p_n
                    new_record=1
                    msg='Radius of pulley have been updated!'
                    QMessageBox.about(self, 'Attention',msg)
            else:
                msg='value already updated!'
                QMessageBox.about(self, 'Attention',msg)
        except:
            msg='please check input value for Radius of pulley should be number!'
            QMessageBox.about(self, 'Attention',msg)

    def len_handle_signal(self,stt):
        if 'start' in stt:
            print('finish start count leng')
            msg='length measurement start counting!'
            QMessageBox.about(self, 'Attention',msg)
            self.ui.bt_START_COUNT.setStyleSheet("background-color: rgb(160, 0, 0);\nborder-radius: 15px;")
            self.ui.bt_START_COUNT.setText("STOP COUNTER")
        elif 'stop' in stt:
            print('finish stop count length')
            msg='length measurement stoped counting!'
            QMessageBox.about(self, 'Attention',msg)
            self.ui.bt_START_COUNT.setStyleSheet("background-color: rgb(0, 170, 0);\nborder-radius: 15px;")
            self.ui.bt_START_COUNT.setText("START COUNTER")
        else:
            print('len do nothing')

    def up_cable_signal(self,tt1,tt2):
        global gps_latitude
        global gps_longitude
        global ttcable
        global crcable
        global fromtubin
        global totubin
        global projectname
        global vesselname
        global gposition
        self.ui.lbl_d_current_laying_cable.setText(crcable)
        self.ui.lbl_d_total_laying_cable.setText(ttcable)
        self.ui.lbl_d_longitude.setText(gps_latitude)
        self.ui.lbl_d_latitude.setText(gps_longitude)
        self.ui.lbl_d_project_name.setText(projectname)
        self.ui.lbl_d_vessel_name.setText(vesselname)
        self.ui.lbl_d_from.setText(fromtubin)
        self.ui.lbl_d_to.setText(totubin)
        self.ui.lbl_d_position.setText(gposition)
    
    def start_stop_len(self):
        print('handle start stop len')
        global kn_len
        global start_len
        global start_click
        global stop_click
        if kn_len==0:
            if start_len==0:
                start_len=1
                stop_click=0
                start_click=1
            else:
                start_len=0
                stop_click=1
                start_click=0
        else:
            msg='length measurement not yet connected!'
            QMessageBox.about(self, 'Attention',msg)

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
            port=com, # com bộ đo chiều dài
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
                self.ui.lbl_d_stt.setStyleSheet("color: rgb(0, 255, 0);\nbackground-color: rgba(85, 85, 127,80);")
                self.ui.lbl_l_stt.setText('len measeurement connected')
            else:
                QMessageBox.about(self, 'Alert','Wrong COM port for len measurement')
                set_len=2
                kn_len=1
                self.ui.bt_reconnect_plc.setEnabled(True)
        except:
            QMessageBox.about(self, 'Alert','connection to lenght measurement divice loss!\nPlease check again.')
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
                self.ui.lbl_d_stt.setStyleSheet("color: rgb(0, 255, 0);\nbackground-color: rgba(85, 85, 127,80);")
                self.ui.lbl_d_stt.setText('connected')
            else:
                QMessageBox.about(self, 'Alert','Wrong COM port for dept device')
                setting=2
                self.ui.bt_reconnect_plc.setEnabled(True)
        except:
            QMessageBox.about(self, 'Alert','connection do dept device loss!\nPlease check again.')
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

    def main_read_D(self,addr):
        hex_a=str(hex(addr))[2:]
        if len(hex_a)==1:
            hex_a='100'+hex_a
        if len(hex_a)==2:
            hex_a='10'+hex_a
        if len(hex_a)==3:
            hex_a='1'+hex_a
        lc=5+int('0x'+hex_a[:2],0)+int('0x'+hex_a[-2:],0)
        crc=lc^0xFFFF
        crc=crc+1
        cmd=(':0103'+hex_a+'0001'+hex(crc)[-2:]).upper()+'\r\n'
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
        crc=lc^0xFFFF
        crc=crc+1
        cmd=(':0106'+hex_a+hex_v+hex(crc)[-2:]).upper()+'\r\n'
        print(cmd.encode('ascii'))
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
        crc=lc^0xFFFF
        crc=crc+1
        cmd=(':0105'+hex_a+hex_v+hex(crc)[-2:]).upper()+'\r\n'
        print(cmd.encode('ascii'))
        return cmd.encode('ascii')    

    def save_mysql_signal(self):
        print('data len,lot,lat saved')

    def load_plc_infor(self):
        print('load_plc_infor')
        global kn_plc
        global ser
        global setting
        if kn_plc!=1:
            # print('read D410, HEIGHT')
            data=self.main_read_D(410)
            ser.write(data)
            # print('finish write line')
            ascii='0000000'
            d410=0
            i=0
            try:
                while True:
                    if ser.in_waiting > 0:
                        buffer = ser.readline()
                        ascii = buffer.decode('utf-8')
                        value=ascii[-8:-4]
                        d410=int(str(value),16)
                        print('D410= ',d410)
                        break
            except:
                print('connection lost!!!')
                self.ui.lbl_d_stt.setStyleSheet("color: rgb(255, 0, 0);\nbackground-color: rgba(85, 85, 127,80);")
                self.ui.lbl_d_stt.setText('connection lost!!!')
                self.ui.bt_reconnect_plc.setEnabled(True)
                return
            self.ui.lbl_d_stt.setStyleSheet("color: rgb(0, 255, 0);\nbackground-color: rgba(85, 85, 127,80);")
            self.ui.lbl_d_stt.setText('Connected')
            self.ui.bt_reconnect_plc.setEnabled(False)
            time.sleep(0.02)
            data=self.main_read_D(460)
            ser.write(data)
            ascii='0000000'
            d460=0
            while True:
                if ser.in_waiting > 0:
                    buffer = ser.readline()
                    ascii = buffer.decode('utf-8')
                    value=ascii[-8:-4]
                    d460=int(str(value),16)
                    print('D460= ',d460)
                    break
            self.ui.lineEdit_d_bar_length.setText(str(d460))
            time.sleep(0.02)
            data=self.main_read_D(410)
            ser.write(data)
            ascii='0000000'
            d410=0
            while True:
                if ser.in_waiting > 0:
                    buffer = ser.readline()
                    ascii = buffer.decode('utf-8')
                    value=ascii[-8:-4]
                    d410=int(str(value),16)
                    print('D410= ',d410)
                    break
            self.ui.lineEdit_d_height.setText(str(d410))
            data=self.main_read_D(466)
            ser.write(data)
            ascii='0000000'
            d466=0
            while True:
                if ser.in_waiting > 0:
                    buffer = ser.readline()
                    ascii = buffer.decode('utf-8')
                    value=ascii[-8:-4]
                    d466=int(str(value),16)
                    print('D466= ',d466)
                    break
            self.ui.lineEdit_d_angle.setText(str(d466))
            setting=0
            self.read_plc=read_D(550)        
            self.read_plc.signal.connect(self.read_plc_signal)
            self.read_plc.start()
            print('read_plc signal send')
        else:
            print('load infor PLC not yet connected')
    
    def load_form(self):
        global ser
        global ser_len
        global set_len
        global setting
        global kn_plc
        global kn_gps
        global kn_len
        global ser_gps
        global set_gps
        global list_com
        global R_p
        global gps_latitude
        global gps_longitude
        global ttcable
        global crcable
        global fromtubin
        global totubin
        global projectname
        global vesselname
        global gposition
        self.ui.lbl_d_current_laying_cable.setText(crcable)
        self.ui.lbl_d_total_laying_cable.setText(ttcable)
        self.ui.lbl_d_longitude.setText(gps_latitude)
        self.ui.lbl_d_latitude.setText(gps_longitude)
        self.ui.lbl_d_project_name.setText(projectname)
        self.ui.lbl_d_vessel_name.setText(vesselname)
        self.ui.lbl_d_from.setText(fromtubin)
        self.ui.lbl_d_to.setText(totubin)
        self.ui.lbl_d_position.setText(gposition)
        self.ui.lineEdit_R_pulley.setText(str(int(R_p)))
        self.refresh_com_port_plc()
        self.rf_com_len()
        print('loading information...')
        plc_port=pd.read_sql('select port from port_setting where device="PLC";',engine_ttp)
        com=plc_port.iloc[0,0]
        print(com)
        if com not in list_com:
            kn_plc=1
            print('plc com not in list')        
            self.ui.lbl_d_stt.setStyleSheet("color: rgb(255, 0, 0);\nbackground-color: rgba(85, 85, 127,80);")
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
                    ser.timeout = 10
                    ser.open()
                kn_plc=0

            except:
                kn_plc=1
                setting=2
        print('loading plc information...')
        self.load_plc_infor()
        print('loading lenght information...')
        len_port=pd.read_sql('select port from port_setting where device="MET";',engine_ttp)
        com=len_port.iloc[0,0]
        print(com)
        if com not in list_com:
            kn_len=1
            print('len com not in list')
            self.ui.lbl_l_stt.setStyleSheet("color: rgb(255, 0, 0);\nbackground-color: rgba(85, 85, 127,80);")
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
                    ser_len.timeout = 10
                    ser_len.open()
                kn_len=0
                set_len=0
                self.ui.lbl_l_stt.setStyleSheet("color: rgb(0, 255, 0);\nbackground-color: rgba(85, 85, 127,80);")
                self.ui.lbl_l_stt.setText('LEN measurement Connected!!!')
                self.ui.bt_reconnect_len.setEnabled(False)
                global start_click
                start_click=1
                self.start_stop_len()
            except:
                kn_len=1
                set_len=2
                self.ui.lbl_l_stt.setStyleSheet("color: rgb(255, 0, 0);\nbackground-color: rgba(85, 85, 127,80);")
                self.ui.lbl_l_stt.setText('LEN measurement Connection loss!!!')           
        print('loading len information...')

    def read_plc_signal(self,d550,d510,curdate,curtime):
        global setting
        global dept
        global deg_dept
        if 'save' in d550:
            print('finish save')
            msg='new setting have been updated!'
            QMessageBox.about(self, 'Attention',msg)
        elif 'reset' in d550:
            msg='Position have been reset! Click OK to back to main display'
            QMessageBox.about(self, 'Attention',msg)
            self.ui.bt_depth_reset.setEnabled(True)
            self.ui.tabWidget.setCurrentIndex(0)
        else:
            print('update picbox')
            dept=str(d550)
            deg_dept=str(d510)
            self.ui.lbl_d_dept_trench.setText(str(d550))
            angle=int(d510)
            print('d510',d510)
            pic='sim/0d.jpg'
            if angle%2==1:
                angle=angle+1
            if angle>60:
                pic='sim/60d.jpg'
            else:
                pic='sim/'+str(angle)+'d.jpg'
            print(pic)
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
        self.ui.lbl_d_current_laying_cable.setText(crcable)
        self.ui.lbl_d_total_laying_cable.setText(ttcable)
        self.ui.lbl_d_longitude.setText(gps_latitude)
        self.ui.lbl_d_latitude.setText(gps_longitude)
        self.ui.lbl_d_project_name.setText(projectname)
        self.ui.lbl_d_vessel_name.setText(vesselname)
        self.ui.lbl_d_from.setText(fromtubin)
        self.ui.lbl_d_to.setText(totubin)
        self.ui.lbl_d_position.setText(gposition)

    def depth_save_setting(self):
        global setting
        global b_value
        global h_value
        global d_value
        global start_save_dept
        b_value=self.ui.lineEdit_d_bar_length.text()
        h_value=self.ui.lineEdit_d_height.text()
        d_value=self.ui.lineEdit_d_angle.text()
        start_save_dept=1
        print('signal save data send')

    def reset_position(self):
        global setting
        global thread_plc
        global start_reset_dept
        setting=1
        start_reset_dept=1
        print('signal reset send')

    def menu_gps_window(self):
        self.u_gui=GPS_GUI(104)
        self.u_gui.show()
        
    def close_window(self):
        self.close()

class sql_read_len(QtCore.QThread):
    signal=pyqtSignal(str,str)
    def __init__(self):
        super(sql_read_len, self).__init__()
    def run(self):
        global ttcable
        global crcable
        engine_ttp = create_engine('mysql+mysqlconnector://ttpdept:plcgpsd@localhost:3306/ttp', echo=False)
        while True:
            ttlen=pd.read_sql('select sum(lentt) from (select id,2*3.1416*R*deg/360/1000 as lentt from leng_log group by id) as tt;',engine_ttp)
            try:
                ttcable=str(round(float(ttlen.iloc[0,0]),1))
            except:
                ttcable="0"
            ttlen=pd.read_sql('select sum(lentt) from (select id,2*3.1416*R*deg/360/1000 as lentt from leng_log where date_cal=date(now()) group by id) as tt;',engine_ttp)
            try:
                crcable=str(round(float(ttlen.iloc[0,0]),1))
            except:
                crcable="0"
            self.signal.emit(ttcable,crcable)
            time.sleep(1)

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
                sql_c=('insert into data_log (timeupdate,dept,longitude,latitude,set_plc,set_gps,kn_plc,kn_gps,x_co,y_co) '
                    +'values (now(),"'+str(dept)+'","'+str(gps_longitude)+'","'+str(gps_latitude)+'","'+str(setting)
                    +'","'+str(set_gps)+'","'+str(kn_plc)+'","'+str(kn_gps)+'","'+str(x)+'","'+str(y)+'");')
                myCursor.execute(sql_c)
                mydb.commit()
                myCursor.close()
                mydb.close()
                time.sleep(2)
                self.signal.emit("ok")

class len_handle(QtCore.QThread):
    signal=pyqtSignal(str)
    def __init__(self,nv):
        super(len_handle,self).__init__()
        self.nv=nv

    def cmd_read_D(self,addr):
        hex_a=str(hex(addr))[2:]
        if len(hex_a)==1:
            hex_a='100'+hex_a
        if len(hex_a)==2:
            hex_a='10'+hex_a
        if len(hex_a)==3:
            hex_a='1'+hex_a
        lc=5+int('0x'+hex_a[:2],0)+int('0x'+hex_a[-2:],0)
        crc=lc^0xFFFF
        crc=crc+1
        cmd=(':0103'+hex_a+'0001'+hex(crc)[-2:]).upper()+'\r\n'
        print(cmd.encode('ascii'))
        return cmd.encode('ascii')
    
    def run(self):
        global start_len
        global start_click
        global stop_click
        global kn_len
        global set_len
        global R_p
        global ser_len
        global new_record
        while True:
            engine_ttp = create_engine('mysql+mysqlconnector://ttpdept:plcgpsd@localhost:3306/ttp', echo=False)
            if kn_len==0 and set_len==0:
                # check start click
                if start_click==1:
                    # enable M2
                    value="ON"
                    hex_a=str(hex(2))[2:]
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
                    crc=lc^0xFFFF
                    crc=crc+1
                    cmd=(':0105'+hex_a+hex_v+hex(crc)[-2:]).upper()+'\r\n'
                    print(cmd.encode('ascii'))
                    cmd_rs=cmd.encode('ascii')
                    ser_len.write(cmd_rs)
                    M2=0
                    while True:
                        if ser_len.in_waiting > 0:
                            buffer = ser_len.readline()
                            print('buffer=', buffer)
                            ascii = buffer.decode('utf-8')
                            value=ascii[-8:-4]
                            M1=int(str(value),16)
                            print('M2= ',M2)
                            break
                    print('finish reset')
                    start_click=0
                    self.signal.emit('start')
                if stop_click==1:
                    value="OFF"
                    hex_a=str(hex(2))[2:]
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
                    crc=lc^0xFFFF
                    crc=crc+1
                    cmd=(':0105'+hex_a+hex_v+hex(crc)[-2:]).upper()+'\r\n'
                    print(cmd.encode('ascii'))
                    cmd_rs=cmd.encode('ascii')
                    ser_len.write(cmd_rs)
                    M2=0
                    while True:
                        if ser_len.in_waiting > 0:
                            buffer = ser_len.readline()
                            print('buffer=', buffer)
                            ascii = buffer.decode('utf-8')
                            value=ascii[-8:-4]
                            M1=int(str(value),16)
                            print('M2= ',M2)
                            break
                    print('finish reset')
                    stop_click=0   
                    self.signal.emit('stoped')                
                print('read D510, angle')
                data=self.cmd_read_D(510)
                ser_len.write(data)
                ascii='0000'
                d510=0
                while True:
                    if ser_len.in_waiting > 0:
                        buffer = ser_len.readline()
                        print('buffer=', buffer)
                        ascii = buffer.decode('utf-8')
                        value=ascii[-8:-4]
                        d510=int(str(value),16)
                        print('D510= ',d510)
                        break
                com='finised read data from len'
                print(com)
                if d510>0:
                    engine_ttp = create_engine('mysql+mysqlconnector://ttpdept:plcgpsd@localhost:3306/ttp', echo=False)
                    mydb=mysql.connector.connect(host="localhost", user='ttpdept', passwd='plcgpsd', database="ttp")
                    myCursor=mydb.cursor()
                    # update record only
                    print('update record only, Value =',d510)
                    if d510>50000:
                            d510=d510-65535
                    cur_record=pd.read_sql('select max(id) from leng_log where date_cal=date(now());',engine_ttp)
                    if len(cur_record)>0:
                        idx=int(cur_record.iloc[0,0])
                        sql_upr='update leng_log set deg='+str(d510)+',timeupdate=now() where id='+str(idx)+';'
                        myCursor=mydb.cursor()
                        myCursor.execute(sql_upr)
                        mydb.commit()
                        myCursor.close()
                        mydb.close()
                    else:
                        # new record today
                        id_r=pd.read_sql('select count(*) from leng_log;',engine_ttp)
                        idx=id_r.iloc[0,0]+1
                        sql_nr='insert into leng_log values ('+str(idx)+','+str(R_p)+','+str(d510)+',now(),date(now()),"");'
                        myCursor=mydb.cursor()
                        myCursor.execute(sql_nr)
                        mydb.commit()
                        myCursor.close()
                        mydb.close()
                    if d510>36000 or new_record==1 or d510<-3600:
                        # reset len
                        value="ON"
                        hex_a=str(hex(1))[2:]
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
                        crc=lc^0xFFFF
                        crc=crc+1
                        cmd=(':0105'+hex_a+hex_v+hex(crc)[-2:]).upper()+'\r\n'
                        print(cmd.encode('ascii'))
                        cmd_rs=cmd.encode('ascii')
                        ser_len.write(cmd_rs)
                        M1=0
                        while True:
                            if ser_len.in_waiting > 0:
                                buffer = ser_len.readline()
                                print('buffer=', buffer)
                                ascii = buffer.decode('utf-8')
                                value=ascii[-8:-4]
                                M1=int(str(value),16)
                                print('M1= ',M1)
                                break
                        print('finish reset')
                        # create new record
                        print('reset counter cause value =',d510)
                        id_r=pd.read_sql('select count(*) from leng_log;',engine_ttp)
                        idx=id_r.iloc[0,0]+1
                        mydb=mysql.connector.connect(host="localhost", user='ttpdept', passwd='plcgpsd', database="ttp")
                        myCursor=mydb.cursor()
                        sql_nr='insert into leng_log values ('+str(idx)+','+str(R_p)+',0,now(),date(now()),"");'
                        myCursor=mydb.cursor()
                        myCursor.execute(sql_nr)
                        mydb.commit()
                        myCursor.close()
                        mydb.close()
                        new_record=0
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
        lc=5+int('0x'+hex_a[:2],0)+int('0x'+hex_a[-2:],0)
        crc=lc^0xFFFF
        crc=crc+1
        cmd=(':0103'+hex_a+'0001'+hex(crc)[-2:]).upper()+'\r\n'
        print(cmd.encode('ascii'))
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
        crc=lc^0xFFFF
        crc=crc+1
        cmd=(':0106'+hex_a+hex_v+hex(crc)[-2:]).upper()+'\r\n'
        print(cmd.encode('ascii'))
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
        crc=lc^0xFFFF
        crc=crc+1
        cmd=(':0105'+hex_a+hex_v+hex(crc)[-2:]).upper()+'\r\n'
        print(cmd.encode('ascii'))
        return cmd.encode('ascii')   

    def run(self):
        global ser
        global kn_plc
        global setting
        global thread_plc
        global start_save_dept
        global start_reset_dept
        global b_value #bar leng
        global h_value # height value
        global d_value # deg value
        while True:
            curdate=datetime.datetime.now().strftime('%y/%m/%d')
            curtime=datetime.datetime.now().strftime('%H:%M:%S')
            thread_plc=1
            if setting==1 and start_save_dept==1 and kn_plc==0: #save setting
                # write plc data
                time.sleep(0.02)
                value=100
                try:
                    value=int(b_value)
                except:
                    value=100
                data=self.main_write_D(460,value)
                ser.write(data)
                ascii='0000000'
                d460=0
                while True:
                    if ser.in_waiting > 0:
                        buffer = ser.readline()
                        ascii = buffer.decode('utf-8')
                        value=ascii[-8:-4]
                        d460=int(str(value),16)
                        break
                time.sleep(0.02)
                #set h value
                value=50
                try:
                    value=int(h_value)
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
                        ascii = buffer.decode('utf-8')
                        value=ascii[-8:-4]
                        d410=int(str(value),16)
                        break
                h_value=str(d410)
                value=90
                try:
                    value=int(d_value)
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
                        ascii = buffer.decode('utf-8')
                        value=ascii[-8:-4]
                        d466=int(str(value),16)
                        break
                d_value=str(d466)
                start_save_dept=0
                self.signal.emit("save_value","save_value",curdate,curtime)
            elif setting==1 and start_reset_dept==1 and kn_plc==0: #reset dept
                print('reset_position')
                cmd=self.main_write_M(1,"ON")
                print(cmd)
                ser.write(cmd)
                ascii='0000000'
                M1=0
                while True:
                    if ser.in_waiting > 0:
                        buffer = ser.readline()
                        print('buffer=', buffer)
                        ascii = buffer.decode('utf-8')
                        value=ascii[-8:-4]
                        M1=int(str(value),16)
                        print('M1= ',M1)
                        break
                start_reset_dept=0
                self.signal.emit("reset_value","reset_value",curdate,curtime)
            elif setting==0 and kn_plc==0: # read dept
                d550=0
                d510=0
                try:
                    data=self.cmd_read_D(550)
                    ser.write(data)
                    ascii='0000'
                    d550=0
                    while True:
                        if ser.in_waiting > 0:
                            buffer = ser.readline()
                            ascii = buffer.decode('utf-8')
                            value=ascii[-8:-4]
                            d550=int(str(value),16)
                            print('D550= ',d550)
                            break
                    # time.sleep(0.02)
                    time.sleep(0.02)
                    data=self.cmd_read_D(510)
                    ser.write(data)
                    ascii='0000'
                    d510=0
                    while True:
                        if ser.in_waiting > 0:
                            buffer = ser.readline()
                            ascii = buffer.decode('utf-8')
                            value=ascii[-8:-4]
                            d510=int(str(value),16)
                            break
                    # time.sleep(0.02)
                    time.sleep(0.02)
                    self.signal.emit(str(d550),str(d510),curdate,curtime)
                except:
                    print('a small error')
                    self.signal.emit(str(d550),str(d510),curdate,curtime)
            else:
                print('thread do nothing')
            thread_plc=0
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
        self.update_graph()
        self.load_gps_port()
        self.start_gps()                    
        self.load_gps()

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
            self.ui.lbl_g_stt.setStyleSheet("color: rgb(255, 0, 0);\nbackground-color: rgba(85, 85, 127,80);")
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
                    self.ui.lbl_g_stt.setStyleSheet("color: rgb(0, 255, 0);\nbackground-color: rgba(85, 85, 127,80);")
                    self.ui.lbl_g_stt.setText('GPS Connected')
                    self.ui.bt_reconnect_gps.setEnabled(False)
                    set_gps=0
                    kn_gps=0
                    print('gps connected')
                    self.ui.tabWidget.setCurrentIndex(0)
                else:
                    kn_gps=1
                    set_gps=1
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
                    self.ui.MplWidget.canvas.axes.scatter(x,y, color='blue')
                    self.axins = self.ui.MplWidget.canvas.axes.inset_axes([0.65, 0.65, 0.33, 0.33])
                    self.axins.imshow(self.img,aspect='auto',extent=([691865,704765,1128820,1137940]))
                    self.axins.set_xlim(x-250, x+250)
                    self.axins.set_ylim(y-250, y+250)
                    self.axins.set_xticklabels('')
                    self.axins.set_yticklabels('')
                    self.scat2=self.axins.scatter(x,y,s=15*15,color='blue')
                    self.zoom=self.ui.MplWidget.canvas.axes.indicate_inset_zoom(self.axins)
                    print('draw point gps')
                    self.ui. MplWidget . canvas . draw ()
                    self.ui.lbl_g_stt.setStyleSheet("color: rgb(0, 255, 0);\nbackground-color: rgba(85, 85, 127,80);")
                    self.ui.lbl_g_stt.setText("location updated")
                else:
                    self.ui.lbl_g_stt.setStyleSheet("color: rgb(255, 255, 0);\nbackground-color: rgba(85, 85, 127,80);")
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
                ser_2.timeout = 10
                ser_2.open()
            c=0
            ok=0
            while c<100:
                val = ser_2.readline()                # read complete line from serial output
                val=str(val.decode('utf-8'))
                time.sleep(0.01)
                data=val.split(',')
                if data[0]=='$GNGLL':
                    ok=1
                    break
                c=c+1
            if ok==1:
                ser_gps=ser_2
                QMessageBox.about(self, 'Thông báo','GPS  connected!')
                self.ui.lbl_g_stt.setStyleSheet("color: rgb(0, 255, 0);\nbackground-color: rgba(85, 85, 127,80);")
                self.ui.lbl_g_stt.setText('GPS Connected')
                self.ui.bt_reconnect_gps.setEnabled(False)
                set_gps=0
                kn_gps=0
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
                self.ui.bt_reconnect_gps.setEnabled(True)
                self.ui.lbl_g_stt.setStyleSheet("color: rgb(255, 0, 0);\nbackground-color: rgba(85, 85, 127,80);")
                self.ui.lbl_g_stt.setText('GPS connection loss!!!')
            
        except:
            kn_gps=1
            set_gps=1
            QMessageBox.about(self, 'Thông báo','không kết nối đến được gps!\nVui lòng kiểm tra lại.')
            self.ui.bt_reconnect_gps.setEnabled(True)
            self.ui.lbl_g_stt.setStyleSheet("color: rgb(255, 0, 0);\nbackground-color: rgba(85, 85, 127,80);")
            self.ui.lbl_g_stt.setText('GPS connection loss!!!')

    def load_gps(self):
        global set_gps
        global thread_gps_n
        # if set_gps==0:
        print('read gps location')
        thread_gps_n=thread_gps_n+1
        self.gps_location=read_gps(thread_gps_n)        
        self.gps_location.signal.connect(self.gps_location_signal)
        self.gps_location.start()
        if set_gps!=0:
            print('gps not yet connected')
            self.ui.lbl_g_stt.setStyleSheet("color: rgb(255, 0, 0);\nbackground-color: rgba(85, 85, 127,80);")
            self.ui.lbl_g_stt.setText('GPS Connection lost!!!')

    def gps_location_signal(self,lo,la,curdate,curtime):
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
        global deg_dept
        angle=int(deg_dept)
        pic='sim/0d.jpg'
        if angle%2==1:
            angle=angle+1
        if angle>60:
            pic='sim/60d.jpg'
        else:
            pic='sim/'+str(angle)+'d.jpg'
        self.ui.pic_box_GPS.setPixmap(QtGui.QPixmap(pic))
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
                print('reconect gps')
        except:
                print('gps wrong')
        global p
        global x
        global y
        print(la,lo)
        if lo!='' and la!='':
            try:
            # if 1>0:
                x,y=p(float(la),float(lo))
                print(x,y)
                x=float(x)
                y=float(y)   
            except:
                print('latlon error,convert xy error') 
        
        if cgps>30:
            try:
                if lo!='' and la!='':
                    self.draw_point(la,lo)
            except:
                print('latlon error,cannot refresh map')
            cgps=0
        else:
            cgps=cgps+1
        self.ui.lbl_g_longitude.setText(la)
        self.ui.lbl_g_latitude.setText(lo)
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
        print('gps thread ',self.thread_no)
        while self.thread_no==thread_gps_n:
            curdate=datetime.datetime.now().strftime('%y/%m/%d')
            curtime=datetime.datetime.now().strftime('%H:%M:%S')
            lo=''
            la=''
            if set_gps==0 and kn_gps!=1:
                print('gps thread ',self.thread_no)
                while True:
                    val = ser_gps.readline()                # read complete line from serial output
                    val=str(val.decode('utf-8'))
                    time.sleep(0.02)
                    data=val.split(',')
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