from PyQt5 import QtWidgets, QtGui, uic
from dialogaboutus import DialogAboutUs
import sys


From_MainWindow = uic.loadUiType("../ui/mainwindow.ui")[0]


class MainWindow(QtWidgets.QMainWindow,From_MainWindow):
    def __init__(self):
        # Call constructor of parent classes
        super(MainWindow, self).__init__()
        QtWidgets.QMainWindow.__init__(self)
        self.setupUi(self)

        self.actionAboutMolonaViz.triggered.connect(self.aboutUs)

    def aboutUs(self):
        dlg = DialogAboutUs()
        dlg.exec_()

if __name__ == '__main__':

    app = QtWidgets.QApplication(sys.argv)
    app.setWindowIcon(QtGui.QIcon("../imgs/MolonavizIcon.png"))
    mainWin = MainWindow()
    mainWin.showMaximized()
    sys.exit(app.exec_())