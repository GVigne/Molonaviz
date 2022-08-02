from PyQt5.QtSql import QSqlQuery, QSqlDatabase #QSqlDatabase in used only for type hints
from src.backend.DetectorsModels import ThermometersModel

class LabEquipementManager:
    """
    A concrete class to handle operations on a laboratory's equipement. Contains inner models representing the state of a given laboratory (ie its sensors and their specs) and communicates with the frontend by using Containers objects.
    For now this class is mostly empty, as there is nothin implemented to change or modify a lab's equipement. But should this happen some day, then the infrastructure will be there.

    To bind frontend views to this classes' models, getters are implemented which return the models.
    """
    def __init__(self, con : QSqlDatabase, studyName : str):
        self.con = con
        self.thermoModel = ThermometersModel([])

        selectLabID = self.build_select_lab_id(studyName)
        selectLabID.exec()
        selectLabID.next()
        self.labID = selectLabID.value(0)    
    
    def getThermoModel(self):
        """
        This function should only be called by frontend users.
        Return the thermometer model.
        """
        return self.thermoModel
    
    def refreshDetectors(self):
        """
        This function should only be called by frontend users.
        Refresh the models with appropriate information from the database.
        """
        select_thermo = self.build_select_thermometers()
        self.thermoModel.newQueries([select_thermo])
    
    def build_select_lab_id(self, studyName : str):
        """
        Build and return a query giving the ID of the laboratory corresponding to the given study.
        """
        query = QSqlQuery(self.con)
        query.prepare(f"""SELECT Labo.ID FROM Labo
                        JOIN Study
                        ON Labo.ID = Study.Labo
                        WHERE Study.Name = '{studyName}'
        """)
        return query

    def build_select_thermometers(self):
        """
        Build and return a query which selects all thermometers corresponding to this lab.
        """
        selectQuery = QSqlQuery(self.con)
        selectQuery.prepare(f"""SELECT Thermometer.Name, Thermometer.ManuName, Thermometer.ManuRef, Thermometer.Error  
        FROM Thermometer
        WHERE Thermometer.Labo = {self.labID}""")
        return selectQuery