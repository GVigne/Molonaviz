import sys, os, errno
from PyQt5 import QtWidgets, uic
from PyQt5.QtGui import QPixmap


From_DialogAboutUs = uic.loadUiType("../ui/dialogaboutus.ui")[0]

class DialogAboutUs(QtWidgets.QDialog,From_DialogAboutUs):
    def __init__(self):
        super(DialogAboutUs, self).__init__()
        QtWidgets.QDialog.__init__(self)
        
        self.setupUi(self)

        logoMines = os.path.join(os.path.dirname(__file__), "../imgs/LogoMines.jpeg")
        logoMolonaviz = os.path.join(os.path.dirname(__file__), "../imgs/MolonavizIcon.png")

        self.labelMolonaviz.setPixmap(QPixmap(logoMolonaviz))
        self.labelMines.setPixmap(QPixmap(logoMines))
        # self.labelMolonaviz.setScaledContents(True)
        # self.labelMines.setScaledContents(True)

