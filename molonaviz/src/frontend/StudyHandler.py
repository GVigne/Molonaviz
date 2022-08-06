from PyQt5.QtSql import QSqlDatabase #Used only for type hints
import pandas as pd
from src.utils.utils import convertDates

from src.backend.SamplingPointManager import SamplingPointManager
from src.backend.SPointCoordinator import SPointCoordinator
from src.frontend.SamplingPointViewer import SamplingPointViewer

class StudyHandler:
    """
    A high-level concrete frontend class to handle the user's actions regarding a study.
    An instance of this class can:
        -open and close a study
        -call the backend to add or remove sampling points (SamplingPointManager)
        -open subwindows showing the results and computations related to sampling points in this study.
    An instance of this class is always linked to a study.
    """
    def __init__(self, con : QSqlDatabase, studyName : str):
        self.con = con
        self.studyName = studyName
        self.spointManager = SamplingPointManager(self.con, studyName)

        self.spointCoordinator = None
        self.spointViewer = None
    
    def getSPointModel(self):
        """
        Return the sampling point model.
        """
        return self.spointManager.getSPointModel()
    
    def getSPointsNames(self):
        """
        Return the list of the names of the sampling points.
        """
        return self.spointManager.getSPointsNames()
    
    def refreshSPoints(self):
        """
        Refresh sampling points information
        """
        self.spointManager.refreshSPoints()
    
    def importSPoint(self, name : str, psensor : str, shaft : str, infofile : str, noticefile : str, configfile : str, prawfile : str, trawfile : str):
        """
        Import a new sampling point from given files.
        """
        #Cleanup the .csv files
        infoDF = pd.read_csv(infofile, header=None)
        #Readings csv
        dfpress = pd.read_csv(prawfile)
        dfpress.columns = ["Date", "Voltage", "Temp_Stream"]
        dfpress.dropna(inplace=True)
        convertDates(dfpress)
        dfpress["Date"] = dfpress["Date"].dt.strftime("%Y/%m/%d %H:%M:%S")

        dftemp = pd.read_csv(trawfile)
        dftemp.columns = ["Date", "Temp1", "Temp2", "Temp3", "Temp4"]
        dftemp.dropna(inplace=True)
        convertDates(dftemp)
        dftemp["Date"] = dftemp["Date"].dt.strftime("%Y/%m/%d %H:%M:%S")

        #Give the dataframes to the backend
        self.spointManager.createNewSPoint(name, psensor, shaft, noticefile, configfile, infoDF, dfpress, dftemp)
        self.spointManager.refreshSPoints()
    
    def openSPoint(self, spointName : str):
        """
        Open the sampling point with the name spointName.
        Return a viewer instance which can be added to a subwindow like a widget.
        """
        self.spointCoordinator = SPointCoordinator(self.con, self.studyName, spointName)
        samplingPoint = self.spointManager.getSPoint(spointName)
        self.spointViewer = SamplingPointViewer(self.spointCoordinator, samplingPoint)
        return self.spointViewer

    def close(self):
        """
        Close all subwindows and related processes.
        """
        pass