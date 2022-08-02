
from PyQt5 import QtGui

from src.MoloView import MoloView
from src.MoloModel import MoloModel #Used only for type hints


class ThermometerTreeView(QtGui.QStandardItemModel, MoloView):
    def __init__(self, molomodel: MoloModel | None):
        QtGui.QStandardItemModel.__init__(self)
        MoloView.__init__(self, molomodel)
    
    def on_update(self):
        self.clear() #QStandardItemModel method to visually remove everything from the TreeView
        thermos = self.model.get_all_thermometers()
        for thermometer in thermos:
            item = QtGui.QStandardItem(thermometer.name)
            self.appendRow(item)
            item.appendRow(QtGui.QStandardItem(f"Manufacturer name : {thermometer.manuName}"))
            item.appendRow(QtGui.QStandardItem(f"Manufacturer reference : {thermometer.manuRef}"))
            item.appendRow(QtGui.QStandardItem(f"Error (°C) : {thermometer.error}"))        

# class MoloTreeViewModel(QtGui.QStandardItemModel):
#     """
#     Abstract class for the model used for the tree views in the main window.
#     This tree view displays Containers objects. Each item it shows MUST have a field or attribute called "name" which identifies it in a unique way.
#     """
#     def __init__(self):
#         super().__init__()
#         self.elements = []
    
#     def add_data(self, input_data : Thermometer | PSensor | Shaft | Point):
#         """
#         Add a new element to the model.
#         """
#         self.elements.append(input_data)
#         self.display_element(input_data)
    
#     def display_element(self,input_data : Thermometer | PSensor | Shaft | Point):
#         """
#         Display the new element input_data in a pretty way.
#         """
#         pass
    
#     def remove_data(self,input_data : Thermometer | PSensor | Shaft | Point):
#         """
#         Remove the given item.
#         """
#         #Remove the item from self.elements
#         index = None
#         for i,v in enumerate(self.elements):
#             if v.name == input_data.name:
#                 index = i
#                 break
#         self.elements.pop(index)
#         #Stop displaying it.
#         index = None
#         for i in range(self.rowCount()):
#             if self.item(i).data() ==input_data.name:
#                 index = i
#                 break
#         self.removeRow(i)

#     def clear(self):
#         """
#         Clear everything in the view. This is an overloaded method.
#         """
#         self.elements = []
#         super().clear()
        

# class ThermometerTreeViewModel(MoloTreeViewModel):
#     """
#     Concrete class for the model used for to display the thermometers in a tree view in the main window.
#     """
#     def __init__(self):
#         super().__init__()
    
#     def display_element(self, thermometer : Thermometer):
#         item = QtGui.QStandardItem(thermometer.name)
#         self.appendRow(item)
#         item.appendRow(QtGui.QStandardItem(f"Manufacturer name : {thermometer.manuName}"))
#         item.appendRow(QtGui.QStandardItem(f"Manufacturer reference : {thermometer.manuRef}"))
#         item.appendRow(QtGui.QStandardItem(f"Error (°C) : {thermometer.error}"))

# class PSensorTreeViewModel(MoloTreeViewModel):
#     """
#     Concrete class for the model used for to display the pressure sensors in a tree view in the main window.
#     """
#     def __init__(self):
#         super().__init__()
    
#     def display_element(self, psensor : PSensor):
#         item = QtGui.QStandardItem(psensor.name)
#         self.appendRow(item)
#         item.appendRow(QtGui.QStandardItem(f"Datalogger : {psensor.datalogger}"))
#         item.appendRow(QtGui.QStandardItem(f"Calibration date : {psensor.calibrationDate}"))
#         item.appendRow(QtGui.QStandardItem(f"Intercept : {psensor.intercept}"))
#         item.appendRow(QtGui.QStandardItem(f"Du/Dh : {psensor.dudh}"))
#         item.appendRow(QtGui.QStandardItem(f"Du/Dt : {psensor.dudt}"))
#         item.appendRow(QtGui.QStandardItem(f"Error : {psensor.error}"))

# class ShaftTreeViewModel(MoloTreeViewModel):
#     """
#     Concrete class for the model used for to display the shafts in a tree view in the main window.
#     """
#     def __init__(self):
#         super().__init__()
    
#     def display_element(self, shaft : Shaft):
#         item = QtGui.QStandardItem(shaft.name)
#         self.appendRow(item)
#         item.appendRow(QtGui.QStandardItem(f"Datalogger : {shaft.datalogger}"))
#         item.appendRow(QtGui.QStandardItem(f"Thermometers type : {shaft.thermoType}"))
#         item.appendRow(QtGui.QStandardItem(f"Thermometers depths (m) : {shaft.depths}"))

# class PointTreeViewModel(MoloTreeViewModel):
#     """
#     Concrete class for the model used for to display the points associated to a study in a tree view in the main window.
#     """
#     def __init__(self):
#         super().__init__()
    
#     def display_element(self, point : Point):
#         item = QtGui.QStandardItem(point.name)
#         item.setData(point.name, QtCore.Qt.UserRole) #Flag the name of the point as an information (in fact the only information) which the user will be able to retrieve. 
#         self.appendRow(item)
#         item.appendRow(QtGui.QStandardItem(f"Pressure sensor : {point.psensor}"))
#         item.appendRow(QtGui.QStandardItem(f"Shaft : {point.shaft}"))
#         item.appendRow(QtGui.QStandardItem(f"River bed = {point.rivBed}"))
#         item.appendRow(QtGui.QStandardItem(f"Offset = {point.offset}"))

