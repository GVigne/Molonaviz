# from dialogcleanupmain import DialogCleanupMain
# from dialogcompute import DialogCompute
# from compute import Compute
# from usefulfonctions import *

from math import isnan
from numpy import nan
import os
import csv
from PyQt5 import QtWidgets, QtCore, uic
from PyQt5 import QtGui
from PyQt5.QtSql import QSqlQueryModel, QSqlQuery, QSqlDatabase #QSqlDatabase in used only for type hints
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from src.dialogExportCleanedMeasures import DialogExportCleanedMeasures
from src.Containers import Point
from src.Compute import Compute
from src.MoloModel import  PressureDataModel, TemperatureDataModel, SolvedTemperatureModel, HeatFluxesModel, WaterFluxModel,ParamsDistributionModel
from src.MoloView import PressureView, TemperatureView,UmbrellaView,TempDepthView,TempMapView,AdvectiveFlowView, ConductiveFlowView, TotalFlowView, WaterFluxView, Log10KView, ConductivityView, PorosityView, CapacityView
from src.dialogCleanupMain import DialogCleanupMain
from src.dialogConfirm import DialogConfirm
from src.dialogCompute import DialogCompute
from utils.utils import convertDates
from utils.utilsQueries import build_max_depth

From_WidgetPoint = uic.loadUiType(os.path.join(os.path.dirname(__file__), "..", "ui", "widgetPoint.ui"))[0]

class WidgetPoint(QtWidgets.QWidget, From_WidgetPoint):
    
    def __init__(self, con : QSqlDatabase, samplingPoint: Point, samplingPointID : int | str):
        # Call constructor of parent classes
        super(WidgetPoint, self).__init__()
        QtWidgets.QWidget.__init__(self)
        
        self.setupUi(self)        
        self.samplingPoint = samplingPoint
        self.samplingPointID = samplingPointID #The ID of the point being opened
        self.con = con
        self.pointID = self.getOrCreatePointID()
        self.computeEngine = Compute(self.con, self.pointID)
        
        #This should already be done in the .ui file
        self.checkBoxRawData.setChecked(True)
        self.checkBoxDirectModel.setChecked(True)
        self.radioButtonTherm1.setChecked(True)
        #By default, this widget tries to maximize the size of the boxes, even if they are empty.
        self.splitterVertical.setSizes([QtGui.QGuiApplication.primaryScreen().virtualSize().height(),QtGui.QGuiApplication.primaryScreen().virtualSize().height()])
        self.splitterHorizLeft.setSizes([QtGui.QGuiApplication.primaryScreen().virtualSize().width(),QtGui.QGuiApplication.primaryScreen().virtualSize().width()])
        self.splitterHorizRight.setSizes([QtGui.QGuiApplication.primaryScreen().virtualSize().width(),QtGui.QGuiApplication.primaryScreen().virtualSize().width()])

        #Create all models and related views: they are empty for now
        self.pressuremodel = PressureDataModel([])
        self.tempmodel = TemperatureDataModel([])
        self.tempmap_model = SolvedTemperatureModel([])
        self.fluxes_model = HeatFluxesModel([])
        self.waterflux_model = WaterFluxModel([])
        self.paramsdistr_model = ParamsDistributionModel([])

        self.graphpress = PressureView(self.pressuremodel)
        self.graphtemp = TemperatureView(self.tempmodel)
        self.waterflux_view = WaterFluxView(self.waterflux_model)
        self.advective_view = AdvectiveFlowView(self.fluxes_model)
        self.conductive_view = ConductiveFlowView(self.fluxes_model)
        self.totalflux_view = TotalFlowView(self.fluxes_model)
        self.umbrella_view = UmbrellaView(self.tempmap_model)
        self.tempmap_view = TempMapView(self.tempmap_model)      
        self.depth_view = TempDepthView(self.tempmap_model)
        self.logk_view = Log10KView(self.paramsdistr_model)
        self.conductivity_view = ConductivityView(self.paramsdistr_model)
        self.porosity_view = PorosityView(self.paramsdistr_model)
        self.capacity_view = CapacityView(self.paramsdistr_model)

        #Link the views showing the pressure and temperature measures to the correct layout. 
        toolbar = NavigationToolbar(self.graphpress, self)
        self.pressVBox.addWidget(self.graphpress)
        self.pressVBox.addWidget(toolbar)
        toolbar = NavigationToolbar(self.graphtemp, self)
        self.tempVBox.addWidget(self.graphtemp)
        self.tempVBox.addWidget(toolbar)

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

        #Prepare all the tabs and the views.
        self.setInfoTab()
        self.setWidgetInfos()
        self.setupComboBoxLayers()
        self.setupCheckboxesQuantiles()
        self.setPressureAndTemperatureModels()
        self.updateAllModels()
    
    def getOrCreatePointID(self):
        """
        Return the Point ID corresponding to this point OR if this is the first time this point is opened, create the relevant entry in the Point table.
        """
        select_pointID = self.build_select_point_ID()
        select_pointID.exec()
        select_pointID.next()
        if select_pointID.value(0) is None:
            insertPoint = self.build_insert_point()
            insertPoint.bindValue(":SamplingPoint", self.samplingPointID)
            insertPoint.exec()
            return insertPoint.lastInsertId()
        return select_pointID.value(0)

    def setInfoTab(self):
        select_paths, select_infos = self.build_infos_queries()
        #Installation image
        select_paths.exec()
        select_paths.next()
        self.labelSchema.setPixmap(QtGui.QPixmap(select_paths.value(0))) 
        self.labelSchema.setAlignment(QtCore.Qt.AlignHCenter)
        #This allows the image to take the entire size of the widget, however it will be misshapen
        # self.labelSchema.setScaledContents(True)
        # self.labelSchema.setSizePolicy(QtWidgets.QSizePolicy.Ignored,QtWidgets.QSizePolicy.Ignored)
        #Notice
        try:
            file = open(select_paths.value(1), encoding = "latin-1") #The encoding must allow to read accents
            notice = file.read()
            self.plainTextEditNotice.setPlainText(notice)
        except Exception as e:
            self.plainTextEditNotice.setPlainText("No notice was found")
            
        #Infos
        select_infos.exec()
        self.infosModel = QSqlQueryModel()
        self.infosModel.setQuery(select_infos)
        self.tableViewInfos.setModel(self.infosModel)

    def setupComboBoxLayers(self):
        """
        Setup the Combo box and which will be used to display the parameters.
        If no layer is in the database, then the warning "QSqlQuery::value: not positioned on a valid record" will be raised, and nothing will be added to the combo box.
        """
        select_depths_layers = self.build_layers_query()
        select_depths_layers.exec()
        first_layer = True
        while select_depths_layers.next():
            if first_layer:
                self.changeDisplayedParams(select_depths_layers.value(0))
                first_layer = False
            self.comboBoxSelectLayer.addItem(str(select_depths_layers.value(0)))
    
    def changeDisplayedParams(self,layer):
        """
        Display in the table view the parameters corresponding to the given layer, and update histograms.
        """
        select_params = self.build_params_query(layer)
        select_params.exec()
        self.paramsModel = QSqlQueryModel()
        self.paramsModel.setQuery(select_params)
        self.tableViewParams.setModel(self.paramsModel)

        #Resize the table view so it looks pretty
        self.tableViewParams.resizeColumnsToContents()
        
        try:
            select_params = self.build_params_distribution(layer)
            self.paramsdistr_model.new_queries([select_params])
            self.paramsdistr_model.exec() #Refresh the model
        except Exception:
            #self.paramsdistr_model is not initialised yet. This "feature" can only occur if there were no histograms (for instance only cleaned measures) and we switch to a database with histograms (example: via the update_all_models method)
            pass

    
    def setupCheckboxesQuantiles(self):
        """
        Display as many checkboxes as there are quantiles in the database, along with the associated RMSE.
        """
        self.checkBoxDirectModel.stateChanged.connect(self.refreshTempDepthView)

        select_quantiles = self.build_global_RMSE_query()
        select_quantiles.exec()
        i=1
        while select_quantiles.next():
            if select_quantiles.value(1) !=0:
                #Value 0 is already hardcoded in the .ui file
                text_checkbox = f"Quantile {select_quantiles.value(1)}"
                quantile_checkbox = QtWidgets.QCheckBox(text_checkbox)
                quantile_checkbox.stateChanged.connect(self.refreshTempDepthView)
                self.quantilesLayout.addWidget(quantile_checkbox,i,0)
                self.quantilesLayout.addWidget(QtWidgets.QLabel(f"RMSE: {select_quantiles.value(0):.2f} °C"),i,1)
                i +=1

        select_RMSE_therm = self.build_therm_RMSE()
        select_RMSE_therm.exec()
        select_RMSE_therm.next()
        #Display the RMSE for each thermometer or 0 if it has not been computed yet (ie select_RMSE_therm has only None values)
        self.labelRMSETherm1.setText(f"RMSE: {select_RMSE_therm.value(0) if select_RMSE_therm.value(0) else 0:.2f} °C")
        self.labelRMSETherm2.setText(f"RMSE: {select_RMSE_therm.value(1) if select_RMSE_therm.value(1) else 0:.2f} °C")
        self.labelRMSETherm3.setText(f"RMSE: {select_RMSE_therm.value(2) if select_RMSE_therm.value(2) else 0:.2f} °C")

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
            
            select_data = self.build_cleaned_measures(full_query=True)
            select_data.exec()
            while select_data.next():
                presswriter.writerow([select_data.value(0), select_data.value(6),select_data.value(5)])
                tempwriter.writerow([select_data.value(i) for i in range(5)])
            pressfile.close()
            tempfile.close()
            print("The cleaned measures have been exported successfully.")

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
        select_thermo_depth = self.build_thermo_depth(depth_id)
        select_thermo_depth.exec()
        select_thermo_depth.next()

        self.depth_view.update_options([select_thermo_depth.value(0),quantiles])
        self.depth_view.on_update() #Refresh the view

    def setPressureAndTemperatureModels(self):
        # Set the Temperature and Pressure arrays
        if self.checkBoxRawData.isChecked():
            select_query = self.build_raw_measures(full_query=True)
        else:
            select_query = self.build_cleaned_measures(full_query=True)
        select_query.exec()
        self.currentDataModel = QSqlQueryModel()
        self.currentDataModel.setQuery(select_query)
        self.tableViewDataArray.setModel(self.currentDataModel)
        #Resize the table view so it looks pretty
        self.tableViewDataArray.resizeColumnsToContents()
        width = self.tableViewDataArray.verticalHeader().width()
        for i in range(self.tableViewDataArray.model().rowCount()):
            width += self.tableViewDataArray.columnWidth(i)
        width +=20 #Approximate width of the splitter bar
        self.tableViewDataArray.setFixedWidth(width)


    def setWidgetInfos(self):
        self.setWindowTitle(self.samplingPoint.name)
        self.lineEditPointName.setText(self.samplingPoint.name)
        self.lineEditSensor.setText(self.samplingPoint.psensor)
        self.lineEditShaft.setText(self.samplingPoint.shaft)
    
    def checkbox(self):
        """
        Refresh type of data displayed (raw or processed) when the checkbox changes state.
        """
        self.setPressureAndTemperatureModels()

        if self.checkBoxRawData.isChecked():
            select_pressure = self.build_raw_measures(field ="Pressure")
            select_temp = self.build_raw_measures(field ="Temp")
        else:
            select_pressure = self.build_cleaned_measures(field ="Pressure")
            select_temp = self.build_cleaned_measures(field ="Temp")

        self.pressuremodel.new_queries([select_pressure])
        self.pressuremodel.exec()

        self.tempmodel.new_queries([select_temp])
        self.tempmodel.exec()

    def reset(self):
        dlg = DialogConfirm("Are you sure you want to delete the cleaned measures and all computations made for this point? This cannot be undone.")
        res = dlg.exec()
        if res == QtWidgets.QDialog.Accepted:
            self.deleteComputations()
            self.deleteCleanedAndDates()
            self.refreshModels()

    def cleanup(self):
        dlg = DialogCleanupMain(self.con,self.samplingPoint, self.samplingPointID)
        res = dlg.exec()
        if res == QtWidgets.QDialog.Accepted:
            confirm = DialogConfirm("Cleaning up the measures will delete the previous cleanup, as well as any computations made for this point. Are you sure?")
            confirmRes = confirm.exec()
            if confirmRes == QtWidgets.QDialog.Accepted:
                #Clean the database first before putting new data
                self.deleteComputations()
                self.deleteCleanedAndDates()

                dlg.df_cleaned["date"].replace('', nan, inplace = True)
                dlg.df_cleaned.dropna(subset = ["date"], inplace = True)
                convertDates(dlg.df_cleaned) #Convert the dates to database format
                dlg.df_cleaned["date"] = dlg.df_cleaned["date"].dt.strftime("%Y/%m/%d %H:%M:%S")

                query_dates = self.build_insert_date()
                query_dates.bindValue(":PointKey", self.pointID)

                query_measures = self.build_insert_cleaned_measures()
                query_measures.bindValue(":PointKey", self.pointID)
                
                self.con.transaction()
                for row in dlg.df_cleaned.itertuples():
                    if not(isnan(row[2]) or isnan(row[3]) or isnan(row[4]) or isnan(row[5]) or isnan(row[6]) or isnan(row[7])):
                        query_dates.bindValue(":Date", row[1])
                        query_dates.exec()
                        query_measures.bindValue(":DateID", query_dates.lastInsertId())
                        query_measures.bindValue(":TempBed", row[2])
                        query_measures.bindValue(":Temp1", row[4])
                        query_measures.bindValue(":Temp2", row[5])
                        query_measures.bindValue(":Temp3", row[6])
                        query_measures.bindValue(":Temp4", row[7])
                        query_measures.bindValue(":Pressure", row[3])
                        query_measures.exec()
                self.con.commit()

                self.refreshModels()


    def compute(self):
        selectdepth = build_max_depth(self.con, self.samplingPointID)
        selectdepth.exec()
        selectdepth.next()
        dlg = DialogCompute(selectdepth.value(0))
        res = dlg.exec()
        if res == QtWidgets.QDialog.Accepted:
            self.deleteComputations()
            if dlg.computationIsMCMC():
                #MCMC
                self.computeEngine.MCMCFinished.connect(self.refreshModels)
                nb_iter, all_priors, nb_cells, quantiles = dlg.getInputMCMC()
                self.computeEngine.computeMCMC(nb_iter, all_priors, nb_cells, quantiles)
            else:
                #Direct Model
                self.computeEngine.DirectModelFinished.connect(self.refreshModels)
                params, nb_cells = dlg.getInputDirectModel()
                self.computeEngine.computeDirectModel(params, nb_cells)

    def refreshbins(self):
        try:
            bins = self.horizontalSliderBins.value()
            self.logk_view.update_bins(bins)
            self.logk_view.on_update()

            self.conductivity_view.update_bins(bins)
            self.conductivity_view.on_update()

            self.porosity_view.update_bins(bins)
            self.porosity_view.on_update()

            self.capacity_view.update_bins(bins)
            self.capacity_view.on_update()
        except Exception:
            #The views don't exist yet: computations have not been made. The button should be inactive
            pass
    
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

    def updateAllModels(self):
        """
        Update all the models displaying results by refreshing the queries in the database.
        """
        #Always refresh the measures
        #Pressure measures
        if self.checkBoxRawData.isChecked():
            select_pressure = self.build_raw_measures(field ="Pressure")
        else:
            select_pressure = self.build_cleaned_measures(field ="Pressure")
        self.pressuremodel.new_queries([select_pressure])
        self.pressuremodel.exec()
        #Temperature measures
        if self.checkBoxRawData.isChecked():
            select_temp = self.build_raw_measures(field ="Temp")
        else:
            select_temp = self.build_cleaned_measures(field ="Temp")
        self.tempmodel.new_queries([select_temp])
        self.tempmodel.exec()
        
        self.clearAllLayouts()
        if self.computation_type() is not None:
            #Plot the heat fluxes
            select_heatfluxes= self.build_result_queries(result_type="2DMap",option="HeatFlows") #This is a list
            select_depths = self.build_depths()
            select_dates = self.build_dates()
            self.fluxes_model.new_queries([select_dates,select_depths]+select_heatfluxes)
            self.fluxes_model.exec()

            #Plot the water fluxes
            select_waterflux= self.build_result_queries(result_type="WaterFlux") #This is already a list
            self.waterflux_model.new_queries(select_waterflux)
            self.waterflux_model.exec()

            #Plot the temperatures
            select_tempmap = self.build_result_queries(result_type="2DMap",option="Temperature") #This is a list of temperatures for all quantiles
            select_depths = self.build_depths()
            select_dates = self.build_dates()
            self.tempmap_model.new_queries([select_dates,select_depths]+select_tempmap)
        
            sel_depth = self.build_thermo_depth(1)
            sel_depth.exec()
            sel_depth.next()
            options = [sel_depth.value(0), [0]] #First thermometer, direct model
            self.depth_view.update_options(options)
            self.tempmap_model.exec()

            #Histogramms
            select_params = self.build_params_distribution(self.comboBoxSelectLayer.currentText())
            self.paramsdistr_model.new_queries([select_params])
            self.paramsdistr_model.exec()

            #Show the views in the corresponding layouts
            self.linkViewsLayouts()
        else:
            self.linkLayoutsNoComputations()
       

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

    def label_update(self):
        self.labelBins.setText(str(self.horizontalSliderBins.value()))
    
    def refreshModels(self):
        """
        Refresh all existing models. This is mostly redundant with updateAllModels: this function should be fused with updateAllModels when making the clear separation backend/frontend.
        """
        self.comboBoxSelectLayer.clear()
        self.setupComboBoxLayers()

        self.setPressureAndTemperatureModels()
        self.updateAllModels()
    
    def deleteComputations(self):
        """
        Delete every computations made for this point. This function builds and execute the DELETE queries. Be careful, calling it will clear the database for this point!
        """
        deleteTableQuery = QSqlQuery(self.con)
        #Careful: should have joins as WaterFlow.PointKey !=Samplingpoint.name
        deleteTableQuery.exec(f'DELETE FROM WaterFlow WHERE WaterFlow.PointKey=(SELECT Point.ID FROM Point WHERE Point.ID ={self.pointID})')
        deleteTableQuery.exec(f'DELETE FROM RMSE WHERE PointKey=(SELECT Point.ID FROM Point WHERE Point.ID ={self.pointID})')
        deleteTableQuery.exec(f'DELETE FROM TemperatureAndHeatFlows WHERE PointKey=(SELECT Point.ID FROM Point WHERE Point.ID  = {self.pointID})')
        deleteTableQuery.exec(f'DELETE FROM ParametersDistribution WHERE ParametersDistribution.PointKey=(SELECT Point.ID FROM Point WHERE Point.ID = {self.pointID})')
        deleteTableQuery.exec(f'DELETE FROM BestParameters WHERE BestParameters.PointKey=(SELECT Point.ID FROM Point WHERE Point.ID = {self.pointID})')
        deleteTableQuery.exec(f'DELETE FROM Quantiles WHERE Quantiles.PointKey=(SELECT Point.ID FROM Point WHERE Point.ID = {self.pointID})')
        deleteTableQuery.exec(f'DELETE FROM Depth WHERE Depth.PointKey=(SELECT Point.ID FROM Point WHERE Point.ID = {self.pointID})')
        deleteTableQuery.exec(f'DELETE FROM Layer WHERE Layer.PointKey=(SELECT Point.ID FROM Point WHERE Point.ID = {self.pointID})')
        deleteTableQuery.exec(f'DELETE FROM Quantile WHERE Quantile.PointKey=(SELECT Point.ID FROM Point WHERE Point.ID = {self.pointID})')
        deleteTableQuery.exec(f"""UPDATE Point
                        SET IncertK = NULL,
                            IncertLambda = NULL,
                            DiscretStep = NULL,
                            IncertRho = NULL,
                            TempUncertainty = NULL,
                            IncertPressure = NULL
                        WHERE ID = {self.pointID}""")

    def deleteCleanedAndDates(self):
        """
        Delete the cleaned measures made for this point as well as the dates. This function builds and execute the DELETE queries. Be careful, calling it will clear the database for this point!
        """
        dateID = QSqlQuery(self.con)
        dateID.exec(f"""SELECT Date.ID FROM DATE
                        JOIN Point
                        ON Date.PointKey = Point.ID
                        WHERE Point.ID={self.pointID}""")
        deleteTableQuery = QSqlQuery(self.con)
        deleteTableQuery.exec(f"DELETE FROM CleanedMeasures WHERE CleanedMeasures.PointKey=(SELECT ID FROM Point WHERE Point.ID={self.pointID})")
        deleteDate = QSqlQuery(self.con)

        deleteDate.prepare("DELETE FROM Date WHERE Date.ID = :Date")
        self.con.transaction()
        while dateID.next():
            deleteDate.bindValue(":Date", dateID.value(0))
            deleteDate.exec()
        self.con.commit()

    def build_select_point_ID(self):
        """
        Build and return a query giving the ID of the Point corresponding to the current sampling point
        """
        query = QSqlQuery(self.con)
        query.prepare(f"""
            SELECT Point.ID FROM Point
            JOIN SamplingPoint
            ON Point.SamplingPoint = SamplingPoint.ID
            WHERE SamplingPoint.ID = {self.samplingPointID}
        """)
        return query
    
    def build_insert_point(self):
        """
        Build and return a query creating a Point. For now, most fields are empty.
        """
        query = QSqlQuery(self.con)
        query.prepare(f""" INSERT INTO Point (SamplingPoint)  VALUES (:SamplingPoint)
        """)
        return query

    def build_infos_queries(self):
        """
        Build and return two queries for the info tab:
        -one to get the configuration image of the sampling point and the notice. Theses are paths.
        -one to get the rest of the information of the sampling point.
        """
        paths = QSqlQuery(self.con)
        paths.prepare(f"""
            SELECT SamplingPoint.Scheme, SamplingPoint.Notice FROM SamplingPoint 
            WHERE SamplingPoint.ID = '{self.samplingPointID}' 
        """)

        infos = QSqlQuery(self.con)
        infos.prepare(f"""
            SELECT SamplingPoint.Name, SamplingPoint.Setup, SamplingPoint.LastTransfer, SamplingPoint.Offset, SamplingPoint.RiverBed FROM SamplingPoint 
            WHERE SamplingPoint.ID = '{self.samplingPointID}' 
        """)
        return paths, infos

    def build_layers_query(self):
        """
        Build and return a query giving the depths of all the layers.
        """
        query = QSqlQuery(self.con)
        query.prepare(f"""
            SELECT Layer.Depth FROM Layer 
            JOIN Point
            ON Layer.PointKey = Point.ID
            WHERE Point.ID = {self.pointID} 
            ORDER BY Layer.Depth 
        """)
        return query
    
    def build_params_query(self, depth : float | str):
        """
        Build and return the parameters for the given depth.
        """
        query = QSqlQuery(self.con)
        query.prepare(f"""
            SELECT BestParameters.Permeability, BestParameters.ThermConduct, BestParameters.Porosity, BestParameters.Capacity FROM BestParameters 
            JOIN Layer ON BestParameters.Layer = Layer.ID
            JOIN Point
            ON BestParameters.PointKey = Point.ID
            WHERE Point.ID = {self.pointID}
            AND Layer.Depth = {depth}
        """)
        return query
    
    def build_global_RMSE_query(self):
        """
        Build and return all the quantiles as well as the associated global RMSE.
        """
        query = QSqlQuery(self.con)
        query.prepare(f"""
            SELECT RMSE.RMSETotal, Quantile.Quantile FROM RMSE 
            JOIN Quantile
            ON RMSE.Quantile = Quantile.ID
            JOIN Point
            ON Quantile.PointKey = Point.ID
            WHERE Point.ID = {self.pointID}
            ORDER BY Quantile.Quantile
        """)
        return query
    
    def build_therm_RMSE(self):
        """
        Build and return the RMSE for the three thermometers.
        """
        query = QSqlQuery(self.con)
        query.prepare(f"""
            SELECT RMSE1, RMSE2, RMSE3 FROM RMSE 
            JOIN Quantile
            ON RMSE.Quantile = Quantile.ID
            JOIN Point
            ON Quantile.PointKey = Point.ID
            WHERE Point.ID = {self.pointID}
            AND Quantile.Quantile = 0
        """)
        return query
    
    def build_quantiles(self):
        """
        Build and return the quantiles values.
        """
        query = QSqlQuery(self.con)
        query.prepare(f"""
            SELECT Quantile.Quantile FROM Quantile
            JOIN Point
            ON Quantile.PointKey = Point.ID
            WHERE Point.ID = {self.pointID}
            ORDER BY Quantile.Quantile  
        """)
        return query
    
    def build_depths(self):
        """
        Build and return all the depths values.
        """
        query = QSqlQuery(self.con)
        query.prepare(f"""
            SELECT Depth.Depth FROM Depth
            JOIN Point
            ON Depth.PointKey = Point.ID
            WHERE Point.ID = {self.pointID}
            ORDER BY Depth.Depth  
        """)
        return query
        
    def build_dates(self):
        """
        Build and return all the dates for this point.
        """
        query = QSqlQuery(self.con)
        query.prepare(f"""
            SELECT Date.Date FROM Date 
            JOIN Point
            ON Date.PointKey = Point.ID
            WHERE Point.ID = {self.pointID}
            ORDER by Date.Date   
        """)
        return query
    
    def build_thermo_depth(self, id : int):
        """
        Given an integer (1,2 or 3), return the associated depth of the thermometer.
        """
        if id in [1,2,3]:
            field = f"Depth{id}"
            query = QSqlQuery(self.con)
            query.prepare(f"""
                SELECT Depth.Depth FROM Depth
                JOIN RMSE
                ON Depth.ID = RMSE.{field} 
                JOIN Point
                ON RMSE.PointKey = Point.ID 
                WHERE Point.ID = {self.pointID}
            """) 
            return query
    
    def build_params_distribution(self, layer : float | str):
        """
        Given a layer's depth, return the distribution for the 4 types of parameters.
        """
        query = QSqlQuery(self.con)
        query.prepare(f"""
            SELECT Permeability, ThermConduct, Porosity, HeatCapacity FROM ParametersDistribution
            JOIN Point
            ON ParametersDistribution.PointKey = Point.ID
            JOIN Layer
            ON ParametersDistribution.Layer = Layer.ID
            WHERE Layer.Depth = {layer}
            AND Point.ID = {self.pointID}
        """)
        return query
    
    def build_raw_measures(self, full_query : bool = False, field : str = ""):
        """
        Build an return a query getting the raw measures:
        -if full_query is True, then extract the Date, Pressure and all Temperatures.
        -if field is not an empty string, then it MUST be either "Temp" or "Pressure". Extract the Date and the corresponding field : either all the temperatures or just the pressure.
        """
        query = QSqlQuery(self.con)
        if full_query:
            query.prepare(f"""
                SELECT RawMeasuresTemp.Date, RawMeasuresTemp.Temp1, RawMeasuresTemp.Temp2, RawMeasuresTemp.Temp3, RawMeasuresTemp.Temp4, RawMeasuresPress.TempBed, RawMeasuresPress.Voltage FROM RawMeasuresTemp, RawMeasuresPress
                WHERE RawMeasuresTemp.Date = RawMeasuresPress.Date
                AND RawMeasuresPress.SamplingPoint= (SELECT ID FROM SamplingPoint WHERE SamplingPoint.ID = {self.samplingPointID})
                AND RawMeasuresTemp.SamplingPoint = (SELECT ID FROM SamplingPoint WHERE SamplingPoint.ID = {self.samplingPointID})
                ORDER BY RawMeasuresTemp.Date
            """)
            return query
        elif field =="Temp":
            query.prepare(f"""
                 SELECT RawMeasuresTemp.Date, RawMeasuresTemp.Temp1, RawMeasuresTemp.Temp2, RawMeasuresTemp.Temp3, RawMeasuresTemp.Temp4, RawMeasuresPress.TempBed FROM RawMeasuresTemp, RawMeasuresPress
                 WHERE RawMeasuresTemp.Date = RawMeasuresPress.Date
                 AND RawMeasuresPress.SamplingPoint = (SELECT ID FROM SamplingPoint WHERE SamplingPoint.ID = {self.samplingPointID})
                 AND RawMeasuresTemp.SamplingPoint = (SELECT ID FROM SamplingPoint WHERE SamplingPoint.ID = {self.samplingPointID})
                 ORDER BY RawMeasuresTemp.Date
            """)
            return query
        elif field =="Pressure":
            query.prepare(f"""
                SELECT RawMeasuresPress.Date,RawMeasuresPress.Voltage FROM RawMeasuresPress
                JOIN SamplingPoint
                ON RawMeasuresPress.SamplingPoint = SamplingPoint.ID
                WHERE SamplingPoint.ID = {self.samplingPointID}
                ORDER BY RawMeasuresPress.Date
            """)
            return query

    def build_cleaned_measures(self, full_query : bool = False, field : str = ""):
        """
        Build an return a query getting the cleaned measures. This function behaves the same as build_raw_measures: see its docstrings for additional information.
        """
        query = QSqlQuery(self.con)
        if full_query:
                query.prepare(f"""
                    SELECT Date.Date, CleanedMeasures.Temp1, CleanedMeasures.Temp2, CleanedMeasures.Temp3, CleanedMeasures.Temp4, CleanedMeasures.TempBed, CleanedMeasures.Pressure FROM CleanedMeasures
                    JOIN Date
                    ON CleanedMeasures.Date = Date.ID
                    JOIN Point
                    ON CleanedMeasures.PointKey = Point.ID
                    WHERE Point.ID = {self.pointID}
                    ORDER BY Date.Date
                """)
                return query
        elif field =="Temp":
            query.prepare(f"""
                SELECT Date.Date, CleanedMeasures.Temp1, CleanedMeasures.Temp2, CleanedMeasures.Temp3, CleanedMeasures.Temp4, CleanedMeasures.TempBed FROM CleanedMeasures
                JOIN Date
                ON CleanedMeasures.Date = Date.ID
                JOIN Point
                ON CleanedMeasures.PointKey = Point.ID
                WHERE Point.ID = {self.pointID}
                ORDER BY Date.Date
            """)
            return query
        elif field =="Pressure":
            query.prepare(f"""
                SELECT Date.Date, CleanedMeasures.Pressure FROM CleanedMeasures
                JOIN Date
                ON CleanedMeasures.Date = Date.ID
                JOIN Point
                ON CleanedMeasures.PointKey = Point.ID
                WHERE Point.ID = {self.pointID}
                ORDER BY Date.Date
            """)
            return query

    def computation_type(self):
        """
        Return None if no computation was made: else, return False if only the direct model was computed and True if the MCMC was computed.
        """
        q = QSqlQuery(self.con)
        q.prepare(f"""SELECT COUNT(*) FROM Quantile
                JOIN Point
                ON Quantile.PointKey = Point.ID
                WHERE Point.ID = {self.pointID}""")
        q.exec()
        q.next()
        if q.value(0) ==0:
            return None
        elif q.value(0) ==1:
            return False
        else: 
            return True

    def build_result_queries(self,result_type ="",option=""):
        """
        Return a list of queries according to the user's wish. The list will either be of length 1 (the model was not computed before), or more than one: in this case, there are as many queries as there are quantiles: the first query corresponds to the default model (quantile 0)
        """
        computation_type = self.computation_type()
        if computation_type is None:
            return []
        elif not computation_type:
            return [self.define_result_queries(result_type=result_type,option=option, quantile=0)]
        else:
            #This could be enhanced by going in the database and seeing which quantiles are available. For now, these available quantiles will be hard-coded
            select_quantiles = self.build_quantiles()
            select_quantiles.exec()
            result = []
            while select_quantiles.next():
                if select_quantiles.value(0) ==0:
                    #Default model should always be the first one
                    result.insert(0,self.define_result_queries(result_type=result_type,option=option, quantile=select_quantiles.value(0)))
                else:
                    result.append(self.define_result_queries(result_type=result_type,option=option, quantile=select_quantiles.value(0)))
            return result
    
    def define_result_queries(self,result_type ="",option="",quantile = 0):
        """
        Build and return ONE AND ONLY ONE query concerning the results.
        -quantile must be a float, and is either 0 (direct result), 0.05,0.5 or 0.95
        -option can be a string (which 2D map should be displayed or a date for the umbrellas) or a float (depth required by user)
        """
        #Water Flux
        query = QSqlQuery(self.con)
        if result_type =="WaterFlux":
            query.prepare(f"""
                SELECT Date.Date, WaterFlow.WaterFlow, Quantile.Quantile FROM WaterFlow
                JOIN Date
                ON WaterFlow.Date = Date.ID
                JOIN Quantile
                ON WaterFlow.Quantile = Quantile.ID
                JOIN Point
                ON Quantile.PointKey = Point.ID
                WHERE Point.ID = {self.pointID}
                AND Quantile.Quantile = {quantile}
                ORDER BY Date.Date
            """)
            return query
        elif result_type =="2DMap":
            if option=="Temperature":
                query.prepare(f"""
                    SELECT TemperatureAndHeatFlows.Temperature, Quantile.Quantile FROM TemperatureAndHeatFlows
                    JOIN Date
                    ON TemperatureAndHeatFlows.Date = Date.ID
                    JOIN Depth
                    ON TemperatureAndHeatFlows.Depth = Depth.ID
                    JOIN Quantile
                    ON TemperatureAndHeatFlows.Quantile = Quantile.ID
                    JOIN Point
                    ON Quantile.PointKey = Point.ID
                    WHERE Point.ID = {self.pointID}
                    AND Quantile.Quantile = {quantile}
                    ORDER BY Date.Date, Depth.Depth   
                """) #Column major: order by date
                return query
            elif option=="HeatFlows":
                query.prepare(f"""
                    SELECT Date.Date, TemperatureAndHeatFlows.AdvectiveFlow,TemperatureAndHeatFlows.ConductiveFlow,TemperatureAndHeatFlows.TotalFlow, TemperatureAndHeatFlows.Depth FROM TemperatureAndHeatFlows
                    JOIN Date
                    ON TemperatureAndHeatFlows.Date = Date.ID
                    JOIN Depth
                    ON TemperatureAndHeatFlows.Depth = Depth.ID
                    JOIN Quantile
                    ON TemperatureAndHeatFlows.Quantile = Quantile.ID
                    JOIN Point
                    ON Quantile.PointKey = Point.ID
                    WHERE Point.ID = {self.pointID}
                    AND Quantile.Quantile = {quantile}
                    ORDER BY Date.Date, Depth.Depth
                """)
                return query
    
    def build_insert_date(self):
        """
        Build and return a query to insert dates in the Date table.
        """
        query = QSqlQuery(self.con)
        query.prepare(f"""
            INSERT INTO Date (Date, PointKey)
            VALUES (:Date, :PointKey)
        """)
        return query
    
    def build_insert_cleaned_measures(self):
        """
        Build and return a query to insert cleaned measures in the database.
        """
        query = QSqlQuery(self.con)
        query.prepare(f"""
            INSERT INTO CleanedMeasures (Date, TempBed, Temp1, Temp2, Temp3, Temp4, Pressure, PointKey)
            VALUES (:DateID, :TempBed, :Temp1, :Temp2, :Temp3, :Temp4, :Pressure, :PointKey)        
        """)
        return query