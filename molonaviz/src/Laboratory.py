import os.path
import glob
import pandas as pd
from ast import literal_eval
from PyQt5.QtSql import QSqlQuery

class Lab:
    """
    A concrete class to do some manipulations on a Lab. For now, this is used when importing a lab from a directory.
    """
    def __init__(self, con, pathToDir,labName):
        self.con = con
        self.pathToDir = pathToDir
        self.labName = labName
        self.labId = None #Should be updated when the lab is created.
    
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
    
    def addLab(self):
        insert_lab = self.build_insert_lab()
        insert_lab.exec()
        print(f"The lab {self.labName} has been added to the database.")

        get_id = self.build_lab_id()
        get_id.exec()
        get_id.next()
        self.labId = get_id.value(0)

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
        query.prepare(f"INSERT INTO Labo (Name) VALUES ('{self.labName}');")
        return query
    
    def build_lab_id(self):
        """
        Build and return a query giving the ID of the current lab.
        """
        query = QSqlQuery(self.con)
        query.prepare(f"SELECT Labo.ID FROM Labo WHERE Labo.Name ='{self.labName}'")
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