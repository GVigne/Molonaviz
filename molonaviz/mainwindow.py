from PyQt5 import QtWidgets, QtGui, QtCore, uic
from PyQt5.QtSql import QSqlDatabase
from src.dialogaboutus import DialogAboutUs
from src.dialogopendatabase import DialogOpenDatabase
from src.utils import displayCriticalMessage
import sys, os


From_MainWindow = uic.loadUiType("ui/mainwindow.ui")[0]


class MainWindow(QtWidgets.QMainWindow,From_MainWindow):
    def __init__(self):
        # Call constructor of parent classes
        super(MainWindow, self).__init__()
        QtWidgets.QMainWindow.__init__(self)
        self.setupUi(self)

        self.actionAboutMolonaViz.triggered.connect(self.aboutUs)

        self.con = None #Connection to the database
        self.openDatabase()
    
    def openDatabase(self):
        """
        If the user has never opened the database of if the config file is not valid (as a reminder, config is a text document containing the path to the database), display a dialog so the user may choose th e database directory.

        Then, open the database in the directory. 
        """
        databaseDir = None
        remember = False
        try:
            with open('config.txt') as f:
                databaseDir = f.readline()
        except OSError:
            #The config file does not exist. 
            dlg = DialogOpenDatabase()
            dlg.setWindowModality(QtCore.Qt.ApplicationModal)
            res = dlg.exec_()
            if res == QtWidgets.QDialog.Accepted:
                databaseDir = dlg.getDir()
                remember = dlg.checkBoxRemember.isChecked()
            else:
                #If the user cancels or quits the dialog, quit Molonaviz.
                sys.exit()

        databaseFile = os.path.join(databaseDir,"Molonari.sqlite")

        if os.path.isfile(databaseFile):
            #The database exists: open it.
            self.con = QSqlDatabase.addDatabase("QSQLITE")
            self.con.setDatabaseName(databaseFile)
            self.con.open()

            if remember:
                with open('config.txt', 'w') as f:
                    #Write (or overwrite) the path to the database file
                    f.write(databaseDir)
        else:
            #Problemn when finding the database.
            displayCriticalMessage("The database wasn't found. Please try again.")
            self.openDatabase()

    def aboutUs(self):
        dlg = DialogAboutUs()
        dlg.exec_()
    
    def closeEvent(self, event):
        """
        Close the database when user quits the app.
        """
        try:
            self.con.close()
        except Exception as e:
            pass
        super().close()


if __name__ == '__main__':

    app = QtWidgets.QApplication(sys.argv)
    app.setWindowIcon(QtGui.QIcon("../imgs/MolonavizIcon.png"))
    mainWin = MainWindow()
    mainWin.showMaximized()
    sys.exit(app.exec_())