"""
This file shows different Containers, which are just fancy classes which mimick a dictionnary, as well as a custom list which can emit QtSignals.
The only goal of the Containers classes (Thermometer, PSensor, Shaft and Point) is to have a list of attributes which can be easily read. They have no methods. 
"""
from PyQt5.QtCore import QObject, pyqtSignal

class MoloQtList(QObject):
    """
    Custom list which can emit two signals, one when an item is appended and one when an item is removed.
    In order for this to work, theses items MUST have a field or attribute called "name" which identifies them in a unique way: this is useful to identify elements when trying to delete one.
    """
    appendSignal = pyqtSignal(object)
    removeSignal = pyqtSignal(object)
    clearSignal = pyqtSignal()

    def __init__(self):
        super(MoloQtList, self).__init__()
        self.elements = []
    
    def append(self,item):
        """
        This is the method which should be called when trying to add an element to the MoloQtList.
        The parameter item must have a field or attribute called "name" which should be a string.
        """
        self.elements.append(item)
        self.appendSignal.emit(item)
    
    def remove(self,itemName):
        """
        This is the method which should be called when trying to remove an element from the MoloQtList.
        The parameter itemName is a string corresponding to the unique identifier of an element in the MoloQtList.
        """
        index = None
        for i,v in enumerate(self.elements):
            if v.name == itemName:
                index = i
                break
        item = self.elements.pop(index) #Remove the item with the given name itemName
        self.removeSignal.emit(item)  #Emit the signal saying that item was removed from the list
    
    def clear(self):
        """
        Clear the list and everything in it. Used only when the MoloQtList should be destroyed (ie when closing the lab or the study)
        """
        self.elements = []
        self.clearSignal.emit()

class Thermometer:
    def __init__(self, name, manuName, manuRef, error):
        self.name = name
        self.manuName = manuName
        self.manuRef = manuRef
        self.error = error

class PSensor:
    def __init__(self, name, datalogger, calibrationDate, intercept, dudh, dudt, error):
        self.name = name
        self.datalogger = datalogger
        self.calibrationDate = calibrationDate
        self.intercept = intercept
        self.dudh = dudh
        self.dudt = dudt
        self.error = error

class Shaft:
    def __init__(self, name, datalogger, depths, thermoType):
        self.name = name
        self.datalogger = datalogger
        self.thermoType = thermoType
        self.depths = depths

class Point:
    def __init__(self, name, psensor, shaft, rivBed, offset):
        self.name = name
        self.psensor = psensor
        self.shaft = shaft
        self.rivBed = rivBed
        self.offset = offset
