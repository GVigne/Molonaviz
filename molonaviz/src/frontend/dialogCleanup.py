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

from src.utils.utils import convertDates, dateToMdates, displayCriticalMessage
from src.backend.SPointCoordinator import SPointCoordinator
from src.Containers import SamplingPoint
from src.InnerMessages import CleanupStatus, ComputationsState

From_DialogCleanup= uic.loadUiType(os.path.join(os.path.dirname(__file__), "ui", "dialogCleanup.ui"))[0]

class InvalidCSVStructure(Exception):
    pass


class CompareCanvas(FigureCanvasQTAgg):
    """
    A small class to represent a canvas on which raw and cleaned measures will be plotted.
    This class holds two panda dataframes (reference_data = raw data, modified_data = cleaned data). These dataframes must have dates in datetime (or Timestamp) format. However, internally, these dataframes hold matplotlib dates.
    """
    def __init__(self):
        self.fig = Figure()
        self.axes = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.reference_data = pd.DataFrame(columns =["Date", "Temp1","Temp2", "Temp3", "Temp4", "TempBed", "Pressure"])
        self.modified_data = pd.DataFrame(columns =["Date", "Temp1","Temp2", "Temp3", "Temp4", "TempBed", "Pressure"])
    
    def set_reference_data(self, data):
        """
        Set the given dataframe as the reference data.
        """
        self.reference_data = data
        # self.reference_data["Date"] = dateToMdates(self.reference_data["Date"])
    
    def set_modified_data(self, data):
        self.modified_data = data
        # self.modified_data["Date"] = dateToMdates(self.modified_data["Date"])

    def plot_data(self, field):
        """
        Plot given field (Pressure, Temp1, Temp2, Temp3, Temp4 or TempBed).
        """
        self.axes.clear()
        #Dark pandas magic!
        if not self.reference_data.empty:
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

        self.uiToDF = {"Differential pressure" : "Pressure",
                    "Temperature at depth 1": "Temp1",
                    "Temperature at depth 2": "Temp2",
                    "Temperature at depth 3": "Temp3",
                    "Temperature at depth 4": "Temp4",
                    "Stream Temperature" : "TempBed"
                    } # Conversion between what is displayed on the ui and the corresponding DF column.
        self.comboBoxRawVar.addItems(list(self.uiToDF.keys()))

        self.radioButtonNone.setChecked(True) # This should already be done in the UI      
        self.radioButtonC.setChecked(True) # This should already be done in the UI 
        
        self.radioButtonNone.clicked.connect(self.setNoneComputation) # This should already be done in the UI        
        self.radioButtonIQR.clicked.connect(self.setIQRComputation)
        self.radioButtonZScore.clicked.connect(self.setZScoreComputation)
        self.radioButtonF.clicked.connect(self.refreshPlot)
        self.radioButtonK.clicked.connect(self.refreshPlot)
        self.radioButtonC.clicked.connect(self.refreshPlot)
        self.comboBoxRawVar.currentIndexChanged.connect(self.showNewVar)
        self.pushButtonResetAll.clicked.connect(self.reset)
        self.tabWidget.currentChanged.connect(self.switchTab)
        self.pushButtonBrowse.clicked.connect(self.browse)

        self.spinBoxStartDay.valueChanged.connect(self.refreshPlot)
        self.spinBoxStartMonth.valueChanged.connect(self.refreshPlot)
        self.spinBoxStartYear.valueChanged.connect(self.refreshPlot)
        self.spinBoxEndDay.valueChanged.connect(self.refreshPlot)
        self.spinBoxEndMonth.valueChanged.connect(self.refreshPlot)
        self.spinBoxEndYear.valueChanged.connect(self.refreshPlot)

        self.varStatus = {"Pressure" : CleanupStatus.NONE,
                          "Temp1" : CleanupStatus.NONE,
                          "Temp2" : CleanupStatus.NONE,
                          "Temp3" : CleanupStatus.NONE,
                          "Temp4" : CleanupStatus.NONE,
                          "TempBed" : CleanupStatus.NONE
                        } # The cleanup status for every variable: initially, we don't do anything.
        self.data = None
        self.intercept, self.dUdH, self.dUdT = self.coordinator.calibrationInfos()
        self.buildDF()
        self.convertVoltagePressure()
        self.setupStartEndDates()

        self.mplCanvas = CompareCanvas()
        self.mplCanvas.set_reference_data(self.data)
        self.toolBar = NavigationToolbar2QT(self.mplCanvas,self)
        self.widgetToolBar.addWidget(self.toolBar)
        self.widgetRawData.addWidget(self.mplCanvas)
    
        self.refreshPlot()

    def buildDF(self):
        """
        Fetch raw measures from the coordinator, and arrange them all in one big panda dataframe stored in self.data.
        """
        backend_data = self.coordinator.allRawMeasures()
        self.data = pd.DataFrame(backend_data, columns = ["Date","Temp1", "Temp2", "Temp3", "Temp4", "TempBed", "Voltage"])
    
    def convertVoltagePressure(self):
        """
        Convert the Voltage column into a (differential) Pressure field, taking into account the calibration information.
        This should only be called once, as we'd rather have the user speak in terms of differential pressure than in Voltage.
        """
        self.data["Pressure"] = (self.data["Voltage"] - self.data["TempBed"]*self.dUdT - self.intercept)/self.dUdH
        self.data.drop(labels="Voltage", axis = 1, inplace = True)
    
    def setupStartEndDates(self):
        """
        Fill the combo boxes with the first date and the last date in the dataframe.
        """
        # Block the signals so refreshPlot isn't called 6 times.
        for spin in [self.spinBoxStartDay, self.spinBoxStartMonth, self.spinBoxStartYear, self.spinBoxEndDay, self.spinBoxEndMonth, self.spinBoxEndYear]:
            spin.blockSignals(True)

        startDate = self.data["Date"].iloc[0]
        self.spinBoxStartDay.setValue(startDate.day)
        self.spinBoxStartMonth.setValue(startDate.month)
        self.spinBoxStartYear.setValue(startDate.year)
        endDate = self.data["Date"].iloc[-1]
        self.spinBoxEndDay.setValue(endDate.day)
        self.spinBoxEndMonth.setValue(endDate.month)
        self.spinBoxEndYear.setValue(endDate.year)

        # Re-enable the signals
        for spin in [self.spinBoxStartDay, self.spinBoxStartMonth, self.spinBoxStartYear, self.spinBoxEndDay, self.spinBoxEndMonth, self.spinBoxEndYear]:
            spin.blockSignals(False)

    def setNoneComputation(self):
        """
        Set None cleanup rule for the current variable.
        """
        var = self.uiToDF[self.comboBoxRawVar.currentText()]
        self.varStatus[var] = CleanupStatus.NONE
        self.refreshPlot()
    
    def setIQRComputation(self):
        """
        Set IQR cleanup rule for the current variable.
        """
        var = self.uiToDF[self.comboBoxRawVar.currentText()]
        self.varStatus[var] = CleanupStatus.IQR
        self.refreshPlot()
    
    def setZScoreComputation(self):
        """
        Set Z-Score cleanup rule for the current variable.
        """
        var = self.uiToDF[self.comboBoxRawVar.currentText()]
        self.varStatus[var] = CleanupStatus.ZSCORE
        self.refreshPlot()
    
    def showNewVar(self):
        """
        Refresh the plots and update the radio buttons for the current variable.
        """
        var = self.uiToDF[self.comboBoxRawVar.currentText()]
        if self.varStatus[var] == CleanupStatus.NONE:
            self.radioButtonNone.setChecked(True)
        elif self.varStatus[var] == CleanupStatus.IQR:
            self.radioButtonIQR.setChecked(True)
        elif self.varStatus[var] == CleanupStatus.ZSCORE:
            self.radioButtonZScore.setChecked(True)

        self.refreshPlot()

    def refreshPlot(self):
        """
        Refresh the plot according to the variable the user is looking at.
        Currently, this implies recomputing the for every variable the decomposition (IQR, Zscore or None). If this is problem, this should be changed: however, we are only looking at ~10 variables on a dataframe of ~5000 entries, so it really shouldn't be a limitation. 
        """
        cleanedData = self.data.copy(deep = True)
        self.applyDateBoundariesChanges(cleanedData)
        self.applyCleanupChanges(cleanedData) # Modifies in place cleanedData
        reference_data, cleanedData = self.applyTemperatureChanges(cleanedData)

        self.mplCanvas.set_reference_data(reference_data)
        self.mplCanvas.set_modified_data(cleanedData)
        displayVar = self.uiToDF[self.comboBoxRawVar.currentText()]
        self.mplCanvas.plot_data(displayVar)
    
    def applyDateBoundariesChanges(self, cleanedData : pd.DataFrame):
        """
        Restrict IN PLACE the given dataframe to the boundaries given by the spinboxes.
        In any of the following cases, the initial dataframe is not modified:
        - the start date is after the last date in the dataframe
        - the end date is before the first date in the dataframe
        - the end date is before the start date
        """
        pd_startDate = pd.Timestamp(day = self.spinBoxStartDay.value(), 
                                    month = self.spinBoxStartMonth.value(), 
                                    year = self.spinBoxStartYear.value(),
                                    hour = 0,
                                    minute = 0,
                                    second = 0)
        pd_endDate = pd.Timestamp(day = self.spinBoxEndDay.value(),
                                month = self.spinBoxEndMonth.value(),
                                year = self.spinBoxEndYear.value(),
                                hour = 23,
                                minute = 59,
                                second = 59)
        if pd_startDate > cleanedData["Date"].iloc[-1]:
            return cleanedData
        elif pd_endDate < cleanedData["Date"].iloc[0]:
            return cleanedData
        elif pd_startDate > pd_endDate:
            return cleanedData
        else:
            cleanedData.drop(cleanedData.loc[cleanedData["Date"] > pd_endDate].index, inplace = True)
            cleanedData.drop(cleanedData.loc[cleanedData["Date"] < pd_startDate].index, inplace = True)
            cleanedData.dropna(inplace=True)
            return cleanedData

    def applyCleanupChanges(self, cleanedData : pd.DataFrame):
        """
        Apply IN PLACE the cleanup change requested for every variable on the given dataframe.
        """
        for i, (varName, varStatus) in enumerate(self.varStatus.items()):
            if varStatus == CleanupStatus.NONE:
                # Nothing to be done, move on!
                pass
            elif varStatus == CleanupStatus.IQR:
                self.applyIQR(cleanedData, varName)
            elif varStatus == CleanupStatus.ZSCORE:
                self.applyZScore(cleanedData, varName)
        cleanedData.dropna(inplace = True) # For sanity purposes
    
    def applyIQR(self, cleanedData : pd.DataFrame, varName : str):
        """
        Modifies IN PLACE the given dataframe by applying IQR treatment on the column with name varName.
        """
        q1 = cleanedData[varName].quantile(0.25)
        q3 = cleanedData[varName].quantile(0.75)
        iqr = q3-q1 #Interquartile range
        fence_low  = q1-1.5*iqr
        fence_high = q3+1.5*iqr

        cleanedData.drop(cleanedData.loc[cleanedData[varName] < fence_low].index, inplace = True)
        cleanedData.drop(cleanedData.loc[cleanedData[varName] > fence_high].index, inplace = True)

    def applyZScore(self, cleanedData : pd.DataFrame, varName : str):
        """
        Modifies IN PLACE the given dataframe by applying Z-Score treatment on the column with name varName.
        """
        var_column = self.data[varName].copy(deep = True).dropna()
        cleanedData[varName]= var_column.loc[(np.abs(stats.zscore(var_column)) < 3)] # Pandas dark magic!
        cleanedData.dropna(inplace = True)
    
    def reset(self):
        """
        Discard all cleanup changes made.
        """
        self.varStatus = {"Pressure" : CleanupStatus.NONE,
                          "Temp1" : CleanupStatus.NONE,
                          "Temp2" : CleanupStatus.NONE,
                          "Temp3" : CleanupStatus.NONE,
                          "Temp4" : CleanupStatus.NONE,
                          "TempBed" : CleanupStatus.NONE
                        } # No cleanup done by default.
        self.radioButtonNone.setChecked(True)
        self.mplCanvas.set_modified_data(None)
        self.setupStartEndDates()

        self.refreshPlot()
    
    def CtoF(self, x):
        return x*1.8 + 32
    
    def CtoK(self,x):
        return x+273.15

    def applyTemperatureChanges(self, cleanedData : pd.DataFrame):
        """
        Return two dataframes:
            - the first is a copy of self.data, with a temperature conversion. self.data must not be modified.
            - the second is the given cleanedData dataframe onto which a temperature conversion has been done. cleanedData can be modified
        This function builds on the fact that self.data and cleanedData have values in °C.
        """
        if self.radioButtonC.isChecked():
            return self.data, cleanedData # Nothing to change
        else:
            if self.radioButtonF.isChecked():
                convertFun = self.CtoF
            elif self.radioButtonK.isChecked():
                convertFun = self.CtoK

            referenceData = self.data.copy(deep = True)
            referenceData[["Temp1","Temp2","Temp3","Temp4", "TempBed"]] = referenceData[["Temp1","Temp2","Temp3","Temp4", "TempBed"]].apply(convertFun)
            cleanedData[["Temp1","Temp2","Temp3","Temp4", "TempBed"]] = cleanedData[["Temp1","Temp2","Temp3","Temp4", "TempBed"]].apply(convertFun)

            return referenceData, cleanedData

    def browse(self):
        filePath = QtWidgets.QFileDialog.getOpenFileName(self, "Get Cleaned Measures File","", "CSV files (*.csv)")[0]
        if filePath:
            self.lineEditBrowseCleaned.setText(filePath)

    def switchTab(self):
        """
        Method called when user switches tab. For now, this resets the line edit with the path to the cleaned measures.
        """
        self.lineEditBrowseCleaned.setText("")

    def importCleanedData(self, path):
        """
        Given a path to a .csv file, open it and get relevant information for the backend. Return a dataframe with the correct structure.
        WARNING: this function MUST return a dataframe with exactly the structure defined, and without any NaNs, empty blanks...
        """
        # TODO: improve this function!
        df = pd.read_csv(path)
        columnnames = df.columns.values.tolist()
        if columnnames != ["Date","Temp1", "Temp2", "Temp3", "Temp4", "TempBed", "Pressure"]:
            displayCriticalMessage("The columns must be named (in this order): Date, Temp1, Temp2, Temp3, Temp4, TempBed, Pressure.")
            raise InvalidCSVStructure
        #The backend will call something like row[1] to have the Date. The first column must be the index, and not relevant data. Check if there is an index.
        if not(pd.Index(np.arange(0,len(df))).equals(df.index)):
            displayCriticalMessage("The dataframe must have the default index column as a numbering method.")
            raise InvalidCSVStructure
        df.dropna(inplace=True)

        try:
            convertDates(df)
        except Exception as e:
            displayCriticalMessage("The 'Date' column can't be converted to datetime objects.")
            raise InvalidCSVStructure
        return df

    def getCleanedMeasures(self):
        """
        Return the dataframe with the cleaned measures.
        Return an empty dataframe if something went wrong and the measures couldn't get extracted.
        """
        pathToCleaned = self.lineEditBrowseCleaned.text()
        if pathToCleaned == "":
            cleanedData = self.data.copy(deep = True)
            self.applyDateBoundariesChanges(cleanedData)
            self.applyCleanupChanges(cleanedData)
        else:
            try:
                cleanedData = self.importCleanedData(pathToCleaned)
            except Exception as e:
                cleanedData = pd.DataFrame() #Empty Dataframe
        return cleanedData
