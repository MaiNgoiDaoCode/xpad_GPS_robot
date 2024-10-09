from  PyQt5.QtWidgets  import *

from  matplotlib.backends.backend_qt5agg  import  FigureCanvas

from  matplotlib.figure  import  Figure

    
class  MplWidget (QWidget):
    
    def  __init__ ( self ,  parent  =  None ):

        QWidget.__init__ ( self ,  parent )
        
        self.fig = Figure()
        self.fig.set_tight_layout(True)
        self . canvas  =  FigureCanvas ( self.fig)
        
        vertical_layout  =  QVBoxLayout () 
        vertical_layout . addWidget ( self . canvas )
        
        self . canvas . axes  =  self . canvas . figure . add_subplot ( 111 ) 
        self . setLayout ( vertical_layout )