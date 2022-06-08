from PyQt5 import QtWidgets, QtGui, QtCore, uic
from PyQt5.QtSql import QSqlDatabase

from queue import Queue
import sys, os.path
from src.Study import Study

from src.dialogAboutUs import DialogAboutUs
from src.dialogOpenDatabase import DialogOpenDatabase
from src.dialogImportLab import DialogImportLab
from src.dialogOpenStudy import tryOpenStudy
from src.dialogCreateStudy import tryCreateStudy
from src.dialogOpenPoint import tryOpenPoint
from src.dialogImportPoint import DialogImportPoint

from src.Laboratory import Lab
from utils.utils import displayCriticalMessage
from utils.utilsQueries import createStudyDatabase
from src.printThread import InterceptOutput, Receiver
from src.MoloTreeViewModels import ThermometerTreeViewModel, PSensorTreeViewModel, ShaftTreeViewModel, PointTreeViewModel

From_MainWindow = uic.loadUiType(os.path.join(os.path.dirname(__file__),"ui","mainwindow.ui"))[0]
class MainWindow(QtWidgets.QMainWindow,From_MainWindow):
    """
    The main window of the Molonaviz application.
    """
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
        self.actionCloseStudy.triggered.connect(self.closeStudy)
        self.actionImportPoint.triggered.connect(self.importPoint)
        self.actionOpenPoint.triggered.connect(self.openPointFromAction)
        self.actionHideShowPoints.triggered.connect(self.changeDockPointsStatus)
        self.actionHideShowSensors.triggered.connect(self.changeDockSensorsStatus)
        self.actionHideShowAppMessages.triggered.connect(self.changeDockAppMessagesStatus)
        self.actionSwitchToTabbedView.triggered.connect(self.switchToTabbedView)
        self.actionSwitchToSubWindowView.triggered.connect(self.switchToSubWindowView)
        self.actionSwitchToCascadeView.triggered.connect(self.switchToCascadeView)

        self.treeViewDataPoints.doubleClicked.connect(self.openPointFromDock)

    
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
        """
        Display a dialog so the user may import a laboratory from a directory. The laboratory is added to the database.
        """
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
        Display a dialog so the user may create a study.The study is added to the database. Then, open this study (by calling self.openStudy)
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
    
    def openStudy(self, studyName : str):
        """
        Given a VALID name of a study, open it.
        """
        #Create the study. This will also create the corresponding Lab, and display the sensors by using the given models.
        self.currentStudy = Study(self.con,studyName, thermoModel=self.thermometersModel, psensorModel=self.psensorModel, shaftModel=self.shaftModel, pointModel=self.pointModel)
        
        #Enable previously disabled actions, such as the menu used to manage points
        self.actionCreateStudy.setEnabled(False)
        self.actionOpenStudy.setEnabled(False)
        self.actionCloseStudy.setEnabled(True)
        self.menuPoint.setEnabled(True)
        self.actionImportPoint.setEnabled(True)
        self.actionOpenPoint.setEnabled(True)
        self.actionRemovePoint.setEnabled(True)
    
    def closeStudy(self):
        """
        Close the current study and revert the app to the initial state.
        """
        self.currentStudy.close() #Close the study and related windows
        self.currentStudy = None #Forget the study        

        #Enable and disable actions so as to go back to go back to the initial state (no study opened)
        self.actionCreateStudy.setEnabled(True)
        self.actionOpenStudy.setEnabled(True)
        self.actionCloseStudy.setEnabled(False)
        self.menuPoint.setEnabled(False)
        self.actionImportPoint.setEnabled(False)
        self.actionOpenPoint.setEnabled(False)
        self.actionRemovePoint.setEnabled(False)
    
    def importPoint(self):
        """
        Display a dialog so that the user may import and add to the database a point.
        This function may only be called if a study is opened, ie if self.currentStudy is not None.
        """
        dlg = DialogImportPoint(self.con, self.currentStudy.ID)
        dlg.setWindowModality(QtCore.Qt.ApplicationModal)
        res = dlg.exec_()
        if res == QtWidgets.QDialog.Accepted:
            name, psensor, shaft, infofile, noticefile, configfile, prawfile, trawfile = dlg.getPointInfo()
            self.currentStudy.importNewPoint(name, psensor, shaft, infofile, noticefile, configfile, prawfile, trawfile)

    def openPointFromAction(self):
        """
        This happens when the user clicks the "Open Point" action. Display a dialog so the user may choose a point to open, or display an error message. Then, open the corresponding point.
        This function may only be called if a study is opened, ie if self.currentStudy is not None. 
        """
        point_name = tryOpenPoint(self.con, self.currentStudy.ID)
        if point_name: #study_name is not an empty string: we should open the corresponding Point.
            self.currentStudy.openPoint(point_name, self.mdiArea)
    
    def openPointFromDock(self):
        """
        This happens when the user double cliks a point from the dock. Open it.
        This function may only be called if a study is opened, ie if self.currentStudy is not None.
        """
        #Get the information with the flag "UserRole": this information is the name of the point (as defined in MoloTreeViewModels).
        pointName = self.treeViewDataPoints.selectedIndexes()[0].data(QtCore.Qt.UserRole)
        if pointName is None:
            #The user clicked on one of the sub-items instead (shaft, pressure sensor...). Get the information from the parent widget.
            pointName = self.treeViewDataPoints.selectedIndexes()[0].parent().data(QtCore.Qt.UserRole)

        self.currentStudy.openPoint(pointName, self.mdiArea)
    
    def switchToTabbedView(self):
        """
        Rearrange the subwindows to display them as tabs.
        """
        self.mdiArea.setViewMode(QtWidgets.QMdiArea.TabbedView)
        self.actionSwitchToTabbedView.setEnabled(False) #Disable this action to show the user it is the display mode currently being used.
        self.actionSwitchToSubWindowView.setEnabled(True)
        self.actionSwitchToCascadeView.setEnabled(True)

    def switchToSubWindowView(self):
        """
        Rearrange the subwindows to display them in a tile pattern.
        """
        self.mdiArea.setViewMode(QtWidgets.QMdiArea.SubWindowView)
        self.mdiArea.tileSubWindows()
        self.actionSwitchToTabbedView.setEnabled(True)
        self.actionSwitchToSubWindowView.setEnabled(False) #Disable this action to show the user it is the display mode currently being used.
        self.actionSwitchToCascadeView.setEnabled(True)

    def switchToCascadeView(self):
        """
        Rearrange the subwindows to display them in a cascade.
        """
        self.mdiArea.setViewMode(QtWidgets.QMdiArea.SubWindowView)
        self.mdiArea.cascadeSubWindows()
        self.actionSwitchToTabbedView.setEnabled(True)
        self.actionSwitchToSubWindowView.setEnabled(True)
        self.actionSwitchToCascadeView.setEnabled(False) #Disable this action to show the user it is the display mode currently being used.
    
    
    def changeDockPointsStatus(self):
        """
        Hide or show the dock displaying the sampling points.
        """
        if self.actionHideShowPoints.isChecked():
            self.dockDataPoints.show()
        else :
            self.dockDataPoints.hide()
    
    def changeDockSensorsStatus(self):
        """
        Hide or show the dock displaying the sensors.
        """
        if self.actionHideShowSensors.isChecked():
            self.dockSensors.show()
        else :
            self.dockSensors.hide()
    
    def changeDockAppMessagesStatus(self):
        """
        Hide or show the dock displaying the application messages.
        """
        if self.actionHideShowAppMessages.isChecked():
            self.dockAppMessages.show()
        else :
            self.dockAppMessages.hide()

    def printApplicationMessage(self, text : str):
        """
        Show in the corresponding dock a message which needs to be displayed. This means that the program called the print() method somewhere.
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
        """
        Display the French user guide in a new window.
        """
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