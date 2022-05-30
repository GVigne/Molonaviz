from PyQt5.QtSql import QSqlQuery
from src.Laboratory import Lab
from src.Containers import Point

class Study:
    """
    A concrete class to handle the study being currently opened by the user.
    """
    def __init__(self,con, studyName, thermoModel = None, psensorModel = None, shaftModel = None, pointModel = None):
        """
        thermoModel, psensorModel, shaftModel and pointModel are instances of MoloTreeViewModel. These are the models used to display data: the MoloQtList should be linked to these models.
        """
        self.con = con
        self.name = studyName

        self.lab = None
        self.createSelfLab(thermoModel, psensorModel, shaftModel)
        self.points = []
        self.createSelfPoints()
    
    def createSelfLab(self,thermoModel, psensorModel, shaftModel):
        """
        Build a Lab object which corresponds to the laboratory in the database.
        """
        labId= self.build_lab_name()
        labId.exec()
        labId.next()

        self.lab = Lab(self.con,labId.value(0),True, thermoModel=thermoModel, psensorModel=psensorModel, shaftModel=shaftModel)
    
    def createSelfPoints(self):
        """
        Populate self.points with Point objects corresponding to the SamplingPoints in the database.
        This method should only be called during the initialisation.
        """
        selectPoints = self.build_select_points()
        selectPoints.exec()
        while selectPoints.next():
            self.points.append(Point(selectPoints.value(0),selectPoints.value(1),selectPoints.value(2),selectPoints.value(3),selectPoints.value(4)))
        
    
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
        query.prepare(f"""SELECT SamplingPoint.Name, PressureSensor.Name, Shaft.Name, SamplingPoint.RiverBed, SamplingPoint.DeltaH
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