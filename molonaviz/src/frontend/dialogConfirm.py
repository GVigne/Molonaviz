import os
from PyQt5 import QtWidgets, uic

From_DialogConfirm = uic.loadUiType(os.path.join(os.path.dirname(__file__), "ui","dialogConfirm.ui"))[0]

class DialogConfirm(QtWidgets.QDialog,From_DialogConfirm):
    """
    Just a simple Confirm/Cancel window.
    """
    def __init__(self, message : str):
        """
        labs is the list of the names of all the laboratories in the database.
        """
        super(DialogConfirm, self).__init__()
        QtWidgets.QDialog.__init__(self)
        self.setupUi(self)
        self.plainTextEdit.insertPlainText(message)
