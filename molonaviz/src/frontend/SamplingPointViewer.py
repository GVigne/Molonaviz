# from dialogcompute import DialogCompute
# from compute import Compute
# from usefulfonctions import *
# 
# from src.Compute import Compute
# from src.MoloModel import  PressureDataModel, TemperatureDataModel, SolvedTemperatureModel, HeatFluxesModel, WaterFluxModel,ParamsDistributionModel
# from src.dialogCleanupMain import DialogCleanupMain
# from src.dialogCompute import DialogCompute
# from utils.utils import convertDates
# from utils.utilsQueries import build_max_depth
import os
import csv
from numpy import nan
from PyQt5 import QtWidgets, QtCore, uic, QtGui
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

from src.Containers import SamplingPoint
from src.backend.SPointCoordinator import SPointCoordinator
from src.backend.Compute import Compute

from src.frontend.GraphViews import PressureView, TemperatureView,UmbrellaView,TempDepthView,TempMapView,AdvectiveFlowView, ConductiveFlowView, TotalFlowView, WaterFluxView, Log10KView, ConductivityView, PorosityView, CapacityView
from src.frontend.dialogExportCleanedMeasures import DialogExportCleanedMeasures
from src.frontend.dialogConfirm import DialogConfirm
from src.frontend.dialogCleanupMain import DialogCleanupMain
from src.frontend.dialogCompute import DialogCompute
from src.utils.utils import convertDates


From_SamplingPointViewer = uic.loadUiType(os.path.join(os.path.dirname(__file__), "ui", "SamplingPointViewer.ui"))[0]

class SamplingPointViewer(QtWidgets.QWidget, From_SamplingPointViewer):
    
    def __init__(self, spointCoordinator : SPointCoordinator, samplingPoint: SamplingPoint):
        # Call constructor of parent classes
        super(SamplingPointViewer, self).__init__()
        QtWidgets.QWidget.__init__(self)

        self.samplingPoint = samplingPoint
        self.coordinator = spointCoordinator
        self.computeEngine = Compute(self.coordinator)

        self.setupUi(self) 

        #This should already be done in the .ui file
        self.checkBoxRawData.setChecked(True)
        self.checkBoxDirectModel.setChecked(True)
        self.radioButtonTherm1.setChecked(True)
        #By default, this widget tries to maximize the size of the boxes, even if they are empty.
        self.splitterVertical.setSizes([QtGui.QGuiApplication.primaryScreen().virtualSize().height(),QtGui.QGuiApplication.primaryScreen().virtualSize().height()])
        self.splitterHorizLeft.setSizes([QtGui.QGuiApplication.primaryScreen().virtualSize().width(),QtGui.QGuiApplication.primaryScreen().virtualSize().width()])
        self.splitterHorizRight.setSizes([QtGui.QGuiApplication.primaryScreen().virtualSize().width(),QtGui.QGuiApplication.primaryScreen().virtualSize().width()])

        #Create all view and link them to the correct models
        self.graphpress = PressureView(self.coordinator.getPressureModel())
        self.graphtemp = TemperatureView(self.coordinator.getTempModel())
        self.waterflux_view = WaterFluxView(self.coordinator.getWaterFluxesModel())
        fluxesModel = self.coordinator.getFluxesModel()
        self.advective_view = AdvectiveFlowView(fluxesModel)
        self.conductive_view = ConductiveFlowView(fluxesModel)
        self.totalflux_view = TotalFlowView(fluxesModel)
        tempMapModel = self.coordinator.getTempMapModel()
        self.umbrella_view = UmbrellaView(tempMapModel)
        self.tempmap_view = TempMapView(tempMapModel)    
        self.depth_view = TempDepthView(tempMapModel)
        paramsDistrModel = self.coordinator.getParamsDistrModel()
        self.logk_view = Log10KView(paramsDistrModel)
        self.conductivity_view = ConductivityView(paramsDistrModel)
        self.porosity_view = PorosityView(paramsDistrModel)
        self.capacity_view = CapacityView(paramsDistrModel)

        #Link the views showing the pressure and temperature measures to the correct layout. 
        toolbar = NavigationToolbar(self.graphpress, self)
        self.pressVBox.addWidget(self.graphpress)
        self.pressVBox.addWidget(toolbar)
        toolbar = NavigationToolbar(self.graphtemp, self)
        self.tempVBox.addWidget(self.graphtemp)
        self.tempVBox.addWidget(toolbar)

        #This allows to create 4 graphs in a square with one vertical and one horizontal splitter.  
        self.splitterHorizLeft.splitterMoved.connect(self.adjustRightSplitter)
        self.splitterHorizRight.splitterMoved.connect(self.adjustLeftSplitter)

        # Link every button to their function
        self.comboBoxSelectLayer.textActivated.connect(self.changeDisplayedParams)
        self.radioButtonTherm1.clicked.connect(self.refreshTempDepthView)
        self.radioButtonTherm2.clicked.connect(self.refreshTempDepthView)
        self.radioButtonTherm3.clicked.connect(self.refreshTempDepthView)      
        self.pushButtonReset.clicked.connect(self.reset)
        self.pushButtonCleanUp.clicked.connect(self.cleanup)
        self.pushButtonCompute.clicked.connect(self.compute)
        self.pushButtonExportMeasures.clicked.connect(self.exportMeasures)
        self.checkBoxRawData.stateChanged.connect(self.checkbox)
        self.pushButtonRefreshBins.clicked.connect(self.refreshbins)
        self.horizontalSliderBins.valueChanged.connect(self.label_update)

        #Prepare all the tabs.
        self.setWidgetInfos()
        self.setInfoTab()
        self.setupCheckboxesQuantiles()
        self.setPressureAndTemperatureTables()
        self.updateAllViews()
    
    def exportMeasures(self):
        """
        Export two .csv files corresponding to the cleaned measures to the location given by the user.
        """
        dlg = DialogExportCleanedMeasures(self.samplingPoint)
        dlg.setWindowModality(QtCore.Qt.ApplicationModal)
        res = dlg.exec()
        if res == QtWidgets.QDialog.Accepted:
            pressPath, tempPath = dlg.getFilesNames()
            pressfile = open(pressPath, 'w')
            presswriter = csv.writer(pressfile)
            presswriter.writerow(["Date", "Differential pressure (m)", "Temperature (K)"])
            tempfile = open(tempPath, 'w')
            tempwriter = csv.writer(tempfile)
            tempwriter.writerow(["Date", "Temperature 1 (K)", "Temperature 2 (K)", "Temperature 3 (K)", "Temperature 4 (K)"])
            
            measures = self.coordinator.allCleanedMeasures()
            for temprow, pressrow in measures:
                presswriter.writerow(pressrow)
                tempwriter.writerow(temprow)
            pressfile.close()
            tempfile.close()
            print("The cleaned measures have been exported successfully.")
    
    def checkbox(self):
        """
        Refresh type of data displayed (raw or processed) when the checkbox changes state.
        """
        self.setPressureAndTemperatureTables()
        self.coordinator.refreshMeasuresPlots(self.checkBoxRawData.isChecked())

    def refreshbins(self):
        bins = self.horizontalSliderBins.value()
        self.logk_view.update_bins(bins)
        self.logk_view.on_update()

        self.conductivity_view.update_bins(bins)
        self.conductivity_view.on_update()

        self.porosity_view.update_bins(bins)
        self.porosity_view.on_update()

        self.capacity_view.update_bins(bins)
        self.capacity_view.on_update()
    
    def label_update(self):
        self.labelBins.setText(str(self.horizontalSliderBins.value()))
    
    def setWidgetInfos(self):
        self.setWindowTitle(self.samplingPoint.name)
        self.lineEditPointName.setText(self.samplingPoint.name)
        self.lineEditSensor.setText(self.samplingPoint.psensor)
        self.lineEditShaft.setText(self.samplingPoint.shaft)

    def setInfoTab(self):
        schemePath, noticePath, infosModel = self.coordinator.getSPointInfos()
        self.labelSchema.setPixmap(QtGui.QPixmap(schemePath))
        self.labelSchema.setAlignment(QtCore.Qt.AlignHCenter)
        #The following lines allow the image to take the entire size of the widget, however it will be misshapen
        # self.labelSchema.setScaledContents(True)
        # self.labelSchema.setSizePolicy(QtWidgets.QSizePolicy.Ignored,QtWidgets.QSizePolicy.Ignored)
        #Notice
        try:
            file = open(noticePath, encoding = "latin-1") #The encoding must allow to read accents
            notice = file.read()
            self.plainTextEditNotice.setPlainText(notice)
        except Exception as e:
            self.plainTextEditNotice.setPlainText("No notice was found")
            
        #Infos
        self.infosModel = infosModel
        self.tableViewInfos.setModel(self.infosModel)
    
    def setupComboBoxLayers(self):
        """
        Setup the Combo box and which will be used to display the parameters.
        """
        layers = self.coordinator.layersDepths()
        for layer in layers:
            self.comboBoxSelectLayer.addItem(str(layer))
        if len(layers) > 0:
            self.changeDisplayedParams(layers[0])    

    def changeDisplayedParams(self, layer : float):
        """
        Display in the table view the parameters corresponding to the given layer, and update histograms.
        """
        self.paramsModel = self.coordinator.getParamsModel(layer)
        self.tableViewParams.setModel(self.paramsModel)
        #Resize the table view so it looks pretty
        self.tableViewParams.resizeColumnsToContents()
        self.coordinator.refreshParamsDistr(layer)
    
    def setupCheckboxesQuantiles(self):
        """
        Display as many checkboxes as there are quantiles in the database, along with the associated RMSE.
        """
        self.checkBoxDirectModel.stateChanged.connect(self.refreshTempDepthView)

        globalRMSE, thermRMSE = self.coordinator.allRMSE()
        i = 1
        for index, (quantile, rmse) in enumerate(globalRMSE.items()):
            if quantile !=0:
                #Value 0 is already hardcoded in the .ui file
                text_checkbox = f"Quantile {quantile}"
                quantile_checkbox = QtWidgets.QCheckBox(text_checkbox)
                quantile_checkbox.stateChanged.connect(self.refreshTempDepthView)
                self.quantilesLayout.addWidget(quantile_checkbox,i,0)
                self.quantilesLayout.addWidget(QtWidgets.QLabel(f"RMSE: {rmse:.2f} °C"),i,1)
                i +=1

        #Display the RMSE for each thermometer or 0 if it has not been computed yet (ie select_RMSE_therm has only None values)
        self.labelRMSETherm1.setText(f"RMSE: {thermRMSE[0] if thermRMSE[0] else 0:.2f} °C")
        self.labelRMSETherm2.setText(f"RMSE: {thermRMSE[1] if thermRMSE[1] else 0:.2f} °C")
        self.labelRMSETherm3.setText(f"RMSE: {thermRMSE[2] if thermRMSE[2] else 0:.2f} °C")
    
    def refreshTempDepthView(self):
        """
        This method is called when a checkbox showing a quantile or a radio buttion is changed. New curves should be plotted in the Temperature per Depth View.
        """
        #Needs to be adapted!
        quantiles = []
        for i in range (self.quantilesLayout.count()):
            checkbox = self.quantilesLayout.itemAt(i).widget()
            if isinstance(checkbox, QtWidgets.QCheckBox):
                if checkbox.isChecked():
                    txt = checkbox.text()
                    #A bit ugly but it works
                    if txt == "Direct model":
                        quantiles.append(0)
                    else:
                        #txt is "Quantile ... "
                        quantiles.append(float(txt[8:]))
        depth_id = 0
        if self.radioButtonTherm1.isChecked():
            depth_id = 1
        elif self.radioButtonTherm2.isChecked():
            depth_id = 2
        elif self.radioButtonTherm3.isChecked():
            depth_id = 3

        thermo_depth = self.coordinator.thermoDepth(depth_id)
        self.depth_view.update_options([thermo_depth,quantiles])
        self.depth_view.on_update() #Refresh the view
    
    def setPressureAndTemperatureTables(self):
        """
        Set the two tables giving direct information from the database.
        """
        # Set the Temperature and Pressure arrays
        self.currentDataModel = self.coordinator.getTableModel(self.checkBoxRawData.isChecked())
        self.tableViewDataArray.setModel(self.currentDataModel)
        #Resize the table view so it looks pretty
        self.tableViewDataArray.resizeColumnsToContents()
        width = self.tableViewDataArray.verticalHeader().width()
        for i in range(self.tableViewDataArray.model().rowCount()):
            width += self.tableViewDataArray.columnWidth(i)
        width +=20 #Approximate width of the splitter bar
        self.tableViewDataArray.setFixedWidth(width)
    
    def updateAllViews(self):
        """
        Update all the views displaying results by asking the backend to refresh the models.
        """
        self.comboBoxSelectLayer.clear()
        self.setupComboBoxLayers()

        self.setPressureAndTemperatureTables()

        self.clearAllLayouts()
        if self.coordinator.computation_type() is not None:
            self.linkViewsLayouts()
        else:
             self.linkLayoutsNoComputations()

        thermo_depth = self.coordinator.thermoDepth(1)
        options = [thermo_depth, [0]] #First thermometer, direct model
        self.depth_view.update_options(options)

        self.coordinator.refreshAllModels(self.checkBoxRawData.isChecked(), self.comboBoxSelectLayer.currentText())

    def clearAllLayouts(self):
        """
        Clear all vertical layouts in the widget point window except for the "Data array and plots" tab, as these should always contain a view (either raw or cleaned measures).
        """
        layouts = [self.waterFluxVBox, self.advectiveFluxVBox, self.totalFluxVBox, self.conductiveFluxVBox, self.topRightVLayout, self.botLeftVLayout, self.botRightVLayout, self.log10KVBox, self.conductivityVBox, self.porosityVBox, self.capacityVBox]
        for layout in layouts:
            #Taken from Stack Overflow
            for i in reversed(range(layout.count())):
                layout.itemAt(i).widget().setParent(None)
    
    def linkLayoutsNoComputations(self):
        """
        Fill all vertical layouts with a message saying no model has been computed, except for those "Data array and plots" tab as these should always contain a view (either raw or cleaned measures).
        """
        layouts = [self.waterFluxVBox, self.advectiveFluxVBox, self.totalFluxVBox, self.conductiveFluxVBox, self.topRightVLayout, self.botLeftVLayout, self.botRightVLayout, self.log10KVBox, self.conductivityVBox, self.porosityVBox, self.capacityVBox]
        for layout in layouts:
            label = QtWidgets.QLabel("No model has been computed yet")
            layout.addWidget(label, QtCore.Qt.AlignCenter)
    
    def linkViewsLayouts(self):
        """
        Fill all the vertical layouts with the correct view.
        """
        layoutsviews = [[self.waterFluxVBox,self.waterflux_view],
                        [self.advectiveFluxVBox,self.advective_view],
                        [self.conductiveFluxVBox, self.conductive_view],
                        [self.totalFluxVBox, self.totalflux_view],
                        [self.topRightVLayout, self.depth_view],
                        [self.botLeftVLayout, self.umbrella_view],
                        [self.botRightVLayout, self.tempmap_view],
                        [self.log10KVBox, self.logk_view],
                        [self.conductivityVBox, self.conductivity_view],
                        [self.porosityVBox, self.porosity_view],
                        [self.capacityVBox, self.capacity_view]]

        for layout, view in layoutsviews:
            toolbar = NavigationToolbar(view, self)
            layout.addWidget(view)
            layout.addWidget(toolbar)
    
    def reset(self):
        dlg = DialogConfirm("Are you sure you want to delete the cleaned measures and all computations made for this point? This cannot be undone.")
        res = dlg.exec()
        if res == QtWidgets.QDialog.Accepted:
            self.coordinator.deleteProcessedData()
            self.updateAllViews()
    
    def cleanup(self):
        dlg = DialogCleanupMain(self.coordinator,self.samplingPoint)
        res = dlg.exec()
        if res == QtWidgets.QDialog.Accepted:
            confirm = DialogConfirm("Cleaning up the measures will delete the previous cleanup, as well as any computations made for this point. Are you sure?")
            confirmRes = confirm.exec()
            if confirmRes == QtWidgets.QDialog.Accepted:
                #Clean the database first before putting new data
                self.coordinator.deleteProcessedData()

                dlg.df_cleaned["date"].replace('', nan, inplace = True)
                dlg.df_cleaned.dropna(subset = ["date"], inplace = True)
                convertDates(dlg.df_cleaned) #Convert the dates to database format
                dlg.df_cleaned["date"] = dlg.df_cleaned["date"].dt.strftime("%Y/%m/%d %H:%M:%S")

                self.coordinator.insertCleanedMeasures(dlg.df_cleaned)

                self.updateAllViews()
    
    def compute(self):
        dlg = DialogCompute(self.coordinator.maxDepth())
        res = dlg.exec()
        if res == QtWidgets.QDialog.Accepted:
            self.coordinator.deleteComputations()
            if dlg.computationIsMCMC():
                #MCMC
                self.computeEngine.MCMCFinished.connect(self.updateAllViews)
                nb_iter, all_priors, nb_cells, quantiles = dlg.getInputMCMC()
                self.computeEngine.computeMCMC(nb_iter, all_priors, nb_cells, quantiles)
            else:
                #Direct Model
                self.computeEngine.DirectModelFinished.connect(self.updateAllViews)
                params, nb_cells = dlg.getInputDirectModel()
                self.computeEngine.computeDirectModel(params, nb_cells)


    def adjustRightSplitter(self, pos : int, index : int):
        """
        This is called when the left horizontal splitter is moved. Move the right one accordingly.
        """
        self.splitterHorizRight.setSizes(self.splitterHorizLeft.sizes())
    
    def adjustLeftSplitter(self, pos : int, index : int):
        """
        This is called when the right horizontal splitter is moved. Move the left one accordingly.
        """
        self.splitterHorizLeft.setSizes(self.splitterHorizRight.sizes())