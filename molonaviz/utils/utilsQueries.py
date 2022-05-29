"""
Some useful queries which have been grouped here to prevent code duplication.
"""
from PyQt5.QtSql import QSqlQuery

def createStudyDatabase(con,studyname,labName):
    """
    Given a study name and a VALID laboratory name, create the corresponding study in the dabatase.
    """
    selectLabID = build_lab_id(con,labName)
    selectLabID.exec()
    selectLabID.next()
    labID = selectLabID.value(0)

    insertStudy = build_insert_study(con)
    insertStudy.bindValue(":Name",studyname)
    insertStudy.bindValue(":Labo",labID)
    insertStudy.exec()
    print(f"The study {studyname} has been added to the database.")

def build_insert_study(con):
    """
    Build and return a query creating a study in the database
    """
    query = QSqlQuery(con)
    query.prepare("""
        INSERT INTO Study(
            Name,
            Labo)
        VALUES (:Name, :Labo)
        """)
    return query

def build_lab_id(con,labName):
    """
    Build and return a query giving the ID of the laboratory called labName.
    """
    query = QSqlQuery(con)
    query.prepare(f"SELECT Labo.ID FROM Labo WHERE Labo.Name ='{labName}'")
    return query