import os.path
import glob
import pandas as pd
from ast import literal_eval
from PyQt5.QtSql import QSqlQuery
from utils.utilsQueries import build_lab_id
from src.Containers import MoloQtList, Thermometer, PSensor, Shaft

class Lab:
    """
    A concrete class to do some manipulations on a laboratory.
    When creating an instance of this class, one MUST give a boolean (isInDatabase):
    -if isInDatabase, then the sensors corresponding to this lab will be extracted from the database. These are stored in a MoloQtList: the appropriate signals are connected to the MoloTreeViewModel thermoModel, psensorModel and shaftModel.
    -else this means we are trying to create a new laboratory from a directory. In this case, pathToDir MUST NOT be an empty string and MUST be a valid directory path.
    """
    def __init__(self, con, labName, isInDatabase, pathToDir = "", thermoModel = None, psensorModel = None, shaftModel = None):
        self.con = con
        self.labName = labName
        self.labId = None #Should be updated when the lab is created.
        self.thermometers = MoloQtList()
        self.psensors = MoloQtList()
        self.shafts = MoloQtList()
        if isInDatabase:
            self.refreshLabId()

            #Connect the signals to the given models.
            self.thermometers.appendSignal.connect(thermoModel.add_data)
            self.thermometers.removeSignal.connect(thermoModel.remove_data)
            self.thermometers.clearSignal.connect(thermoModel.clear)
            self.psensors.appendSignal.connect(psensorModel.add_data)
            self.psensors.removeSignal.connect(psensorModel.remove_data)
            self.psensors.clearSignal.connect(psensorModel.clear)
            self.shafts.appendSignal.connect(shaftModel.add_data)
            self.shafts.removeSignal.connect(shaftModel.remove_data)
            self.shafts.clearSignal.connect(shaftModel.clear)
            #Now, get the appropriate information from the database.
            self.extractSensors()
        else:
            self.pathToDir = pathToDir


    def checkIntegrity(self):
        """
        Check that this Lab is not in conflict with the database.
        For now, this means checking there is no laboratory with the same name in the database.
        """
        similar_lab = self.build_similar_lab()
        similar_lab.exec()
        if similar_lab.next():
            return False
        return True
    
    def addToDatabase(self):
        """
        Add the laboratory to the database.
        This function only works if no lab with the same name is in the database. It can't update a lab, only create a new one from scratch.
        """
        self.addLab()
        self.addThermometers()
        self.addPressureSensors()
        self.addShafts()

    def extractSensors(self):
        """
        This function should only be called if the lab is ALREADY in the database. 
        Update self.thermometers, self.psensors and self.shafts according to the database.
        """
        select_thermo = self.build_select_thermometers()
        select_thermo.exec()
        while select_thermo.next():
            self.thermometers.append(Thermometer(select_thermo.value(0),select_thermo.value(1),select_thermo.value(2),select_thermo.value(3)))
        
        select_psensor = self.build_select_psensors()
        select_psensor.exec()
        while select_psensor.next():
            self.psensors.append(PSensor(select_psensor.value(0),select_psensor.value(1),select_psensor.value(2),select_psensor.value(3),select_psensor.value(4),select_psensor.value(5),select_psensor.value(6)))

        select_shafts = self.build_select_shafts()
        select_shafts.exec()
        while select_shafts.next():
            self.shafts.append(Shaft(select_shafts.value(0),select_shafts.value(1), [select_shafts.value(i) for i in [2,3,4,5]], select_shafts.value(6)))

    def refreshLabId(self):
        """
        Update self.labID to reflect the ID in the database of the current Lab. This may only be called if the current lab is already in the database.
        """
        get_id = build_lab_id(self.con,self.labName)
        get_id.exec()
        get_id.next()
        self.labId = get_id.value(0)
    
    def addLab(self):
        insert_lab = self.build_insert_lab()
        insert_lab.exec()
        print(f"The lab {self.labName} has been added to the database.")
        self.refreshLabId()

    def addThermometers(self):
        tempdir = os.path.join(self.pathToDir, "temperature_sensors", "*.csv")
        files = glob.glob(tempdir)
        files.sort()
        nb_errors = 0
        insertQuery = self.build_insert_thermometer()
        for file in files:
            try :
                df = pd.read_csv(file, header=None, index_col=0)
                consName = df.iloc[0].at[1] 
                ref = df.iloc[1].at[1]
                name = df.iloc[2].at[1]
                sigma = float(df.iloc[3].at[1].replace(',','.'))

                insertQuery.bindValue(":Name",name)
                insertQuery.bindValue(":Manu_name",consName)
                insertQuery.bindValue(":Manu_ref",ref)
                insertQuery.bindValue(":Error",sigma)
                insertQuery.bindValue(":Labo",self.labId)
                insertQuery.exec()
            except Exception:
                nb_errors +=1
                print("Couldn't load thermometer ", file)
        if nb_errors ==0:
            print("The thermometers have been added to the database.")

    def addPressureSensors(self):
        psdir = os.path.join(self.pathToDir, "pressure_sensors", "*.csv")
        files = glob.glob(psdir)
        files.sort()
        nb_errors = 0
        insertPsensor = self.build_insert_psensor()
        for file in files:
            try :
                df = pd.read_csv(file, header=None, index_col=0)
                name = df.iloc[0].at[1]
                datalogger = df.iloc[1].at[1]
                calibrationDate = df.iloc[2].at[1]
                intercept = float(df.iloc[3].at[1].replace(',','.'))
                dudh = float(df.iloc[4].at[1].replace(',','.'))
                dudt = float(df.iloc[5].at[1].replace(',','.'))
                sigma = float(df.iloc[6].at[1].replace(',','.'))
                thermo_name = df.iloc[7].at[1]
                select_thermo = self.build_thermo_id(thermo_name)
                select_thermo.exec()
                select_thermo.next()
                thermo_model = select_thermo.value(0)

                insertPsensor.bindValue(":Name",name)
                insertPsensor.bindValue(":Datalogger",datalogger)
                insertPsensor.bindValue(":Calibration",calibrationDate)
                insertPsensor.bindValue(":Intercept",intercept)
                insertPsensor.bindValue(":DuDh",dudh)
                insertPsensor.bindValue(":DuDt",dudt)
                insertPsensor.bindValue(":Precision",sigma)
                insertPsensor.bindValue(":Thermo_model",thermo_model)
                insertPsensor.bindValue(":Labo",self.labId)
                insertPsensor.exec()
            except Exception:
                nb_errors +=1
                print("Couldn't load pressure sensor ", file)
        if nb_errors ==0:
            print("The pressure sensors have been added to the database.")

    def addShafts(self):
        psdir = os.path.join(self.pathToDir, "shafts", "*.csv")
        files = glob.glob(psdir)
        files.sort()
        nb_errors = 0
        insertShaft = self.build_insert_shaft()
        for file in files:
            try :
                df = pd.read_csv(file, header=None)
                name = df.iloc[0].at[1]
                datalogger = df.iloc[1].at[1]
                tSensorName = df.iloc[2].at[1] 
                depths = literal_eval(df.iloc[3].at[1]) #This is now a list
                select_thermo = self.build_thermo_id(tSensorName)
                select_thermo.exec()
                select_thermo.next()
                thermo_model = select_thermo.value(0)

                insertShaft.bindValue(":Name",name)
                insertShaft.bindValue(":Datalogger", datalogger)
                insertShaft.bindValue(":Depth1",depths[0])
                insertShaft.bindValue(":Depth2",depths[1])
                insertShaft.bindValue(":Depth3",depths[2])
                insertShaft.bindValue(":Depth4",depths[3])
                insertShaft.bindValue(":Thermo_model",thermo_model)
                insertShaft.bindValue(":Labo",self.labId)
                insertShaft.exec()
            except Exception:
                nb_errors +=1
                print("Couldn't load shaft ", file)
        if nb_errors ==0:
            print("The shafts have been added to the database.")
    
    def close(self):
        """
        Close the lab and its dependencies.
        """
        #Clear the models and the views showing this lab's sensors.
        self.thermometers.clear()
        self.psensors.clear()
        self.shafts.clear()
    
    def build_similar_lab(self):
        """
        Build and return a query to check is a lab with the same name is in the database.
        """
        query = QSqlQuery(self.con)
        query.prepare(f"SELECT Labo.Name FROM Labo WHERE Labo.Name ='{self.labName}'")
        return query

    def build_insert_lab(self):
        """
        Build and return a query which inserts into the database the current lab.
        """
        query = QSqlQuery(self.con)
        query.prepare(f"INSERT INTO Labo (Name) VALUES ('{self.labName}')")
        return query

    def build_insert_thermometer(self):
        """
        Build and return a query which creates a thermometer.
        """
        insertQuery = QSqlQuery(self.con)
        insertQuery.prepare(
        """
        INSERT INTO Thermometer (
            Name,
            Manu_name,
            Manu_ref,
            Error,
            Labo
        )
        VALUES (:Name, :Manu_name, :Manu_ref, :Error, :Labo)
        """)
        return insertQuery
    
    def build_thermo_id(self,thermoname):
        """
        Build and return a query giving a the ID of a given thermometer.
        """
        selectQuery = QSqlQuery(self.con)
        selectQuery.prepare(f"SELECT Thermometer.ID FROM Thermometer WHERE Thermometer.Name = '{thermoname}' AND Thermometer.Labo = '{self.labId}'")
        return selectQuery
    
    def build_insert_psensor(self):
        """
        Build and return a query which creates a pressure sensor.
        """
        insertQuery = QSqlQuery(self.con)
        insertQuery.prepare(
        """ 
        INSERT INTO PressureSensor (
            Name,
            Datalogger,
            Calibration,
            Intercept,
            [Du/Dh],
            [Du/Dt],
            Precision,
            Thermo_model,
            Labo
        )
        VALUES (:Name, :Datalogger, :Calibration, :Intercept, :DuDh, :DuDt, :Precision, :Thermo_model, :Labo)
        """)
        return insertQuery
    
    def build_insert_shaft(self):
        """
        Build and return a query which creates a shaft.
        """
        insertQuery = QSqlQuery(self.con)
        insertQuery.prepare("""
            INSERT INTO Shaft (
                Name,
                Depth1,
                Datalogger,
                Depth2,
                Depth3,
                Depth4,
                Thermo_model,
                Labo
            )
            VALUES (:Name, :Datalogger, :Depth1, :Depth2, :Depth3, :Depth4, :Thermo_model, :Labo)
            """)
        return insertQuery
    
    def build_select_thermometers(self):
        """
        Build and return a query which selects all thermometers corresponding to this lab.
        """
        selectQuery = QSqlQuery(self.con)
        selectQuery.prepare(f"""SELECT Thermometer.Name, Thermometer.Manu_name, Thermometer.Manu_ref, Thermometer.Error  
        FROM Thermometer
        WHERE Thermometer.Labo = {self.labId}""")
        return selectQuery
    
    def build_select_psensors(self):
        """
        Build and return a query which selects all pressure sensors corresponding to this lab.
        """
        selectQuery = QSqlQuery(self.con)
        selectQuery.prepare(f"""SELECT PressureSensor.Name, PressureSensor.Datalogger, PressureSensor.Calibration, PressureSensor.Intercept, PressureSensor."Du/Dh", PressureSensor."Du/Dt", PressureSensor.Precision
        FROM PressureSensor
        WHERE PressureSensor.Labo = {self.labId}""")
        return selectQuery

    
    def build_select_shafts(self):
        """
        Build and return a query which selects all shafts corresponding to this lab.
        """
        selectQuery = QSqlQuery(self.con)
        selectQuery.prepare(f""" SELECT Shaft.Name, Shaft.Datalogger, Shaft.Depth1, Shaft.Depth2, Shaft.Depth3, Shaft.Depth4, Thermometer.Name
        FROM Shaft
        JOIN Thermometer
        ON Shaft.Thermo_model = Thermometer.ID
        WHERE Shaft.Labo = {self.labId}""")
        return selectQuery
