import os
from PyQt5 import QtWidgets, uic
from src.utils.utils import displayCriticalMessage
from src.Containers import SamplingPoint

From_DialogExportCleanedMeasures = uic.loadUiType(os.path.join(os.path.dirname(__file__), "ui","dialogExportCleanedMeasures.ui"))[0]
class DialogExportCleanedMeasures(QtWidgets.QDialog,From_DialogExportCleanedMeasures):
    """
    Enable the user to pick the path to the directory where the cleaned measures (two .csv files) will be saved.
    """
    def __init__(self, spoint : SamplingPoint):
        super(From_DialogExportCleanedMeasures, self).__init__()
        QtWidgets.QDialog.__init__(self)
        self.setupUi(self)

        self.lineEditPressuresName.setText(f"cleanedPressures{spoint.name}")
        self.lineEditTemperaturesName.setText(f"cleanedTemperatures{spoint.name}")

        self.pushButtonBrowse.clicked.connect(self.browseDir)
    
    def accept(self):
        """
        This is an overloaded function, called when the user presses the "OK" button.
        Make the directory given is a valid by the user.
        """
        if not os.path.isdir(self.lineEditCleanMeasDir.text()):
            displayCriticalMessage("The directory does not exist. Please give another one.")
            return
        super().accept()
        
    def browseDir(self):
        """
        Display a dialog so that the user may choose the target directory
        """
        fileDir = QtWidgets.QFileDialog.getExistingDirectory(self, "Select target directory")
        if fileDir:
            self.lineEditCleanMeasDir.setText(fileDir)
    
    def getFilesNames(self):
        """
        Return the correctly formated file paths.
        """
        fileDir = self.lineEditCleanMeasDir.text()
        pressPath = os.path.join(fileDir, self.lineEditPressuresName.text())
        tempPath = os.path.join(fileDir, self.lineEditTemperaturesName.text())
        return self.addCSVExtension(pressPath), self.addCSVExtension(tempPath)
    
    def addCSVExtension(self, filePath : str):
        """
        Add the .csv extension to the given file path if it already isn't there.
        """
        if filePath[-4:] ==".csv":
            return filePath
        return filePath + ".csv"