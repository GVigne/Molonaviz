# from dialogcleanupmain import DialogCleanupMain
# from dialogcompute import DialogCompute
# from compute import Compute
# from usefulfonctions import *
# from dialogreset import DialogReset

import os
import csv
from PyQt5 import QtWidgets, QtCore, uic
from PyQt5.QtGui import QPixmap
from PyQt5.QtSql import QSqlQueryModel, QSqlQuery, QSqlDatabase #QSqlDatabase in used only for type hints
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from src.dialogExportCleanedMeasures import DialogExportCleanedMeasures
from src.Containers import Point
from src.MoloModel import  PressureDataModel, TemperatureDataModel, SolvedTemperatureModel, HeatFluxesModel, WaterFluxModel,ParamsDistributionModel
from src.MoloView import PressureView, TemperatureView,UmbrellaView,TempDepthView,TempMapView,AdvectiveFlowView, ConductiveFlowView, TotalFlowView, WaterFluxView, Log10KView, ConductivityView, PorosityView, CapacityView


From_WidgetPoint = uic.loadUiType(os.path.join(os.path.dirname(__file__), "..", "ui", "widgetPoint.ui"))[0]

class WidgetPoint(QtWidgets.QWidget, From_WidgetPoint):
    
    def __init__(self, con : QSqlDatabase, point: Point):
        # Call constructor of parent classes
        super(WidgetPoint, self).__init__()
        QtWidgets.QWidget.__init__(self)
        
        self.setupUi(self)        
        self.point = point
        self.con = con
        # self.computeEngine = Compute(db, self.point)

        #This should already be done in the .ui file
        self.checkBoxRawData.setChecked(True)
        self.checkBoxDirectModel.setChecked(True)
        self.radioButtonTherm1.setChecked(True)

        #Create all models: they are empty for now
        self.pressuremodel = PressureDataModel([])
        self.tempmodel = TemperatureDataModel([])
        self.tempmap_model = SolvedTemperatureModel([])
        self.fluxes_model = HeatFluxesModel([])
        self.waterflux_model = WaterFluxModel([])
        self.paramsdistr_model = ParamsDistributionModel([])
        
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
        self.setDataPlots()
        self.setResultsPlots()

    def setInfoTab(self):
        select_paths, select_infos = self.build_infos_queries()
        #Installation image
        select_paths.exec()
        select_paths.next()
        self.labelSchema.setPixmap(QPixmap(select_paths.value(0))) 
        self.labelSchema.setAlignment(QtCore.Qt.AlignHCenter)
        #This allows the image to take the entire size of the widget, however it will be misshapen
        # self.labelSchema.setScaledContents(True)
        # self.labelSchema.setSizePolicy(QtWidgets.QSizePolicy.Ignored,QtWidgets.QSizePolicy.Ignored)
        #Notice
        try:
            file = open(select_paths.value(1))
            notice = file.read()
            self.plainTextEditNotice.setPlainText(notice)
        except Exception:
            self.plainTextEditNotice.setPlainText("No notice was found")
            
        #Infos
        select_infos.exec()
        self.infosModel = QSqlQueryModel()
        self.infosModel.setQuery(select_infos)
        self.tableViewInfos.setModel(self.infosModel)

    def setupComboBoxLayers(self):
        """
        Setup the Combo box and which will be used to display the parameters
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
        self.paramsModel = QSqlQueryModel()
        self.paramsModel.setQuery(select_params)
        self.tableViewParams.setModel(self.paramsModel)
        
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
                self.gridLayoutQuantiles.addWidget(quantile_checkbox,i,0)
                self.gridLayoutQuantiles.addWidget(QtWidgets.QLabel(f"RMSE: {select_quantiles.value(0)} °C"),i,1)
                i +=1

        select_RMSE_therm = self.build_therm_RMSE()
        select_RMSE_therm.exec()
        select_RMSE_therm.next()
        #Display the RMSE for each thermometer or 0 if it has not been computed yet (ie select_RMSE_therm has only None values)
        self.labelRMSETherm1.setText(f"RMSE: {select_RMSE_therm.value(0) if select_RMSE_therm.value(0) else 0} °C")
        self.labelRMSETherm2.setText(f"RMSE: {select_RMSE_therm.value(1) if select_RMSE_therm.value(1) else 0} °C")
        self.labelRMSETherm3.setText(f"RMSE: {select_RMSE_therm.value(2) if select_RMSE_therm.value(2) else 0} °C")

    def exportMeasures(self):
        """
        Export two .csv files corresponding to the cleaned measures to the location given by the user.
        """
        dlg = DialogExportCleanedMeasures(self.point)
        dlg.setWindowModality(QtCore.Qt.ApplicationModal)
        res = dlg.exec_()
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
        for i in range (self.gridLayoutQuantiles.count()):
            checkbox = self.gridLayoutQuantiles.itemAt(i).widget()
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
        self.currentDataModel = QSqlQueryModel()
        self.currentDataModel.setQuery(select_query)
        self.tableViewDataArray.setModel(self.currentDataModel)

    def setWidgetInfos(self):
        self.setWindowTitle(self.point.name)
        self.lineEditPointName.setText(self.point.name)
        self.lineEditSensor.setText(self.point.psensor)
        self.lineEditShaft.setText(self.point.shaft)
    
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

    def deleteComputations(self):
        pointname = self.point.getName()
        deleteTableQuery = QSqlQuery()
        #Careful: should have joins as WaterFlow.PointKey !=Samplingpoint.name
        deleteTableQuery.exec_(f'DELETE FROM WaterFlow WHERE WaterFlow.PointKey=(SELECT Point.id FROM Point WHERE Point.SamplingPoint = (SELECT SamplingPoint.id FROM SamplingPoint WHERE SamplingPoint.Name="{pointname}"))')
        deleteTableQuery.exec_(f'DELETE FROM RMSE WHERE PointKey=(SELECT Point.id FROM Point WHERE Point.SamplingPoint = (SELECT SamplingPoint.id FROM SamplingPoint WHERE SamplingPoint.Name="{pointname}"))')
        deleteTableQuery.exec_(f'DELETE FROM TemperatureAndHeatFlows WHERE PointKey=(SELECT Point.id FROM Point WHERE Point.SamplingPoint = (SELECT SamplingPoint.id FROM SamplingPoint WHERE SamplingPoint.Name="{pointname}"))')
        deleteTableQuery.exec_(f'DELETE FROM ParametersDistribution WHERE ParametersDistribution.PointKey=(SELECT Point.id FROM Point WHERE Point.SamplingPoint = (SELECT SamplingPoint.id FROM SamplingPoint WHERE SamplingPoint.Name="{pointname}"))')
        deleteTableQuery.exec_(f'DELETE FROM BestParameters WHERE BestParameters.PointKey=(SELECT Point.id FROM Point WHERE Point.SamplingPoint = (SELECT SamplingPoint.id FROM SamplingPoint WHERE SamplingPoint.Name="{pointname}"))')

        deleteTableQuery.exec_("DELETE FROM Date WHERE (SELECT count(*) FROM RMSE)==0")    #We delete the rows of this table if and only if the point we reset was the only one open
        deleteTableQuery.exec_("DELETE FROM Depth WHERE (SELECT count(*) FROM RMSE)==0")

        '''
        clearLayout(self.groupBoxWaterFlux)
        clearLayout(self.groupBoxAdvectiveFlux)
        clearLayout(self.groupBoxConductiveFlux)
        clearLayout(self.groupBoxTotalFlux)
        clearLayout(self.gridLayoutQuantiles)
        clearLayout(self.labelRMSETherm1)
        clearLayout(self.labelRMSETherm2)
        clearLayout(self.labelRMSETherm3)
        clearLayout(self.tableViewDataArray)'''

    def deleteCleaned(self):
        pointname = self.point.getName()
        deleteTableQuery = QSqlQuery()
        deleteTableQuery.exec_("DELETE FROM CleanedMeasures WHERE PointKey=(SELECT id FROM SamplingPoint WHERE SamplingPoint.Name='"+pointname+"')")
        #clearLayout(self.tableViewDataArray)

    def reset(self):
        dlg = DialogReset()
        res = dlg.exec_()
        if res == QtWidgets.QDialog.Accepted:
            self.deleteComputations()
            self.deleteCleaned()
            self.update_all_models()

    def cleanup(self):
        cleanUpDir = os.path.join(self.study.rootDir,"Cleanup_scripts")
        dlg = DialogCleanupMain(self.point.name, cleanUpDir,self.study,self.study.con)
        res = dlg.exec_()
        #print(self.pointDir)
        if res == QtWidgets.QDialog.Accepted:
            dlg.df_cleaned["date"] = dlg.df_cleaned.apply(lambda x: x['date'].strftime("%Y:%m:%d:%H:%M:%S"), axis=1)
            dlg.mainDb.dateDb.insert(dlg.df_cleaned["date"])
            dlg.mainDb.cleanedMeasuresDb.update(dlg.df_cleaned,dlg.pointKey)

            zh = dlg.df_cleaned[["date","t1","t2","t3","t4"]]
            zh.to_csv(os.path.join(cleanUpDir,f"processed_temperatures_{self.point.name}.csv"))
            press = dlg.df_cleaned[["date","charge_diff","t_stream"]]
            press.to_csv(os.path.join(cleanUpDir,f"processed_pressures_{self.point.name}.csv"))
        # #Needs to be adapted!
        # if self.currentdata == "raw":
        #     print("Please clean-up your processed data. Click again on the raw data box")
        # else:
        #     dlg = DialogCleanupMain(self.point.name,self.pointDir,self.study)
        #     res = dlg.exec_()
        #     #print(self.pointDir)
        #     if res == QtWidgets.QDialog.Accepted:
        #         dlg.mainDb.newDatesDb.insert(dlg.df_cleaned)
        #         dlg.mainDb.cleanedMeasuresDb.update(dlg.df_cleaned,dlg.pointKey)

        #         # script,scriptpartiel = dlg.getScript()
        #         # print("Cleaning data...")

        #         # try :
        #         #     self.dftemp, self.dfpress = self.point.cleanup(script, self.dftemp, self.dfpress)
        #         #     print("Data successfully cleaned !...")
                    
        #         #     #On actualise les modèles
        #         #     self.currentTemperatureModel.setData(self.dftemp)
        #         #     self.currentPressureModel.setData(self.dfpress)
        #         #     #self.tableViewTemp.resizeColumnsToContents()
        #         #     #self.tableViewPress.resizeColumnsToContents()
        #         #     self.graphpress.update_(self.dfpress)
        #         #     self.graphtemp.update_(self.dftemp, dfpressure=self.dfpress)
        #         #     print("Plots successfully updated")
                    
        #         #     # Save the modified text
        #         #     with open(os.path.join(self.pointDir,"script_"+self.point.name+".txt"),'w') as file:
        #         #         file.write(scriptpartiel)
        #         #     print("Script successfully saved")
                    
                    
        #         # except Exception as e :
        #         #     print(e, "==> Clean-up aborted")
        #         #     displayCriticalMessage("Error : Clean-up aborted", f'Clean-up was aborted due to the following error : \n"{str(e)}" ' )
        #         #     self.cleanup()
    

    def compute(self):
        #Needs to be adapted! Especially self.onMCMCisFinished (when computations are done)
        
        # sensorDir = self.study.getSensorDir()

        dlg = DialogCompute(self.point.name)
        res = dlg.exec()
        if res == 10: #Direct Model
            params, nb_cells, depths = dlg.getInputDirectModel()
            self.computeEngine.computeDirectModel(params, nb_cells,depths)
            self.update_all_models()

    
        if res == 1 : #MCMC
            print("Not direct")
            # nb_iter, priors, nb_cells, quantiles = dlg.getInputMCMC()
            # self.nb_quantiles = len(quantiles)
            # with open(self.MCMCDir+"/nb_quantiles", "w") as f:
            #     f.write(str(self.nb_quantiles))
            #     f.close()
            # # compute = Compute(self.point)
            # # compute.computeMCMC(nb_iter, priors, nb_cells, sensorDir)
            # self.computeEngine.MCMCFinished.connect(self.onMCMCFinished)
            # self.computeEngine.computeMCMC(nb_iter, priors, nb_cells, sensorDir, quantiles)

    def onMCMCFinished(self):
        #Needs to be adapted!
        return

        self.setDataFrames('MCMC')

        self.comboBoxDepth.clear()
        for depth in self.dfdepths.values.tolist():
            self.comboBoxDepth.insertItem(len(self.dfdepths.values.tolist()), str(depth))

        if self.MCMCiscomputed :
            print('MCMC is computed')
            self.graphwaterMCMC.update_(self.dfwater)
            self.graphsolvedtempMCMC.update_(self.dfsolvedtemp, self.dfdepths)
            self.graphintertempMCMC.update_(self.dfintertemp, self.dfdepths, nb_quantiles=self.nb_quantiles)
            self.graphfluxesMCMC.update_(self.dfadvec, self.dfconduc, self.dftot, self.dfdepths)
            self.histos.update_(self.dfallparams)
            self.parapluiesMCMC.update_(self.dfsolvedtemp, self.dfdepths)
            self.BestParamsModel.setData(self.dfbestparams)
            print("Model successfully updated !")

        else :

            #Flux d'eau
            clearLayout(self.vboxwaterMCMC)
            self.plotWaterFlowsMCMC(self.dfwater)

            #Flux d'énergie
            clearLayout(self.vboxfluxesMCMC)
            self.plotFriseHeatFluxesMCMC(self.dfadvec, self.dfconduc, self.dftot, self.dfdepths)

            #Frise de température
            clearLayout(self.vboxfrisetempMCMC)
            self.plotFriseTempMCMC(self.dfsolvedtemp, self.dfdepths)
            #Parapluies
            clearLayout(self.vboxsolvedtempMCMC)
            self.plotParapluiesMCMC(self.dfsolvedtemp, self.dfdepths)
            #Température à l'interface
            clearLayout(self.vboxintertempMCMC)
            self.plotInterfaceTempMCMC(self.dfintertemp, self.dfdepths, self.nb_quantiles)

            #Histogrammes
            clearLayout(self.vboxhistos)
            self.histos(self.dfallparams)
            #Les meilleurs paramètres
            self.setBestParamsModel(self.dfbestparams)

            self.MCMCiscomputed = True
            print("Model successfully created !")

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

    def setDataPlots(self):
        #Pressure :
        if self.checkBoxRawData.isChecked():
            select_pressure = self.build_raw_measures(field ="Pressure")
        else:
            select_pressure = self.build_cleaned_measures(field ="Pressure")
        self.pressuremodel = PressureDataModel([select_pressure])
        self.graphpress = PressureView(self.pressuremodel, time_dependent=True,ylabel="Pression différentielle (m)")
        self.toolbarPress = NavigationToolbar(self.graphpress, self)
        vbox = QtWidgets.QVBoxLayout()
        self.groupBoxPress.setLayout(vbox)
        vbox.addWidget(self.graphpress)
        vbox.addWidget(self.toolbarPress)
        
        self.pressuremodel.exec()
      
        #Temperatures :
        if self.checkBoxRawData.isChecked():
            select_temp = self.build_raw_measures(field ="Temp")
        else:
            select_temp = self.build_cleaned_measures(field ="Temp")
        self.tempmodel = TemperatureDataModel([select_temp])
        self.graphtemp = TemperatureView(self.tempmodel, time_dependent=True,ylabel="Température en K")
        self.toolbarTemp = NavigationToolbar(self.graphtemp, self)
        vbox2 = QtWidgets.QVBoxLayout()
        self.groupBoxTemp.setLayout(vbox2)
        vbox2.addWidget(self.graphtemp)
        vbox2.addWidget(self.toolbarTemp)

        self.tempmodel.exec()
      
    
    def setResultsPlots(self):
        """
        Display the results in the corresponding tabs.
        """
        if self.computation_type() is not None:
            self.plotFluxes()
            self.plotTemperatureMap()
            self.plotHistos()  
        else:
            # vbox = QtWidgets.QVBoxLayout()
            vbox = QtWidgets.QVBoxLayout()
            vbox.addWidget(QtWidgets.QLabel("No model has been computed yet"),QtCore.Qt.AlignCenter)
            self.groupBoxWaterFlux.setLayout(vbox)
            vbox = QtWidgets.QVBoxLayout()
            vbox.addWidget(QtWidgets.QLabel("No model has been computed yet"),QtCore.Qt.AlignCenter)
            self.groupBoxAdvectiveFlux.setLayout(vbox)
            vbox = QtWidgets.QVBoxLayout()
            vbox.addWidget(QtWidgets.QLabel("No model has been computed yet"),QtCore.Qt.AlignCenter)
            self.groupBoxTotalFlux.setLayout(vbox)
            vbox = QtWidgets.QVBoxLayout()
            vbox.addWidget(QtWidgets.QLabel("No model has been computed yet"),QtCore.Qt.AlignCenter)
            self.groupBoxConductiveFlux.setLayout(vbox)
            vbox = QtWidgets.QVBoxLayout()
            vbox.addWidget(QtWidgets.QLabel("No model has been computed yet"),QtCore.Qt.AlignCenter)
            self.groupBoxTempMap.setLayout(vbox)
            vbox = QtWidgets.QVBoxLayout()
            vbox.addWidget(QtWidgets.QLabel("No model has been computed yet"),QtCore.Qt.AlignCenter)
            self.groupBoxUmbrella.setLayout(vbox)
            vbox = QtWidgets.QVBoxLayout()
            vbox.addWidget(QtWidgets.QLabel("No model has been computed yet"),QtCore.Qt.AlignCenter)
            self.groupBoxTempDepth.setLayout(vbox)
            vbox = QtWidgets.QVBoxLayout()
            vbox.addWidget(QtWidgets.QLabel("No model has been computed yet"),QtCore.Qt.AlignCenter)
            self.groupBoxLog10K.setLayout(vbox)
            vbox = QtWidgets.QVBoxLayout()
            vbox.addWidget(QtWidgets.QLabel("No model has been computed yet"),QtCore.Qt.AlignCenter)
            self.groupBoxConductivity.setLayout(vbox)
            vbox = QtWidgets.QVBoxLayout()
            vbox.addWidget(QtWidgets.QLabel("No model has been computed yet"),QtCore.Qt.AlignCenter)
            self.groupBoxPorosity.setLayout(vbox)
            vbox = QtWidgets.QVBoxLayout()
            vbox.addWidget(QtWidgets.QLabel("No model has been computed yet"),QtCore.Qt.AlignCenter)
            self.groupBoxCapacity.setLayout(vbox)     
            

    def plotTemperatureMap(self):
        select_tempmap = self.build_result_queries(result_type="2DMap",option="Temperature") #This is a list of temperatures for all quantiles
        select_depths = self.build_depths()
        select_dates = self.build_dates()
        self.tempmap_model = SolvedTemperatureModel([select_dates,select_depths]+select_tempmap)
        self.umbrella_view = UmbrellaView(self.tempmap_model)
        self.tempmap_view = TempMapView(self.tempmap_model)
        
        sel_depth = self.build_thermo_depth(1)
        sel_depth.exec()
        sel_depth.next()
        options = [sel_depth.value(0), [0]] #First thermometer, direct model
        self.depth_view = TempDepthView(self.tempmap_model, options=options)
        
        self.toolbarUmbrella = NavigationToolbar(self.umbrella_view, self)
        vbox = QtWidgets.QVBoxLayout()
        self.groupBoxUmbrella.setLayout(vbox)
        vbox.addWidget(self.umbrella_view)
        vbox.addWidget(self.toolbarUmbrella)

        self.toolbarTempMap = NavigationToolbar(self.tempmap_view, self)
        vbox = QtWidgets.QVBoxLayout()
        self.groupBoxTempMap.setLayout(vbox)
        vbox.addWidget(self.tempmap_view)
        vbox.addWidget(self.toolbarTempMap)

        self.toolbarDepth = NavigationToolbar(self.depth_view, self)
        vbox = QtWidgets.QVBoxLayout()
        self.groupBoxTempDepth.setLayout(vbox)
        vbox.addWidget(self.depth_view)
        vbox.addWidget(self.toolbarDepth)

        self.tempmap_model.exec()

    def plotFluxes(self):
        #Plot the heat fluxes
        select_heatfluxes= self.build_result_queries(result_type="2DMap",option="HeatFlows") #This is a list
        select_depths = self.build_depths()
        select_dates = self.build_dates()
    
        self.fluxes_model = HeatFluxesModel([select_dates,select_depths]+select_heatfluxes)
        self.advective_view = AdvectiveFlowView(self.fluxes_model)
        self.conductive_view = ConductiveFlowView(self.fluxes_model)
        self.totalflux_view = TotalFlowView(self.fluxes_model)

        self.toolbarAdvective = NavigationToolbar(self.advective_view, self)
        vbox = QtWidgets.QVBoxLayout()
        self.groupBoxAdvectiveFlux.setLayout(vbox)
        vbox.addWidget(self.advective_view)
        vbox.addWidget(self.toolbarAdvective)

        self.toolbarConductive = NavigationToolbar(self.conductive_view, self)
        vbox = QtWidgets.QVBoxLayout()
        self.groupBoxConductiveFlux.setLayout(vbox)
        vbox.addWidget(self.conductive_view)
        vbox.addWidget(self.toolbarConductive)

        self.toolbarTotalFlux = NavigationToolbar(self.totalflux_view, self)
        vbox = QtWidgets.QVBoxLayout()
        self.groupBoxTotalFlux.setLayout(vbox)
        vbox.addWidget(self.totalflux_view)
        vbox.addWidget(self.toolbarTotalFlux)

        self.fluxes_model.exec()

        #Plot the water fluxes
        select_waterflux= self.build_result_queries(result_type="WaterFlux") #This is already a list
        self.waterflux_model = WaterFluxModel(select_waterflux)
        self.waterflux_view = WaterFluxView(self.waterflux_model)
        
        self.toolbarWaterFlux = NavigationToolbar(self.waterflux_view, self)
        vbox = QtWidgets.QVBoxLayout()
        self.groupBoxWaterFlux.setLayout(vbox)
        vbox.addWidget(self.waterflux_view)
        vbox.addWidget(self.toolbarWaterFlux)

        self.waterflux_model.exec()
    
    def plotHistos(self):
        select_params = self.build_params_distribution(self.comboBoxSelectLayer.currentText())
        self.paramsdistr_model = ParamsDistributionModel([select_params])

        self.logk_view = Log10KView(self.paramsdistr_model)
        self.conductivity_view = ConductivityView(self.paramsdistr_model)
        self.porosity_view = PorosityView(self.paramsdistr_model)
        self.capacity_view = CapacityView(self.paramsdistr_model)

        self.toolbarLog10k = NavigationToolbar(self.logk_view, self)
        vbox = QtWidgets.QVBoxLayout()
        self.groupBoxLog10K.setLayout(vbox)
        vbox.addWidget(self.logk_view)
        vbox.addWidget(self.toolbarLog10k)

        self.toolbarConductivity = NavigationToolbar(self.conductivity_view, self)
        vbox = QtWidgets.QVBoxLayout()
        self.groupBoxConductivity.setLayout(vbox)
        vbox.addWidget(self.conductivity_view)
        vbox.addWidget(self.toolbarConductivity)

        self.toolbarPorosity = NavigationToolbar(self.porosity_view, self)
        vbox = QtWidgets.QVBoxLayout()
        self.groupBoxPorosity.setLayout(vbox)
        vbox.addWidget(self.porosity_view)
        vbox.addWidget(self.toolbarPorosity)

        self.toolbarCapacity = NavigationToolbar(self.capacity_view, self)
        vbox = QtWidgets.QVBoxLayout()
        self.groupBoxCapacity.setLayout(vbox)
        vbox.addWidget(self.capacity_view)
        vbox.addWidget(self.toolbarCapacity)

        self.paramsdistr_model.exec()

    def label_update(self):
        self.labelBins.setText(str(self.horizontalSliderBins.value()))
    
    def update_all_models(self):
        """
        Update all existing models. This should only be called after reset, cleanup or compute.
        """

        self.setInfoTab()

        self.comboBoxSelectLayer.clear()
        self.setupComboBoxLayers()

        self.setPressureAndTemperatureModels()
    
        if self.checkBoxRawData.isChecked():
            select_pressure = self.build_raw_measures(field ="Pressure")
            select_temp = self.build_raw_measures(field ="Temp")
        else:
            select_pressure = self.build_cleaned_measures(field ="Pressure")
            select_temp = self.build_cleaned_measures(field ="Temp")
        self.pressuremodel.new_queries([select_pressure])
        self.tempmodel.new_queries([select_temp])

        select_tempmap = self.build_result_queries(result_type="2DMap",option="Temperature") #This is a list of temperatures for all quantiles
        select_depths = self.build_depths()
        select_dates = self.build_dates()
        self.tempmap_model.new_queries([select_dates,select_depths]+select_tempmap)

        select_heatfluxes= self.build_result_queries(result_type="2DMap",option="HeatFlows") #This is a list
        select_depths = self.build_depths()
        select_dates = self.build_dates()
        self.fluxes_model.new_queries([select_dates,select_depths]+select_heatfluxes)

        select_waterflux= self.build_result_queries(result_type="WaterFlux") #This is already a list
        self.waterflux_model.new_queries(select_waterflux)

        self.pressuremodel.exec()
        self.tempmodel.exec()
        self.tempmap_model.exec()
        self.fluxes_model.exec()
        self.waterflux_model.exec()
    
    def build_infos_queries(self):
        """
        Build and return two queries for the info tab:
        -one to get the configuration image of the sampling point and the notice. Theses are paths.
        -one to get the rest of the information of the sampling point.
        """
        paths = QSqlQuery(self.con)
        paths.prepare(f"""
            SELECT SamplingPoint.Scheme, SamplingPoint.Notice FROM SamplingPoint 
            WHERE SamplingPoint.Name = '{self.point.name}' 
        """)

        infos = QSqlQuery(self.con)
        infos.prepare(f"""
            SELECT SamplingPoint.Name, SamplingPoint.Setup,SamplingPoint.LastTransfer,SamplingPoint.Offset, SamplingPoint.RiverBed FROM SamplingPoint 
            WHERE SamplingPoint.Name = '{self.point.name}' 
        """)
        return paths, infos

    def build_layers_query(self):
        """
        Build and return a query giving the depths of all the layers.
        """
        query = QSqlQuery(self.con)
        query.prepare(f"""
            SELECT Layer.DepthBed FROM Layer 
            JOIN BestParameters ON Layer.id = BestParameters.Layer
            JOIN Point ON BestParameters.PointKey = Point.id
            JOIN SamplingPoint ON Point.SamplingPoint = SamplingPoint.id
            WHERE SamplingPoint.Name = '{self.point.name}'
            ORDER BY Layer.DepthBed 
        """)
        return query
    
    def build_params_query(self, depth : float | str):
        """
        Build and return the parameters for the given depth.
        """
        query = QSqlQuery(self.con)
        query.prepare(f"""
            SELECT BestParameters.Permeability, BestParameters.ThermConduct, BestParameters.Porosity FROM BestParameters 
            JOIN Layer ON BestParameters.Layer = Layer.id 
            WHERE Layer.DepthBed = {depth}
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
            ON RMSE.Quantile = Quantile.id
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
            ON RMSE.Quantile = Quantile.id
            WHERE RMSE.PointKey = (SELECT id FROM SamplingPoint WHERE SamplingPoint.Name = '{self.point.name}')
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
            ORDER BY Depth.Depth  
        """)
        return query
        
    def build_dates(self):
        """
        Build and return all the dates.
        """
        query = QSqlQuery(self.con)
        query.prepare(f"""
            SELECT Date.Date FROM Date 
            ORder by Date.Date   
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
                ON Depth.id = RMSE.{field} 
                JOIN Point
                ON RMSE.PointKey = Point.id 
                JOIN SamplingPoint
                ON Point.SamplingPoint = SamplingPoint.id
                WHERE SamplingPoint.Name = '{self.point.name}'
            """) 
            return query
    
    def build_params_distribution(self, layer : float | str):
        """
        Given a layer (DepthBed), return the distribution for the 4 types of parameters.
        """
        query = QSqlQuery(self.con)
        query.prepare(f"""
            SELECT Permeability, ThermConduct, Porosity, HeatCapacity FROM ParametersDistribution
            JOIN Point
            ON ParametersDistribution.PointKey = Point.id
            JOIN SamplingPoint
            ON Point.SamplingPoint = SamplingPoint.id
            JOIN Layer
            ON ParametersDistribution.Layer = Layer.id
            WHERE Layer.DepthBed = {layer}
            AND SamplingPoint.Name = '{self.point.name}'
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
                SELECT RawMeasuresTemp.Date, RawMeasuresTemp.Temp1, RawMeasuresTemp.Temp2, RawMeasuresTemp.Temp3, RawMeasuresTemp.Temp4, RawMeasuresPress.TempBed, RawMeasuresPress.Tension FROM RawMeasuresTemp, RawMeasuresPress
                WHERE RawMeasuresTemp.Date = RawMeasuresPress.Date
                AND RawMeasuresPress.PointKey=RawMeasuresTemp.PointKey = (SELECT id FROM SamplingPoint WHERE SamplingPoint.Name = '{self.point.name}')
                ORDER BY RawMeasuresTemp.Date
            """)
            return query
        elif field =="Temp":
            query.prepare(f"""
                SELECT RawMeasuresTemp.Date, RawMeasuresTemp.Temp1, RawMeasuresTemp.Temp2, RawMeasuresTemp.Temp3, RawMeasuresTemp.Temp4, RawMeasuresPress.TempBed FROM RawMeasuresTemp, RawMeasuresPress
                WHERE RawMeasuresTemp.Date = RawMeasuresPress.Date
                AND RawMeasuresPress.PointKey=RawMeasuresTemp.PointKey = (SELECT id FROM SamplingPoint WHERE SamplingPoint.Name = '{self.point.name}')
                ORDER BY RawMeasuresTemp.Date
            """)
            return query
        elif field =="Pressure":
            query.prepare(f"""
                SELECT RawMeasuresPress.Date,RawMeasuresPress.Tension FROM RawMeasuresPress
                WHERE RawMeasuresPress.PointKey= (SELECT id FROM SamplingPoint WHERE SamplingPoint.Name = '{self.point.name}')
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
                    ON CleanedMeasures.Date = Date.id
                    WHERE CleanedMeasures.PointKey = (SELECT id FROM SamplingPoint WHERE SamplingPoint.Name = '{self.point.name}')
                    ORDER BY Date.Date
                """)
                return query
        elif field =="Temp":
            query.prepare(f"""
                SELECT Date.Date, CleanedMeasures.Temp1, CleanedMeasures.Temp2, CleanedMeasures.Temp3, CleanedMeasures.Temp4, CleanedMeasures.TempBed FROM CleanedMeasures
                JOIN Date
                ON CleanedMeasures.Date = Date.id
                WHERE CleanedMeasures.PointKey = (SELECT id FROM SamplingPoint WHERE SamplingPoint.Name = '{self.point.name}')
                ORDER BY Date.Date
            """)
            return query
        elif field =="Pressure":
            query.prepare(f"""
                SELECT Date.Date, CleanedMeasures.Pressure FROM CleanedMeasures
                JOIN Date
                ON CleanedMeasures.Date = Date.id
                WHERE CleanedMeasures.PointKey = (SELECT id FROM SamplingPoint WHERE SamplingPoint.Name = '{self.point.name}')
                ORDER BY Date.Date
            """)
            return query

    def computation_type(self):
        """
        Return None if no computation was made: else, return False if only the direct model was computed and True if the MCMC was computed.
        """
        q = QSqlQuery("SELECT COUNT(*) FROM Quantile")
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
                ON WaterFlow.Date = Date.id
                JOIN Quantile
                ON WaterFlow.Quantile = Quantile.id
                WHERE Quantile.Quantile = {quantile}
                AND WaterFlow.PointKey = (SELECT Point.id FROM Point WHERE Point.SamplingPoint = (SELECT SamplingPoint.id FROM SamplingPoint WHERE SamplingPoint.name = '{self.point.name}'))
                ORDER BY Date.Date
            """)
            return query
        elif result_type =="2DMap":
            if option=="Temperature":
                query.prepare(f"""
                    SELECT TemperatureAndHeatFlows.Temperature,Quantile.Quantile FROM TemperatureAndHeatFlows
                    JOIN Date
                    ON TemperatureAndHeatFlows.Date = Date.id
                    JOIN Depth
                    ON TemperatureAndHeatFlows.Depth = Depth.id
                    JOIN Quantile
                    ON TemperatureAndHeatFlows. Quantile = Quantile.id
                    WHERE Quantile.Quantile = {quantile}
                    AND  TemperatureAndHeatFlows.PointKey = (SELECT Point.id FROM Point WHERE Point.SamplingPoint = (SELECT SamplingPoint.id FROM SamplingPoint WHERE SamplingPoint.name = '{self.point.name}'))
                    ORDER BY Date.Date, Depth.Depth   
                """) #Column major: order by date
                return query
            elif option=="HeatFlows":
                query.prepare(f"""
                    SELECT Date.Date, TemperatureAndHeatFlows.AdvectiveFlow,TemperatureAndHeatFlows.ConductiveFlow,TemperatureAndHeatFlows.TotalFlow, TemperatureAndHeatFlows.Depth FROM TemperatureAndHeatFlows
                    JOIN Date
                    ON TemperatureAndHeatFlows.Date = Date.id
                    JOIN Depth
                    ON eatFlows.Depth = Depth.id
                    WHERE TemperatureAndHeatFlows.Quantile = (SELECT Quantile.id FROM Quantile WHERE Quantile.Quantile = {quantile})
                    AND  TemperatureAndHeatFlows.PointKey = (SELECT Point.id FROM Point WHERE Point.SamplingPoint = (SELECT SamplingPoint.id FROM SamplingPoint WHERE SamplingPoint.name = '{self.point.name}'))
                    ORDER BY Date.Date, Depth.Depth
                """)
                return query