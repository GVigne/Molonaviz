import os
from PyQt5 import QtCore, QtWidgets, uic
from PyQt5.QtSql import QSqlQuery
from utils.utils import displayCriticalMessage

def tryCreateStudy(con):
    """
    This function either displays an error message (no labs in database) or a dialog to choose a lab and the name of the study.
    This function returns a string:
        -either the name of the created study
        -or an empty string if there are no studies in the database or if the user clicked close.
    """
    labs_query = build_select_labs(con)
    labs = []
    labs_query.exec()
    while labs_query.next():
        labs.append(labs_query.value(0))

    if len(labs) ==0:
        displayCriticalMessage("No laboratory was found in the database. Please create one first.")
    else:
        dlg = DialogCreateStudy(labs)
        dlg.setWindowModality(QtCore.Qt.ApplicationModal)
        res = dlg.exec_()
        if res == QtWidgets.QDialog.Accepted:
            userLab = dlg.selectedLab()
            userStudyName = dlg.studyName()
            if not checkUniqueStudyName(con,userStudyName) or not userStudyName: #The study is already in the database, or the study name is empty
                displayCriticalMessage("The name of the study may not be empty and must be different from the studies in the database")
            else:
                return userStudyName,userLab
    return "",""

From_DialogCreateStudy = uic.loadUiType(os.path.join(os.path.dirname(__file__), "..", "ui","dialogCreateStudy.ui"))[0]
class DialogCreateStudy(QtWidgets.QDialog,From_DialogCreateStudy):
    
    def __init__(self,labs):
        """
        Studies is a list of the names of the studies which should be displayed in the combo box.
        """
        super(DialogCreateStudy, self).__init__()
        QtWidgets.QDialog.__init__(self)
        self.setupUi(self)
        
        for lab in labs:
            self.comboBoxShowLabs.addItem(lab)
    
    def selectedLab(self):
        """
        Return the currently selected laboratory.
        """
        return self.comboBoxShowLabs.currentText()
    
    def studyName(self):
        """
        Return the name of the study.
        """
        return self.lineEditStudyName.text()

def checkUniqueStudyName(con,studyName):
    """
    Return True if studyName is not the name of a study in the database.
    """
    similar_studies = build_similar_studies(con,studyName)
    similar_studies.exec()
    if similar_studies.next():
        return False
    return True

def build_similar_studies(con,studyName):
    """
    Build and return a query giving all the studies in the database with the name studyName
    """
    query = QSqlQuery(con)
    query.prepare(f"SELECT * FROM Study WHERE Study.Name='{studyName}'")
    return query

def build_select_labs(con):
    """
    Build and return a query giving all available labs in the database
    """
    query = QSqlQuery(con)
    query.prepare("SELECT Labo.Name FROM Labo")
    return query