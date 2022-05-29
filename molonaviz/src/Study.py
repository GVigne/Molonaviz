from PyQt5.QtSql import QSqlQuery
from src.Laboratory import Lab

class Study:
    """
    A concrete class to handle the study being currently opened by the user.
    """
    def __init__(self,con, studyName):
        self.con = con
        self.name = studyName

        self.lab = None
        self.createSelfLab()
        self.points = []
    
    def createSelfLab(self):
        """
        Build a Lab object which corresponds to the laboratory in the database.
        """
        labId= self.build_lab_name()
        labId.exec()
        labId.next()

        self.lab = Lab(self.con,labId.value(0),True)
    
    def build_lab_name(self):
        """
        Give the name of the laboratory corresponding to this study.
        """
        query = QSqlQuery(self.con)
        query.prepare(f"""SELECT Labo.Name FROM Labo
                        JOIN Study
                        ON Labo.ID = Study.Labo
                        WHERE Study.Name = '{self.name}'
        """)
        return query