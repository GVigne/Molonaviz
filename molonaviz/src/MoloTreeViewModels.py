from PyQt5 import QtGui

class MoloTreeViewModel(QtGui.QStandardItemModel):
    """
    Abstract class for the model used for the tree views in the main window.
    """
    def __init__(self):
        super().__init__()
        self.elements = []
    
    def add_data(self, input_data):
        """
        Add a new element to the model.
        """
        self.elements.append(input_data)
        self.display_element(input_data)
    
    def display_element(self,input_data):
        """
        Display the new element input_data in a pretty way.
        """
        pass

class ThermometerTreeViewModel(MoloTreeViewModel):
    """
    Concrete class for the model used for to display the thermometers in a tree view in the main window.
    """
    def __init__(self):
        super().__init__()
    
    def display_element(self, thermometer):
        item = QtGui.QStandardItem(thermometer.name)
        self.appendRow(item)
        item.appendRow(QtGui.QStandardItem(f"Manufacturer name : {thermometer.manuName}"))
        item.appendRow(QtGui.QStandardItem(f"Manufacturer reference : {thermometer.manuRef}"))
        item.appendRow(QtGui.QStandardItem(f"Error (°C) : {thermometer.error}"))

class PSensorTreeViewModel(MoloTreeViewModel):
    """
    Concrete class for the model used for to display the pressure sensors in a tree view in the main window.
    """
    def __init__(self):
        super().__init__()
    
    def display_element(self,psensor):
        item = QtGui.QStandardItem(psensor.name)
        self.appendRow(item)
        item.appendRow(QtGui.QStandardItem(f"Datalogger : {psensor.datalogger}"))
        item.appendRow(QtGui.QStandardItem(f"Calibration date : {psensor.calibrationDate}"))
        item.appendRow(QtGui.QStandardItem(f"Intercept : {psensor.intercept:.2f}"))
        item.appendRow(QtGui.QStandardItem(f"Du/Dh : {psensor.dudh:.2f}"))
        item.appendRow(QtGui.QStandardItem(f"Du/Dt : {psensor.dudt:.2f}"))
        item.appendRow(QtGui.QStandardItem(f"Error : {psensor.error:.2f}"))

class ShaftTreeViewModel(MoloTreeViewModel):
    """
    Concrete class for the model used for to display the shafts in a tree view in the main window.
    """
    def __init__(self):
        super().__init__()
    
    def display_element(self, shaft):
        item = QtGui.QStandardItem(shaft.name)
        self.appendRow(item)
        item.appendRow(QtGui.QStandardItem(f"Datalogger : {shaft.datalogger}"))
        item.appendRow(QtGui.QStandardItem(f"Thermometers type : {shaft.thermoType}"))
        item.appendRow(QtGui.QStandardItem(f"Thermometers depths (m) : {shaft.depths}"))

class PointTreeViewModel(MoloTreeViewModel):
    """
    Concrete class for the model used for to display the points associated to a study in a tree view in the main window.
    """
    def __init__(self):
        super().__init__()
    
    def display_element(self, point):
        item = QtGui.QStandardItem(point.name)
        self.appendRow(item)
        item.appendRow(QtGui.QStandardItem(f"Pressure sensor : {point.psensor}"))
        item.appendRow(QtGui.QStandardItem(f"Shaft : {point.shaft}"))
        item.appendRow(QtGui.QStandardItem(f"River bed = {point.rivBed:.2f}"))
        item.appendRow(QtGui.QStandardItem(f"Offset = {point.offset:.2f}"))

