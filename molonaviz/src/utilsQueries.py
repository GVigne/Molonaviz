"""
Some useful queries which have been grouped here to prevent code duplication.
"""
from PyQt5.QtSql import QSqlQuery

def build_lab_id(con,labName):
    """
    Build and return a query giving the ID of the laboratory called labName.
    """
    query = QSqlQuery(con)
    query.prepare(f"SELECT Labo.ID FROM Labo WHERE Labo.Name ='{labName}'")
    return query