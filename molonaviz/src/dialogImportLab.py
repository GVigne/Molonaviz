import os
from PyQt5 import QtWidgets, uic
from src.utils import displayCriticalMessage

From_DialogImportLab = uic.loadUiType(os.path.join(os.path.dirname(__file__), "..", "ui","dialogImportLab.ui"))[0]
class DialogImportLab(QtWidgets.QDialog,From_DialogImportLab):
    
    def __init__(self):
        super(DialogImportLab, self).__init__()
        QtWidgets.QDialog.__init__(self)
        self.setupUi(self)

        self.pushButtonBrowse.clicked.connect(self.browseDir)
        
    def browseDir(self):
        fileDir = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Laboratory Directory")
        if fileDir:
            self.lineEditLabDir.setText(fileDir)
    
    def getLaboInfo(self):
        fileDir = self.lineEditLabDir.text()
        labName = self.lineEditLabName.text()
        if not os.path.isdir(fileDir):
            displayCriticalMessage("This directory was not found")
        elif labName =="":
            displayCriticalMessage("The laboratory's name cannot be empty. \nPlease also make sure a laboratory with the same name does not already exist.")
        return fileDir,labName