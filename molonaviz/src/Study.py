from PyQt5.QtSql import QSqlQuery, QSqlDatabase #QSqlDatabase in used only for type hints
from PyQt5 import QtWidgets
from src.Laboratory import Lab
from src.Containers import MoloQtList, Point
from utils.utilsQueries import build_study_id
import shutil, os
import pandas as pd
from src.MoloTreeViewModels import ThermometerTreeViewModel, PSensorTreeViewModel, ShaftTreeViewModel, PointTreeViewModel #Used only for type hints
from src.widgetPoint import WidgetPoint
from src.subWindow import SubWindow

class Study:
    """
    A concrete class to handle the study being currently opened by the user. This class does not handle creation of a study in the database.
    """
    def __init__(self, con : QSqlDatabase, studyName : str, thermoModel : ThermometerTreeViewModel, psensorModel : PSensorTreeViewModel, shaftModel : ShaftTreeViewModel, pointModel : PointTreeViewModel):
        """
        thermoModel, psensorModel, shaftModel and pointModel are the models used to display data in the main window: the MoloQtList should be linked to these models.
        """
        self.con = con
        self.name = studyName
        #Also store the ID of the study as it can come in handy for queries
        select_id = build_study_id(self.con, self.name)
        select_id.exec()
        select_id.next()
        self.ID = select_id.value(0)

        self.lab = None
        self.setupSelfLab(thermoModel, psensorModel, shaftModel)
        self.points = MoloQtList()
        #Connect the signals to the given models.
        self.points.appendSignal.connect(pointModel.add_data)
        self.points.removeSignal.connect(pointModel.remove_data)
        self.points.clearSignal.connect(pointModel.clear)
        self.setupSelfPoints()
    
    def setupSelfLab(self,thermoModel : ThermometerTreeViewModel, psensorModel : PSensorTreeViewModel, shaftModel : ShaftTreeViewModel):
        """
        Build a Lab object which corresponds to the laboratory in the database.
        """
        labId= self.build_lab_name()
        labId.exec()
        labId.next()

        self.lab = Lab(self.con,labId.value(0),True, thermoModel=thermoModel, psensorModel=psensorModel, shaftModel=shaftModel)
    
    def setupSelfPoints(self):
        """
        Populate self.points with Point objects corresponding to the SamplingPoints in the database.
        This method should only be called during the initialisation.
        """
        selectPoints = self.build_select_points()
        selectPoints.exec()
        while selectPoints.next():
            self.points.append(Point(selectPoints.value(0),selectPoints.value(1),selectPoints.value(2),selectPoints.value(3),selectPoints.value(4)))
    
    def importNewPoint(self, pointName : str, psensorName : str, shaftName :str, infofile : str, noticefile : str, configfile : str, prawfile : str, trawfile : str):
        """
        Create a new Sampling Point in the database, and fill in the RawMeasures table with the given information.
        """
        newPoint = self.createNewPoint(pointName, psensorName, shaftName, infofile, noticefile, configfile) #This is a Point object
        self.points.append(newPoint)

        dfpress, dftemp = self.processDataFrames(prawfile,trawfile) 
        select_point_id = self.build_point_id(newPoint.name)
        select_point_id.exec()
        select_point_id.next()
        self.createRawPressRecord(dfpress, select_point_id.value(0))
        self.createRawTempRecord(dftemp, select_point_id.value(0))
        
    
    def createNewPoint(self, pointName : str, psensorName : str, shaftName :str, infofile : str, noticefile : str, configfile : str):
        """
        Create a new Sampling Point in in the database with the relevant information. Return an object of type Point encapsulating these informations.
        Note: although the info file has the name of the point, the pressure sensor and the shaft, the user may have changed it, so pointName, psensorName and shaftName are not necessarily the names listed in infofile.
        """
        insertPoint = self.build_insert_point()

        insertPoint.bindValue(":Name", pointName)
        insertPoint.bindValue(":Study", self.ID)
        #Path to the notice file
        newNoticePath = os.path.join(os.path.dirname(self.con.databaseName()),"Notices", os.path.basename(noticefile))
        shutil.copy2(noticefile, newNoticePath)
        insertPoint.bindValue(":Notice", newNoticePath)
        #Extract relevant data from the infofile.
        df = pd.read_csv(infofile, header=None)
        insertPoint.bindValue(":Setup", df.iloc[3].at[1])
        insertPoint.bindValue(":LastTransfer", df.iloc[4].at[1])
        offset = df.iloc[6].at[1]
        insertPoint.bindValue(":Offset", offset)
        rivBed = df.iloc[5].at[1]
        insertPoint.bindValue(":RiverBed", rivBed)
        #Add the shaft's ID
        select_shaft_id = self.build_shaft_id(shaftName)
        select_shaft_id.exec()
        select_shaft_id.next()
        insertPoint.bindValue(":Shaft", select_shaft_id.value(0))
        #Add the pressure sensor's ID
        select_psensor_id = self.build_psensor_id(psensorName)
        select_psensor_id.exec()
        select_psensor_id.next()
        insertPoint.bindValue(":PressureSensor", select_psensor_id.value(0))
        #Path to the configuration file
        newConfigPath = os.path.join(os.path.dirname(self.con.databaseName()),"Schemes", os.path.basename(configfile))
        shutil.copy2(configfile, newConfigPath)
        insertPoint.bindValue(":Scheme", newConfigPath)

        insertPoint.exec()

        return Point(pointName, psensorName, shaftName, rivBed, offset)
    
    def processDataFrames(self, prawfile : str, trawfile : str):
        """
        Given the path to the pressure readings and the path to the temperature profiles, return two cleaned dataframes: these dataframes are compatible with the database (ie correct number of lines, no NaN,...)
        """
        #Rename the colonnes, delete lignes without any value and delete the index.
        dfpress = pd.read_csv(prawfile)
        val_cols = ["Date", "Voltage", "Temp_Stream"]
        for i in range(len(val_cols)) :
            dfpress.columns.values[i] = val_cols[i]
        dfpress.dropna(subset=val_cols,inplace=True)
        
        dftemp = pd.read_csv(trawfile)
        val_cols = ["Date", "Temp1", "Temp2", "Temp3", "Temp4"]
        for i in range(len(val_cols)) :
            dftemp.columns.values[i] = val_cols[i] 
        dftemp.dropna(subset=val_cols,inplace=True)
        
        return dfpress, dftemp
    
    def createRawPressRecord(self, dfpress : pd.DataFrame, pointID : int | str):
        """
        Extract data from a dataframe and fill the table RawMeasuresPressure with it.
        """
        self.con.transaction()
        insertRawPress = self.build_insert_raw_pressures()
        insertRawPress.bindValue(":PointKey", pointID)
        for row in dfpress.itertuples():
            insertRawPress.bindValue(":Date", row[1])
            insertRawPress.bindValue(":TempBed", row[3])
            insertRawPress.bindValue(":Voltage", row[2])
            insertRawPress.exec()
        self.con.commit()
    
    def createRawTempRecord(self, dftemp : pd.DataFrame, pointID : int | str):
        """
        Extract data from a dataframe and fill the table RawMeasuresTemp with it.
        """
        self.con.transaction()
        insertRawTemp = self.build_insert_raw_temperatures()
        insertRawTemp.bindValue(":PointKey", pointID)
        for row in dftemp.itertuples():
            insertRawTemp.bindValue(":Date", row[1])
            insertRawTemp.bindValue(":Temp1", row[2])
            insertRawTemp.bindValue(":Temp2", row[3])
            insertRawTemp.bindValue(":Temp3", row[4])
            insertRawTemp.bindValue(":Temp4", row[5])
            insertRawTemp.exec()
        self.con.commit()
    
    def openPoint(self, pointName : str, mdi):
        """
        Given a VALID name of a point (ie the name of a point which is in the study), open it in the visualisation window.
        """
        for p in self.points:
            if p.name == pointName:
                point = p
        wdg = WidgetPoint(self.con, point)
        subwindow = SubWindow(wdg)
        mdi.addSubWindow(subwindow)
        subwindow.show()
            
    def close(self):
        """
        Close the study and all related windows.
        """
        # self.points #Clear 
        self.lab.close()
        self.points.clear()

    def build_lab_name(self):
        """
        Build and return a query giving the name of the laboratory corresponding to this study.
        """
        query = QSqlQuery(self.con)
        query.prepare(f"""SELECT Labo.Name FROM Labo
                        JOIN Study
                        ON Labo.ID = Study.Labo
                        WHERE Study.Name = '{self.name}'
        """)
        return query
    
    def build_select_points(self):
        """
        Build and return a query giving all the informations about the points in this study.
        """
        query = QSqlQuery(self.con)
        query.prepare(f"""SELECT SamplingPoint.Name, PressureSensor.Name, Shaft.Name, SamplingPoint.RiverBed, SamplingPoint.Offset
                    FROM SamplingPoint
                    JOIN PressureSensor
                    ON SamplingPoint.PressureSensor = PressureSensor.ID
                    JOIN Shaft
                    ON SamplingPoint.Shaft = Shaft.ID
                    JOIN Study
                    ON SamplingPoint.Study = Study.ID
                    WHERE Study.Name = '{self.name}'
        """)
        return query
    
    def build_insert_point(self):
        """
        Build and return a query which creates a Sampling Point.
        """
        query = QSqlQuery(self.con)
        query.prepare(f"""INSERT INTO SamplingPoint (
                              Name,
                              Notice,
                              Setup,
                              LastTransfer,
                              Offset,
                              RiverBed,
                              Shaft,
                              PressureSensor,
                              Study,
                              Scheme,
                              CleanupScript)
                          VALUES (:Name, :Notice, :Setup, :LastTransfer, :Offset, :RiverBed, :Shaft, :PressureSensor, :Study, :Scheme, null)""")
        return query
    
    def build_insert_raw_pressures(self):
        """
        Build and return a query which fills the table with raw pressure readings.
        """
        query = QSqlQuery(self.con)
        query.prepare(f"""INSERT INTO RawMeasuresPress (
                        Date,
                        TempBed,
                        Voltage,
                        PointKey)
        VALUES (:Date, :TempBed, :Voltage, :PointKey)""")
        return query
    
    def build_insert_raw_temperatures(self):
        """
        Build and return a query which fills the table with raw temperature readings.
        """
        query = QSqlQuery(self.con)
        query.prepare(f""" INSERT INTO RawMeasuresTemp (
                        Date,
                        Temp1,
                        Temp2,
                        Temp3,
                        Temp4,
                        PointKey)
        VALUES (:Date, :Temp1, :Temp2, :Temp3, :Temp4, :PointKey)""")
        return query
    
    def build_psensor_id(self, psensorName : str):
        """
        Build and return a query giving the ID of the pressure sensor in this study called psensorName.
        """
        query = QSqlQuery(self.con)
        query.prepare(f"""SELECT PressureSensor.ID FROM PressureSensor
                        JOIN Labo
                        ON PressureSensor.Labo = Labo.ID
                        JOIN Study 
                        ON Study.Labo = Labo.ID
                        WHERE Study.ID = '{self.ID}' AND PressureSensor.Name = '{psensorName}'""")
        return query
    
    def build_shaft_id(self, shaftName : str):
        """
        Build and return a query giving the ID of the shaft in this study called shaftName.
        """
        query = QSqlQuery(self.con)
        query.prepare(f"""SELECT Shaft.ID FROM Shaft
                        JOIN Labo
                        ON Shaft.Labo = Labo.ID
                        JOIN Study 
                        ON Study.Labo = Labo.ID
                        WHERE Study.ID = '{self.ID}' AND Shaft.Name = '{shaftName}'""")
        return query
    
    def build_point_id(self, pointName : str):
        """
        Build and return a query giving the ID of the sampling point in this study called pointName.
        """
        query = QSqlQuery(self.con)
        query.prepare(f"""SELECT SamplingPoint.ID FROM SamplingPoint
                        JOIN Study 
                        ON SamplingPoint.Study = Study.ID
                        WHERE Study.ID = '{self.ID}' AND SamplingPoint.Name = '{pointName}'""")
        return query