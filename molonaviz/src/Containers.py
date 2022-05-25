"""
This file shows different Containers, which are just fancy classes which mimick a dictionnary. The only goal of theses classes is to have a list of attributes which can be easily read. They have no methods. 
"""

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
    def __init__(self, name, datalogger, thermoType, depths):
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