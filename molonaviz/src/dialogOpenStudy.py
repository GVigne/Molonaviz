import os
from PyQt5 import QtCore, QtWidgets, uic
from PyQt5.QtSql import QSqlQuery, QSqlDatabase #QSqlDatabase in used only for type hints
from utils.utils import displayCriticalMessage


def tryOpenStudy(con : QSqlDatabase):
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
    """
    Enable the user to choose a study to open from the ones already existing in the database.
    Warning: this dialog does not ensure that the studies it display really are in the database. When creating an instance of this class, one must give a list names of studies: one element from this list will be chosen by the user but no verification is made that it is a valid study.
    """
    def __init__(self, studies : list[str]):
        super(DialogOpenStudy, self).__init__()
        QtWidgets.QDialog.__init__(self)
        self.setupUi(self)
        
        for study in studies:
            self.comboBoxShowStudies.addItem(study)
    
    def selectedStudy(self):
        """
        Return the currently selected study.
        """
        return self.comboBoxShowStudies.currentText()

def build_select_studies(con : QSqlDatabase):
    """
    Build and return a query giving all available studies in the database.
    """
    query = QSqlQuery(con)
    query.prepare("SELECT Study.Name FROM Study")
    return query