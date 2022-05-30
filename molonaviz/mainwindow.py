from PyQt5 import QtWidgets, QtGui, QtCore, uic
from PyQt5.QtSql import QSqlDatabase

from queue import Queue
import sys, os.path
from src.Study import Study

from src.dialogAboutUs import DialogAboutUs
from src.dialogOpenDatabase import DialogOpenDatabase
from src.dialogImportLab import DialogImportLab
from src.dialogCreateStudy import DialogCreateStudy
from src.dialogOpenStudy import tryOpenStudy
from src.dialogCreateStudy import tryCreateStudy

from src.Laboratory import Lab
from utils.utils import displayCriticalMessage
from utils.utilsQueries import createStudyDatabase
from src.printThread import InterceptOutput, Receiver
from src.MoloTreeViewModels import ThermometerTreeViewModel, PSensorTreeViewModel, ShaftTreeViewModel, PointTreeViewModel

From_MainWindow = uic.loadUiType(os.path.join(os.path.dirname(__file__),"ui","mainwindow.ui"))[0]
class MainWindow(QtWidgets.QMainWindow,From_MainWindow):
    def __init__(self):
        # Call constructor of parent classes
        super(MainWindow, self).__init__()
        QtWidgets.QMainWindow.__init__(self)
        self.setupUi(self)

        #Setup the tree views
        self.psensorModel = PSensorTreeViewModel()
        self.treeViewPressureSensors.setModel(self.psensorModel)
        self.treeViewPressureSensors.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.shaftModel = ShaftTreeViewModel()
        self.treeViewShafts.setModel(self.shaftModel)
        self.treeViewShafts.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.thermometersModel = ThermometerTreeViewModel()
        self.treeViewThermometers.setModel(self.thermometersModel)
        self.treeViewThermometers.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)    
        self.pointModel = PointTreeViewModel()
        self.treeViewDataPoints.setModel(self.pointModel)
        self.treeViewDataPoints.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)

        #Connect the actions to the appropriate slots
        self.actionImportLabo.triggered.connect(self.importLabo)
        self.actionAboutMolonaViz.triggered.connect(self.aboutUs)
        self.actionOpenUserguideFR.triggered.connect(self.openUserGuideFR)
        self.actionQuitMolonaViz.triggered.connect(self.quitMolonaviz)
        self.actionCreateStudy.triggered.connect(self.createStudy)
        self.actionOpenStudy.triggered.connect(self.chooseStudyName)

        #Some actions or menus should not be enabled: disable them
        self.actionCloseStudy.setEnabled(False)
        self.menuPoint.setEnabled(False)

        #Setup the queue used to display application messages.
        self.messageQueue = Queue()
        sys.stdout = InterceptOutput(self.messageQueue)
        print("MolonaViz - 2022-05-20")

        self.con = None #Connection to the database
        self.currentStudy = None
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
        
    def importLabo(self):
        dlg = DialogImportLab()
        dlg.setWindowModality(QtCore.Qt.ApplicationModal)
        res = dlg.exec_()
        if res == QtWidgets.QDialog.Accepted:
            labdir,labname = dlg.getLaboInfo()
            if labdir and labname: #Both strings are not empty
                lab = Lab(self.con,labname, False, pathToDir = labdir)
                if lab.checkIntegrity():
                    lab.addToDatabase()
                else:
                    displayCriticalMessage("Something went wrong when creating the laboratory, and it wasn't added to the database.\nPlease make sure a laboratory with the same name is not already in the database.")
    
    def createStudy(self):
        """
        Display a dialog so the user may create a study. Then, open this study.
        """
        study_name, study_lab = tryCreateStudy(self.con)
        if study_name and study_lab:#Theses strings are not empty: create the corresponding study
            createStudyDatabase(self.con,study_name,study_lab)
            self.openStudy(study_name)
    
    def chooseStudyName(self):
        """
        Display a dialog so the user may choose a study to open, or display an error message. Then, open a study (by calling self.openStudy).
        """
        study_name = tryOpenStudy(self.con)
        if study_name: #study_name is not an empty string: we should open the corresponding Study.
            self.openStudy(study_name)
    
    def openStudy(self, studyName):
        """
        Given a VALID name of a study, open it.
        """
        self.currentStudy = Study(self.con,studyName)
        #Set the tree models
        for thermo in self.currentStudy.lab.thermometers:
            self.thermometersModel.add_data(thermo)
        for psensor in self.currentStudy.lab.psensors:
            self.psensorModel.add_data(psensor)
        for shaft in self.currentStudy.lab.shafts:
            self.shaftModel.add_data(shaft)
        for point in self.currentStudy.points:
            self.pointModel.add_data(point)
        
        #Enable previously disabled actions, such as the menu used to manage points
        self.actionCreateStudy.setEnabled(False)
        self.actionOpenStudy.setEnabled(False)
        self.actionCloseStudy.setEnabled(True)
        self.menuPoint.setEnabled(True)
        self.actionImportPoint.setEnabled(True)
        self.actionOpenPoint.setEnabled(True)
        self.actionRemovePoint.setEnabled(True)

    
    def printApplicationMessage(self,text):
        """
        Method called when a message needs to be displayed (ie a new element was put in self.messageQueue)
        """
        self.textEditApplicationMessages.moveCursor(QtGui.QTextCursor.End)
        self.textEditApplicationMessages.insertPlainText(text)

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

    # Create thread that will be used to display application messages.
    messageThread = QtCore.QThread()
    my_receiver = Receiver(mainWin.messageQueue)
    my_receiver.printMessage.connect(mainWin.printApplicationMessage)
    my_receiver.moveToThread(messageThread)
    messageThread.started.connect(my_receiver.run)
    messageThread.start()

    sys.exit(app.exec_())