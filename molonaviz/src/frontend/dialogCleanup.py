import os
import pandas as pd

from PyQt5 import QtWidgets, uic
from scipy import stats

# from src.backend.SPointCoordinator import SPointCoordinator
# from src.Containers import SamplingPoint
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator
import matplotlib.dates as mdates
import numpy as np

from src.utils.utils import date_to_mdates
from src.backend.SPointCoordinator import SPointCoordinator
from src.Containers import SamplingPoint

From_DialogCleanup= uic.loadUiType(os.path.join(os.path.dirname(__file__), "ui", "dialogCleanup.ui"))[0]

class CompareCanvas(FigureCanvasQTAgg):
    """
    A small class to represent a canvas on which raw and cleaned measures will be plotted.
    This class holds two panda dataframes (reference_data = raw data, modified_data = cleaned data). These dataframes must have dates in datetime (or Timestamp) format. However, internally, these dataframes hold matplotlib dates.
    """
    def __init__(self):
        self.fig = Figure()
        self.axes = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.reference_data = None
        self.modified_data = None
    
    def set_reference_data(self, data):
        """
        Set the given dataframe as the reference data.
        """
        self.reference_data = data
        # self.reference_data["Date"] = date_to_mdates(self.reference_data["Date"])
    
    def set_modified_data(self, data):
        self.modified_data = data
        # self.modified_data["Date"] = date_to_mdates(self.modified_data["Date"])

    def plot_data(self, field):
        """
        Plot given field (Pressure, Temp1, Temp2, Temp3, Temp4 or TempBed).
        """
        self.axes.clear()
        #Dark pandas magic!
        if self.reference_data is not None:
            if self.modified_data is None:
                self.reference_data.plot.scatter(x ="Date", y = field, c = 'b', s = 1, ax = self.axes)
            else:
                df_all = self.reference_data.merge(self.modified_data.drop_duplicates(), on=["Date", "Temp1","Temp2", "Temp3", "Temp4", "TempBed", "Pressure"], how = 'left', indicator = True)
                cleaned_only = df_all[df_all["_merge"] == "left_only"]  
                untouched =  df_all[df_all["_merge"] == "both"] 
                cleaned_only.plot.scatter(x ="Date", y = field, c = '#FF6D6D', s = 1, ax = self.axes)
                untouched.plot.scatter(x ="Date", y = field, c = 'b', s = 1, ax = self.axes)
            
            self.format_xaxis()
            self.fig.canvas.draw()
    
    def format_xaxis(self):
        formatter = mdates.DateFormatter("%y/%m/%d %H:%M")
        self.axes.xaxis.set_major_formatter(formatter)
        self.axes.xaxis.set_major_locator(MaxNLocator(4))

class DialogCleanup(QtWidgets.QDialog, From_DialogCleanup):
    """
    A dialog to either automatically clean the raw measures, of to import cleaned measures.
    """
    def __init__(self, coordinator : SPointCoordinator, spoint : SamplingPoint):# coordinator : SPointCoordinator, point : SamplingPoint):
        super(DialogCleanup, self).__init__()
        QtWidgets.QDialog.__init__(self)

        self.setupUi(self)
        self.coordinator = coordinator
        self.spoint = spoint

        self.radioButton.setChecked(True)#Should already be done in UI
        self.radioButtonFC.clicked.connect(self.displayinF)
        self.radioButtonCK.clicked.connect(self.displayinK)
        self.radioButton.clicked.connect(self.displayinC)
        self.radioButtonNone.setChecked(True) #This should already be done in the UI
        self.radioButtonNone.clicked.connect(self.setNoneProcessing)
        self.radioButtonIQR.clicked.connect(self.setIQRProcessing)
        self.radioButtonZScore.clicked.connect(self.setZScoreProcessing)

        self.uiToDF = {"Differential pressure" : "Pressure",
                        "Temperature at depth 1": "Temp1",
                        "Temperature at depth 2": "Temp2",
                        "Temperature at depth 3": "Temp3",
                        "Temperature at depth 4": "Temp4",
                        "Stream Temperature" : "TempBed"
                        } #Conversion between what is displayed on the ui and the corresponding DF column.

        #Retrieve the dataframes
        self.data = None
        self.intercept = 0
        self.dUdH = 1
        self.dUdT = 1
        self.buildDF()
        self.convertVoltagePressure()
        self.cleaned_data = self.data.copy(deep = True) #By default, nothing has changed excet Voltage -> Pressure conversion
        self.currentTempUnit = "C" #°C by default

        self.mplCanvas = CompareCanvas()
        self.mplCanvas.set_reference_data(self.data)
        self.toolBar = NavigationToolbar2QT(self.mplCanvas,self)
        self.widgetToolBar.addWidget(self.toolBar)
        self.widgetRawData.addWidget(self.mplCanvas)

        self.comboBoxRawVar.addItems(["Differential pressure", "Temperature at depth 1", "Temperature at depth 2", "Temperature at depth 3", "Temperature at depth 4", "Stream Temperature"])
        self.comboBoxRawVar.currentIndexChanged.connect(self.plotVariable)

        self.plotVariable()
    
    def buildDF(self):
        """
        Fetch raw measures from the coordinator, and arrange them all in one big panda dataframe stored in self.data.
        """
        backend_data = self.coordinator.allRawMeasures()
        self.data = pd.DataFrame(backend_data, columns = ["Date","Temp1", "Temp2", "Temp3", "Temp4", "TempBed", "Voltage"])
        

    def convertVoltagePressure(self):
        """
        Convert the Voltage column into a (differential) Pressure field, taking into accound the calibration information.
        """
        self.data["Pressure"] = (self.data["Voltage"] - self.data["TempBed"]*self.dUdT - self.intercept)/self.dUdH
        self.data.drop(labels="Voltage", axis = 1, inplace = True)
    
    def plotVariable(self):
        #TODO: use a dictionnary for this!
        var = self.uiToDF[self.comboBoxRawVar.currentText()]
        self.mplCanvas.plot_data(var)
    
    def setNoneProcessing(self):
        self.cleaned_data = self.data
        self.mplCanvas.set_modified_data(self.cleaned_data)
        self.plotVariable()
    
    def setIQRProcessing(self):
        var = self.uiToDF[self.comboBoxRawVar.currentText()]
        q1 = self.data[var].quantile(0.25)
        q3 = self.data[var].quantile(0.75)
        iqr = q3-q1 #Interquartile range
        fence_low  = q1-1.5*iqr
        fence_high = q3+1.5*iqr

        self.cleaned_data = self.data.copy(deep = True)
        self.cleaned_data.drop(self.cleaned_data.loc[self.cleaned_data[var] < fence_low].index, inplace = True)
        self.cleaned_data.drop(self.cleaned_data.loc[self.cleaned_data[var] > fence_high].index, inplace = True)

        self.mplCanvas.set_modified_data(self.cleaned_data)
        self.plotVariable()
    
    def setZScoreProcessing(self):
        var = self.uiToDF[self.comboBoxRawVar.currentText()]
        self.cleaned_data = self.data.copy(deep = True)
        var_column = self.data[var].copy(deep = True).dropna()
        self.cleaned_data[var]= var_column.loc[(np.abs(stats.zscore(var_column)) < 3)]
        self.cleaned_data.dropna(inplace = True)
        self.mplCanvas.set_modified_data(self.cleaned_data)
        self.plotVariable()
    
    def FtoC(self, x):
        return (x-32)/1.8
    
    def CtoF(self, x):
        return x*1.8 + 32
    
    def CtoK(self,x):
        return x+273.15

    def KtoC(self,x):
        return x-273.15
    
    def FtoK(self,x):
        return self.CtoK(self.FtoC(x))
    
    def KtoF(self,x):
        return self.CtoF(self.KtoC(x))

    def displayinC(self):
        if self.currentTempUnit !="C":
            if self.currentTempUnit =="F":
                convertFun = self.FtoC
            else:
                convertFun = self.KtoC

            self.data[["Temp1","Temp2","Temp3","Temp4", "TempBed"]] = self.data[["Temp1","Temp2","Temp3","Temp4", "TempBed"]].apply(convertFun)
            if self.cleaned_data is not None:
                self.cleaned_data[["Temp1","Temp2","Temp3","Temp4", "TempBed"]] = self.cleaned_data[["Temp1","Temp2","Temp3","Temp4", "TempBed"]].apply(convertFun)
            
            self.currentTempUnit = "C"
            self.mplCanvas.set_reference_data(self.data)
            self.mplCanvas.set_modified_data(self.cleaned_data)
            self.plotVariable()

    def displayinF(self):
        if self.currentTempUnit !="F":
            if self.currentTempUnit =="C":
                convertFun = self.CtoF
            else:
                convertFun = self.KtoF

            self.data[["Temp1","Temp2","Temp3","Temp4", "TempBed"]] = self.data[["Temp1","Temp2","Temp3","Temp4", "TempBed"]].apply(convertFun)
            if self.cleaned_data is not None:
                self.cleaned_data[["Temp1","Temp2","Temp3","Temp4", "TempBed"]] = self.cleaned_data[["Temp1","Temp2","Temp3","Temp4", "TempBed"]].apply(convertFun)
            
            self.currentTempUnit = "F"
            self.mplCanvas.set_reference_data(self.data)
            self.mplCanvas.set_modified_data(self.cleaned_data)
            self.plotVariable()

    def displayinK(self):
        if self.currentTempUnit !="K":
            if self.currentTempUnit =="C":
                convertFun = self.CtoK
            else:
                convertFun = self.FtoK

            self.data[["Temp1","Temp2","Temp3","Temp4", "TempBed"]] = self.data[["Temp1","Temp2","Temp3","Temp4", "TempBed"]].apply(convertFun)
            if self.cleaned_data is not None:
                self.cleaned_data[["Temp1","Temp2","Temp3","Temp4", "TempBed"]] = self.cleaned_data[["Temp1","Temp2","Temp3","Temp4", "TempBed"]].apply(convertFun)
            
            self.currentTempUnit = "K"
            self.mplCanvas.set_reference_data(self.data)
            self.mplCanvas.set_modified_data(self.cleaned_data)
            self.plotVariable()
    
    def getCleanedMeasures(self):
        # dlg.df_cleaned["date"].replace('', nan, inplace = True)
        # dlg.df_cleaned.dropna(subset = ["date"], inplace = True)
        # convertDates(dlg.df_cleaned) #Convert dates to datetime (or here Timestamp) objects
        return self.cleaned_data