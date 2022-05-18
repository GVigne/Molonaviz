import os, errno
from PyQt5 import QtWidgets, uic

From_DialogOpenDatabase = uic.loadUiType(os.path.join("ui","dialogopendatabase.ui"))[0]
class DialogOpenDatabase(QtWidgets.QDialog,From_DialogOpenDatabase):
    
    def __init__(self):
        super(DialogOpenDatabase, self).__init__()
        QtWidgets.QDialog.__init__(self)
        self.setupUi(self)

        self.pushButtonBrowse.clicked.connect(self.browseDir)
        
    def browseDir(self):
        fileDir = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Database Directory")
        if fileDir:
            self.lineEditDatabaseDir.setText(fileDir)
    
    def getDir(self):
        fileDir = self.lineEditDatabaseDir.text()
        if not os.path.isdir(fileDir):
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), fileDir)
        return fileDir