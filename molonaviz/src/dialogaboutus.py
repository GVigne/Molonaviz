from PyQt5 import QtWidgets, uic
from PyQt5.QtGui import QPixmap
import os.path

From_DialogAboutUs = uic.loadUiType(os.path.join("ui","dialogaboutus.ui"))[0]

class DialogAboutUs(QtWidgets.QDialog,From_DialogAboutUs):
    def __init__(self):
        super(DialogAboutUs, self).__init__()
        QtWidgets.QDialog.__init__(self)
        
        self.setupUi(self)

        logoMines = os.path.join("imgs","LogoMines.jpeg")
        logoMolonaviz = os.path.join("imgs","MolonavizIcon.png")
        self.labelMolonaviz.setPixmap(QPixmap(logoMolonaviz))
        self.labelMines.setPixmap(QPixmap(logoMines))

