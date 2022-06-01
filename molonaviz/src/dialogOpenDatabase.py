import os, sys
from PyQt5 import QtWidgets, uic
from utils.utils import displayCriticalMessage

From_DialogOpenDatabase = uic.loadUiType(os.path.join(os.path.dirname(__file__), "..", "ui","dialogOpenDatabase.ui"))[0]
class DialogOpenDatabase(QtWidgets.QDialog,From_DialogOpenDatabase):
    """
    Enable the user to choose the path to the directory containing the database and associated files.
    """
    def __init__(self):
        super(DialogOpenDatabase, self).__init__()
        QtWidgets.QDialog.__init__(self)
        self.setupUi(self)

        self.pushButtonBrowse.clicked.connect(self.browseDir)
        
    def browseDir(self):
        """
        Display a dialog so that the user may choose the database directory.
        """
        fileDir = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Database Directory")
        if fileDir:
            self.lineEditDatabaseDir.setText(fileDir)
    
    def getDir(self):
        """
        Return the directory path given by the user.
        """
        fileDir = self.lineEditDatabaseDir.text()
        if not os.path.isdir(fileDir):
            displayCriticalMessage("This directory was not found.")
            sys.exit()
        return fileDir