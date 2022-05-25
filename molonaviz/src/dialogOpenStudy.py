import os
from PyQt5 import QtCore, QtWidgets, uic
from PyQt5.QtSql import QSqlQuery
from src.utils import displayCriticalMessage


def tryOpenStudy(con):
    """
    This function either displays an error message (no study in database) or a dialog to choose one study.
    This function returns a string:
        -either the name of a study
        -or an empty string if there are no studies in the database or if the user clicked close.
    """
    studies_query = build_select_studies(con)
    studies = []
    studies_query.exec()
    while studies_query.next():
        studies.append(studies_query.value(0))

    if len(studies) ==0:
        displayCriticalMessage("No study was found in the database. Please create one first.")
    else:
        dlg = DialogOpenStudy(studies)
        dlg.setWindowModality(QtCore.Qt.ApplicationModal)
        res = dlg.exec_()
        if res == QtWidgets.QDialog.Accepted:
            return dlg.selectedStudy()
    return ""

From_DialogOpenStudy = uic.loadUiType(os.path.join(os.path.dirname(__file__), "..", "ui","dialogOpenStudy.ui"))[0]
class DialogOpenStudy(QtWidgets.QDialog,From_DialogOpenStudy):
    
    def __init__(self, studies):
        """
        Studies is a list of the names of the studies which should be displayed in the combo box.
        """
        super(DialogOpenStudy, self).__init__()
        QtWidgets.QDialog.__init__(self)
        self.setupUi(self)
        
        for study in studies:
            self.comboBoxShowStudies.addItem(study)
    
    def selectedStudy(self):
        """
        Return the currently selected study
        """
        return self.comboBoxShowStudies.currentText()

def build_select_studies(con):
    """
    Build and return a query giving all available studies in the database
    """
    query = QSqlQuery(con)
    query.prepare("SELECT Study.Name FROM Study")
    return query