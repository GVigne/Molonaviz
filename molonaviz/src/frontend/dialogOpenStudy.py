import os
from PyQt5 import QtWidgets, uic

From_DialogOpenStudy = uic.loadUiType(os.path.join(os.path.dirname(__file__), "ui","dialogOpenStudy.ui"))[0]
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