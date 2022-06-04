import os
from PyQt5 import QtCore, QtWidgets, uic
from PyQt5.QtSql import QSqlQuery, QSqlDatabase #QSqlDatabase in used only for type hints
from utils.utils import displayCriticalMessage
from utils.utilsQueries import build_point_names


def tryOpenPoint(con : QSqlDatabase, studyID : int | str):
    """
    This function either displays an error message (no point in the study) or a dialog to choose a point.
    This function returns a string:
        -either the name of a point
        -or an empty string if there are no points in the study or if the user clicked close.
    """
    point_queries = build_point_names(con, studyID)
    pointsNames = []
    point_queries.exec()
    while point_queries.next():
        pointsNames.append(point_queries.value(0))

    if len(pointsNames) ==0:
        displayCriticalMessage("No point was found in this study. Please import one first.")
    else:
        dlg = DialogOpenPoint(pointsNames)
        dlg.setWindowModality(QtCore.Qt.ApplicationModal)
        res = dlg.exec_()
        if res == QtWidgets.QDialog.Accepted:
            return dlg.selectedPoint()
    return ""

From_DialogOpenPoint = uic.loadUiType(os.path.join(os.path.dirname(__file__), "..", "ui","dialogOpenPoint.ui"))[0]
class DialogOpenPoint(QtWidgets.QDialog,From_DialogOpenPoint):
    """
    Enable the user to choose a point to open from the ones already existing in the study.
    """
    def __init__(self, pointsNames : list[str]):
        """
        pointsNames should be the list of all the points in the current study.
        """
        super(DialogOpenPoint, self).__init__()
        QtWidgets.QDialog.__init__(self)
        self.setupUi(self)
        
        for point in pointsNames:
            self.comboBoxShowPoints.addItem(point)
    
    def selectedPoint(self):
        """
        Return the currently selected point.
        """
        return self.comboBoxShowPoints.currentText()