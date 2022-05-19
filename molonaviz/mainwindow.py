from PyQt5 import QtWidgets, QtGui, QtCore, uic
from PyQt5.QtSql import QSqlDatabase
from src.dialogaboutus import DialogAboutUs
from src.dialogopendatabase import DialogOpenDatabase
from src.utils import displayCriticalMessage
import sys, os.path


From_MainWindow = uic.loadUiType(os.path.join(os.path.dirname(__file__),"ui","mainwindow.ui"))[0]
class MainWindow(QtWidgets.QMainWindow,From_MainWindow):
    def __init__(self):
        # Call constructor of parent classes
        super(MainWindow, self).__init__()
        QtWidgets.QMainWindow.__init__(self)
        self.setupUi(self)

        self.actionAboutMolonaViz.triggered.connect(self.aboutUs)
        self.actionOpenUserguideFR.triggered.connect(self.openUserGuideFR)
        self.actionQuitMolonaViz.triggered.connect(self.quitMolonaviz)

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
            with open(os.path.join(os.path.dirname(__file__),'config.txt')) as f:
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
                #This is a bit brutal. Maybe there can be some other way to quit via Qt: the problem is that, at this point in the script, the app (QtWidgets.QApplication) has not been executed yet.
                sys.exit()

        databaseFile = os.path.join(databaseDir,"Molonari.sqlite")

        if os.path.isfile(databaseFile):
            #The database exists: open it.
            self.con = QSqlDatabase.addDatabase("QSQLITE")
            self.con.setDatabaseName(databaseFile)
            self.con.open()

            if remember:
                with open(os.path.join(os.path.dirname(__file__),'config.txt'), 'w') as f:
                    #Write (or overwrite) the path to the database file
                    f.write(databaseDir)
        else:
            #Problemn when finding the database.
            displayCriticalMessage("The database wasn't found. Please try again.")
            self.openDatabase()

    def aboutUs(self):
        """
        Display a small dialog about the app.
        """
        dlg = DialogAboutUs()
        dlg.exec_()
    
    def quitMolonaviz(self):
        """
        Close the application.
        """
        QtWidgets.QApplication.quit()

    
    def closeEvent(self, event):
        """
        Close the database when user quits the app.
        """
        try:
            self.con.close()
        except Exception as e:
            pass
        super().close()
    
    def openUserGuideFR(self):
        userguidepath=os.path.dirname(__file__)
        userguidepath=os.path.join(userguidepath,"docs","UserguideFR.pdf")
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(userguidepath))


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    app.setWindowIcon(QtGui.QIcon(os.path.join(os.path.dirname(__file__),"imgs","MolonavizIcon.png")))
    mainWin = MainWindow()
    mainWin.showMaximized()
    sys.exit(app.exec_())