import os
from PyQt5 import QtWidgets, uic

From_DialogOpenSPoint = uic.loadUiType(os.path.join(os.path.dirname(__file__), "ui","dialogOpenSPoint.ui"))[0]
class DialogOpenSPoint(QtWidgets.QDialog,From_DialogOpenSPoint):
    """
    Enable the user to choose a point to open from the ones already existing in the study.
    """
    def __init__(self, pointsNames : list[str]):
        """
        pointsNames should be the list of all the points in the current study.
        """
        super(DialogOpenSPoint, self).__init__()
        QtWidgets.QDialog.__init__(self)
        self.setupUi(self)

        for point in pointsNames:
            self.comboBoxShowPoints.addItem(point)

    def selectedSPoint(self):
        """
        Return the currently selected point.
        """
        return self.comboBoxShowPoints.currentText()