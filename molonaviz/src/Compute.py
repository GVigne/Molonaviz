# import os
# import numpy as np
# import pandas as pd
# from datetime import datetime
# from PyQt5 import QtCore
# from point import Point
# from errors import *
# from usefulfonctions import *
# # We have already check the pyheatmy package in mainwindow, so here we let it pass
# try:
#     from pyheatmy import *
# except:
#     pass
from subprocess import list2cmdline
from PyQt5 import QtCore
from PyQt5.QtSql import QSqlQuery, QSqlDatabase #QSqlDatabase in used only for type hints
from pyheatmy import * 
from utils.utils import databaseDateToDatetime, datetimeToDatabaseDate
from numpy import shape

class ColumnMCMCRunner(QtCore.QObject):
    """
    A QT runner which is meant to launch the MCMC in its own thread.
    """
    finished = QtCore.pyqtSignal()
    
    def __init__(self, col, nb_iter: int, priors: dict, nb_cells: str, quantiles: list):
        super(ColumnMCMCRunner, self).__init__()
        
        self.col = col
        self.nb_iter = nb_iter
        self.priors = priors
        self.nb_cells = nb_cells
        self.quantiles = quantiles
        
    def run(self):
        print("Launching MCMC...")
        self.col.compute_mcmc(self.nb_iter, self.priors, self.nb_cells, self.quantiles)
        self.finished.emit()

class ColumnDirectModelRunner(QtCore.QObject):
    """
    A QT runner which is meant to launch the Direct Model in its own thread.
    """
    finished = QtCore.pyqtSignal()
    
    def __init__(self, col, params : list[list], nb_cells : int):
        super(ColumnDirectModelRunner, self).__init__()
        self.col = col
        self.params = params
        self.nb_cells = nb_cells
        
    def run(self):
        print("Launching Direct Model...")
        layers = layersListCreator(self.params)
        self.col.compute_solve_transi(layers, self.nb_cells)
        self.finished.emit()

class Compute(QtCore.QObject):
    """
    How to use this class : 
    - Initialise the compute engine by giving it the  database connection and ID of the current Point.
    - When computations are needed, create an associated Column objected. This requires cleaned measures to be in the database for this point. This can be made by calling compute.setColumn()
    - Launch the computation :
        - with given parameters : compute.computeDirectModel(params: tuple, nb_cells: int, sensorDir: str)
        - with parameters inferred from MCMC : compute.computeMCMC(nb_iter: int, priors: dict, nb_cells: str, sensorDir: str)
    """
    MCMCFinished = QtCore.pyqtSignal()
    DirectModelFinished = QtCore.pyqtSignal()

    def __init__(self, con : QSqlDatabase, pointID: int | str):
        # Call constructor of parent classes
        super(Compute, self).__init__()
        self.thread = QtCore.QThread()

        self.con = con
        self.pointID = pointID
        self.col = None
    
    def setColumn(self):
        """
        Create the Column object associated to the current Point.
        """
        press = []
        temps = []
        cleaned_measures = self.build_cleaned_measures()
        cleaned_measures.exec()
        while cleaned_measures.next():
            temps.append([databaseDateToDatetime(cleaned_measures.value(0)),[cleaned_measures.value(1), cleaned_measures.value(2), cleaned_measures.value(3), cleaned_measures.value(4)] ]) #Date and 4 Temperatures
            press.append([databaseDateToDatetime(cleaned_measures.value(0)), [cleaned_measures.value(5), cleaned_measures.value(6)]]) #Date, Pressure, Temperature

        column_infos = self.build_column_infos()
        column_infos.exec()
        column_infos.next()

        col_dict = {
	        "river_bed" : column_infos.value(0),
            "depth_sensors" : [column_infos.value(i) for i in [1,2,3,4]],
	        "offset" : column_infos.value(5),
            "dH_measures" : press,
	        "T_measures" : temps,
            "sigma_meas_P" : column_infos.value(6),
            "sigma_meas_T" : column_infos.value(7),
            "inter_mode" : "linear"
            }
        
        self.col = Column.from_dict(col_dict)

    def computeDirectModel(self, params : list[list],  nb_cells: int):
        """
        Launch the direct model with given parameters per layer.
        """
        if self.thread.isRunning():
            print("Please wait while for the previous computation to end")
            return
    
        self.saveLayersAndParams(params)
        self.updateNBCells(nb_cells)

        self.setColumn() #Updates self.col
        self.direct_runner = ColumnDirectModelRunner(self.col,params,nb_cells)
        self.direct_runner.finished.connect(self.endDirectmodel)
        self.direct_runner.moveToThread(self.thread)
        self.thread.started.connect(self.direct_runner.run)
        self.thread.start()
    
    def endDirectmodel(self):
        """
        This is called when the DirectModel is over. Save the relevant information in the database
        """
        self.saveDirectModelResults()

        self.thread.quit()
        print("Direct model finished.")

        self.DirectModelFinished.emit()

    
    def updateNBCells(self, nb_cells):
        """
        Update entry in Point table to reflect the given number of cells.
        """
        updatePoint =  QSqlQuery(self.con)
        updatePoint.prepare(f"UPDATE Point SET DiscretStep = {nb_cells} WHERE ID = {self.pointID}")
        updatePoint.exec()

    def saveLayersAndParams(self, data : list[list]):
        """
        Save the layers and the last parameters in the database.
        """
        insertlayer = QSqlQuery(self.con)
        insertlayer.prepare("INSERT INTO Layer (Layer, DepthBed, PointKey) VALUES (:Layer, :DepthBed, :PointKey)")
        insertlayer.bindValue(":PointKey", self.pointID)

        insertparams = QSqlQuery(self.con)
        insertparams.prepare(f"""INSERT INTO BestParameters (Permeability, ThermConduct, Porosity, Capacity, Layer, PointKey)
                           VALUES (:Permeability, :ThermConduct, :Porosity, :Capacity, :Layer, :PointKey)""")
        insertparams.bindValue(":PointKey", self.pointID)

        self.con.transaction()
        for layer, depth, perm, n, lamb, rho in data:
            insertlayer.bindValue(":Layer", layer)
            insertlayer.bindValue(":DepthBed", depth)
            insertlayer.exec()

            insertparams.bindValue(":Permeability", perm)
            insertparams.bindValue(":ThermConduct", lamb)
            insertparams.bindValue(":Porosity", n)
            insertparams.bindValue(":Capacity", rho)
            insertparams.bindValue(":Layer", insertlayer.lastInsertId())
            insertparams.exec()
        self.con.commit()
    
    def saveDirectModelResults(self):
        """
        Query the database and save the direct model results.
        """
        #Quantile 0
        insertquantiles = QSqlQuery(self.con)
        insertquantiles.prepare(f"INSERT INTO Quantile (Quantile, PointKey) VALUES (0,{self.pointID})")
        
        insertquantiles.exec()
        quantileID = insertquantiles.lastInsertId()

        #Depths
        depths = self.col.get_depths_solve()
        insertDepths = QSqlQuery(self.con)
        insertDepths.prepare("INSERT INTO Depth (Depth,PointKey) VALUES (:Depth, :PointKey)")
        insertDepths.bindValue(":PointKey", self.pointID)
        self.con.transaction()
        for depth in depths:
            insertDepths.bindValue(":Depth", str(depth))
            insertDepths.exec()
        self.con.commit()

        #Temperature and heat flows
        fetchDate = QSqlQuery(self.con)
        fetchDate.prepare(f"SELECT Date.ID FROM Date WHERE Date.PointKey = :PointKey AND Date.Date = :Date ")
        fetchDate.bindValue(":PointKey", self.pointID)
        fetchDepth = QSqlQuery(self.con)
        fetchDepth.prepare(f"SELECT Depth.ID FROM Depth WHERE Depth.PointKey = :PointKey AND Depth.Depth = :Depth")
        fetchDepth.bindValue(":PointKey", self.pointID)

        solvedTemps = self.col.get_temps_solve()
        advecFlows = self.col.get_advec_flows_solve()
        conduFlows = self.col.get_conduc_flows_solve()
        times = self.col.get_times_solve()
        
        insertTemps = QSqlQuery(self.con)
        insertTemps.prepare("""INSERT INTO TemperatureAndHeatFlows (Date, Depth, Temperature, AdvectiveFlow, ConductiveFlow, TotalFlow, PointKey, Quantile)
            VALUES (:Date, :Depth, :Temperature, :AdvectiveFlow, :ConductiveFlow, :TotalFlow, :PointKey, :Quantile)""")
        insertTemps.bindValue(":PointKey", self.pointID)
        insertTemps.bindValue(":Quantile", quantileID)
        #We assume solvedTemps,advecFlows and conduFlows have the same shapes, and that the dates and depths are also identical, ie the first column of all three arrays corrresponds to the same fixed date.

        nb_rows,nb_cols = shape(solvedTemps)
        self.con.transaction()
        for j in range(nb_cols):
            fetchDate.bindValue(":Date", datetimeToDatabaseDate(times[j]))
            fetchDate.exec()
            fetchDate.next()
            insertTemps.bindValue(":Date", fetchDate.value(0))
            for i in range(nb_rows):
                fetchDepth.bindValue(":Depth", float(depths[i]))
                fetchDepth.exec()
                fetchDepth.next()
                insertTemps.bindValue(":Depth", fetchDepth.value(0))
                insertTemps.bindValue(":Temperature", float(solvedTemps[i,j])) #Need to convert into float, as SQL doesn't undestand np.float32 !
                insertTemps.bindValue(":AdvectiveFlow", float(advecFlows[i,j]))
                insertTemps.bindValue(":ConductiveFlow", float(conduFlows[i,j]))
                insertTemps.bindValue(":TotalFlow", float(advecFlows[i,j] + conduFlows[i,j]))
                insertTemps.exec()
        self.con.commit()
        
        #Water flows
        waterFlows = self.col.get_flows_solve(depths[0]) #Water flows at the top of the column.
        insertFlows = QSqlQuery(self.con)
        insertFlows.prepare("INSERT INTO WaterFlow (WaterFlow, Date, PointKey, Quantile) VALUES (:WaterFlow,:Date, :PointKey, :Quantile)")
        insertFlows.bindValue(":PointKey", self.pointID)
        insertFlows.bindValue(":Quantile", quantileID)
        self.con.transaction()
        for j in range(nb_cols):
            fetchDate.bindValue(":Date", datetimeToDatabaseDate(times[j]))
            fetchDate.exec()
            fetchDate.next()
            insertFlows.bindValue(":WaterFlow", float(waterFlows[j]))
            insertFlows.bindValue(":Date", fetchDate.value(0))
            insertFlows.exec()
        self.con.commit()

        #RMSE
        sensorsID = self.col.get_id_sensors()
        depthsensors = [depths[i-1] for i in sensorsID] #Python indexing starts a 0 but cells are indexed starting at 1
        computedRMSE = self.col.get_RMSE()
        insertRMSE = QSqlQuery(self.con)
        insertRMSE.prepare("""INSERT INTO RMSE (Depth1, Depth2, Depth3, RMSE1, RMSE2, RMSE3, RMSETotal, PointKey, Quantile)
                 VALUES (:Depth1, :Depth2, :Depth3, :RMSE1, :RMSE2, :RMSE3, :RMSETotal, :PointKey, :Quantile)""")
        insertRMSE.bindValue(":PointKey", self.pointID)
        insertRMSE.bindValue(":Quantile", quantileID)
        
        self.con.transaction()
        for i in range(1,4):
            fetchDepth.bindValue(":Depth", float(depthsensors[i-1]))
            fetchDepth.exec()
            fetchDepth.next()
            insertRMSE.bindValue(f":Depth{i}", fetchDepth.value(0))
            insertRMSE.bindValue(f":RMSE{i}", float(computedRMSE[i-1]))
        insertRMSE.bindValue(":RMSETotal", float(computedRMSE[3]))
        insertRMSE.exec()
        self.con.commit()




    # def saveResults(self):
    #     temps = self.col.temps_solve
    #     times = self.col.times_solve
    #     flows = self.col.flows_solve
    #     advective_flux = self.col.get_advec_flows_solve()
    #     conductive_flux = self.col.get_conduc_flows_solve()
    #     depths = self.col.get_depths_solve()
        
    #     ## Formatage des dates
    #     n_dates = len(times)
    #     times_string = np.zeros((n_dates,1))
    #     times_string = times_string.astype('str')
    #     for i in range(n_dates):
    #         times_string[i,0] = times[i].strftime('%y/%m/%d %H:%M:%S')
        
    #     ## Profondeurs
    #     df_depths = pd.DataFrame(depths, columns=['Depth (m)'])
    #     depths_file = os.path.join(resultsDir, 'depths.csv')
    #     df_depths.to_csv(depths_file, index=False)

    #     ## Profils de températures

    #     # Création du dataframe
    #     np_temps_solve = np.concatenate((times_string, temps), axis=1)
    #     df_temps_solve = pd.DataFrame(np_temps_solve, columns=['Date Heure, GMT+01:00']+[f'Température (K) pour la profondeur {depth:.4f} m' for depth in depths])
    #     # Sauvegarde sous forme d'un fichier csv
    #     temps_solve_file = os.path.join(resultsDir, 'solved_temperatures.csv')
    #     df_temps_solve.to_csv(temps_solve_file, index=False)


    #     ## Flux d'énergie advectifs

    #     # Création du dataframe
    #     np_advective_flux = np.concatenate((times_string, advective_flux), axis=1)
    #     df_advective_flux = pd.DataFrame(np_advective_flux, columns=['Date Heure, GMT+01:00']+[f'Flux advectif (W/m2) pour la profondeur {depth:.4f} m' for depth in depths])
    #     # Sauvegarde sous forme d'un fichier csv
    #     advective_flux_file = os.path.join(resultsDir, 'advective_flux.csv')
    #     df_advective_flux.to_csv(advective_flux_file, index=False)


    #     ## Flux d'énergie conductifs

    #     # Création du dataframe
    #     np_conductive_flux = np.concatenate((times_string, conductive_flux), axis=1)
    #     df_conductive_flux = pd.DataFrame(np_conductive_flux, columns=['Date Heure, GMT+01:00']+[f'Flux conductif (W/m2) pour la profondeur {depth:.4f} m' for depth in depths])
    #     # Sauvegarde sous forme d'un fichier csv
    #     conductive_flux_file = os.path.join(resultsDir, 'conductive_flux.csv')
    #     df_conductive_flux.to_csv(conductive_flux_file, index=False)

    #     ## Flux d'énergie totaux

    #     # Création du dataframe
    #     np_total_flux = np.concatenate((times_string, advective_flux+conductive_flux), axis=1)
    #     df_total_flux = pd.DataFrame(np_total_flux, columns=['Date Heure, GMT+01:00']+[f"Flux d'énergie total (W/m2) pour la profondeur {depth:.4f} m" for depth in depths])
    #     # Sauvegarde sous forme d'un fichier csv
    #     total_flux_file = os.path.join(resultsDir, 'total_flux.csv')
    #     df_total_flux.to_csv(total_flux_file, index=False)


    #     ## Flux d'eau échangés entre la nappe et la rivière

    #     # Création du dataframe
    #     np_flows = np.zeros((n_dates,1))
    #     for i in range(n_dates):
    #         np_flows[i,0] = flows[i]
    #     np_flows_solve = np.concatenate((times_string, np_flows), axis=1)
    #     df_flows_solve = pd.DataFrame(np_flows_solve, columns=["Date Heure, GMT+01:00", "Débit d'eau échangé (m/s)"])
    #     # Sauvegarde sous forme d'un fichier csv
    #     flows_solve_file = os.path.join(resultsDir, 'solved_flows.csv')
    #     df_flows_solve.to_csv(flows_solve_file, index=False)



    # def computeMCMC(self, nb_iter: int, priors: dict, nb_cells: str, quantiles: tuple):
    #     """
    #     Launch the MCMC computation with given parameters.
    #     """
    #     if self.thread.isRunning():
    #         print("Please wait while for the previous computation to end")
    #         return
    
    #     self.setColumn()
    #     self.mcmc_runner = ColumnMCMCRunner(self.col, nb_iter, priors, nb_cells, quantiles)
    #     self.mcmc_runner.finished.connect(self.endMCMC)
    #     self.mcmc_runner.moveToThread(self.thread)
    #     self.thread.started.connect(self.mcmc_runner.run)
    #     self.thread.start()


    # def endMCMC(self):
    #     """
    #     This is called when the MCMC is over.
    #     """

    #     self.thread.quit()
    #     print("MCMC finished")

    #     best_params = self.col.get_best_param()

    #     # Sauvegarde des résultats de la MCMC
    #     resultsDir = os.path.join(self.point.getPointDir(), 'results', 'MCMC_results')
    #     self.saveBestParams(resultsDir)
    #     self.saveAllParams(resultsDir)
        
    #     # Lancement du modèle direct avec les paramètres inférés
    #     self.col.compute_solve_transi(best_params, self.nb_cells)
        
    #     # Sauvegarde des différents résultats du modèle direct
    #     self.saveResults(resultsDir)

    #     # Sauvegarde des quantiles
    #     self.saveFlowWithQuantiles(resultsDir)
    #     self.saveTempWithQuantiles(resultsDir)

    #     self.MCMCFinished.emit()








    def build_column_infos(self):
        """
        Build and return a query giving all the necessary information for the column.
        """
        query  = QSqlQuery(self.con)
        query.prepare(f"""SELECT SamplingPoint.RiverBed, Shaft.Depth1, Shaft.Depth2, Shaft.Depth3, Shaft.Depth4, SamplingPoint.Offset, PressureSensor.Error, Thermometer.Error FROM SamplingPoint
            JOIN PressureSensor
            ON SamplingPoint.PressureSensor = PressureSensor.ID
            JOIN Shaft
            ON SamplingPoint.Shaft = Shaft.ID
            JOIN Thermometer
            ON Shaft.ThermoModel = Thermometer.ID
            JOIN Point
            ON SamplingPoint.ID = Point.SamplingPoint
            WHERE Point.ID = {self.pointID}
        """)
        return query
    
    def build_cleaned_measures(self):
        """
        Build and return a query giving the dates, temperatures and pressure.
        Warning: this is a code duplicate of widgetPoints's build_cleaned_measures.
        """
        query  = QSqlQuery(self.con)
        query.prepare(f"""
                    SELECT Date.Date, CleanedMeasures.Temp1, CleanedMeasures.Temp2, CleanedMeasures.Temp3, CleanedMeasures.Temp4, CleanedMeasures.Pressure, CleanedMeasures.TempBed FROM CleanedMeasures
                    JOIN Date
                    ON CleanedMeasures.Date = Date.ID
                    JOIN Point
                    ON CleanedMeasures.PointKey = Point.ID
                    WHERE Point.ID = {self.pointID}
                    ORDER BY Date.Date
                """)
        return query



# class ComputeBAD(QtCore.QObject):
#     """
#     How to use this class : 
#     - Create a Compute object : compute = Compute(point: Point)
#     - Create an associated Column object : compute.setColumn(sensorDir: str)
#     - Launch the computation :
#         - with given parameters : compute.computeDirectModel(params: tuple, nb_cells: int, sensorDir: str)
#         - with parameters inferred from MCMC : compute.computeMCMC(nb_iter: int, priors: dict, nb_cells: str, sensorDir: str)
#     """
#     MCMCFinished = QtCore.pyqtSignal()
#     DirectModelFinished = QtCore.pyqtSignal()

#     def __init__(self, point: Point=None):
#         # Call constructor of parent classes
#         super(Compute, self).__init__()
#         self.thread = QtCore.QThread()
#         self.point = point
#         self.col = None
    
#     # def setColumn(self, sensorDir: str):
#     #     self.col = self.point.setColumn(sensorDir)
    
        
#     def computeMCMC(self, nb_iter: int, priors: dict, nb_cells: str, sensorDir: str, quantiles: tuple):
        
#         self.nb_cells = nb_cells
#         if self.thread.isRunning():
#             print("Please wait while previous MCMC is finished")
#             return
    
#         # Initialisation de la colonne
#         self.setColumn(sensorDir)
#         self.quantiles = quantiles

#         # Lancement de la MCMC
#         #self.col.compute_mcmc(nb_iter, priors, nb_cells, quantile = (.05, .5, .95))

#         self.mcmc_runner = ColumnMCMCRunner(self.col, nb_iter, priors, nb_cells, quantiles = self.quantiles)
#         self.mcmc_runner.finished.connect(self.endMCMC)
#         self.mcmc_runner.moveToThread(self.thread)
#         self.thread.started.connect(self.mcmc_runner.run)
#         self.thread.start()


#     def endMCMC(self):

#         self.thread.quit()
#         print("MCMC finished")

#         best_params = self.col.get_best_param()

#         # Sauvegarde des résultats de la MCMC
#         resultsDir = os.path.join(self.point.getPointDir(), 'results', 'MCMC_results')
#         self.saveBestParams(resultsDir)
#         self.saveAllParams(resultsDir)
        
#         # Lancement du modèle direct avec les paramètres inférés
#         self.col.compute_solve_transi(best_params, self.nb_cells)
        
#         # Sauvegarde des différents résultats du modèle direct
#         self.saveResults(resultsDir)

#         # Sauvegarde des quantiles
#         self.saveFlowWithQuantiles(resultsDir)
#         self.saveTempWithQuantiles(resultsDir)

#         self.MCMCFinished.emit()
        

#     def computeDirectModel(self, params: tuple, nb_cells: int, sensorDir: str):

#         # Initialisation de la colonne
#         self.setColumn(sensorDir)

#         # Lancement du modèle direct
#         self.col.compute_solve_transi(params, nb_cells)

#         # Sauvegarde des différents résultats du modèle direct
#         resultsDir = os.path.join(self.point.getPointDir(), 'results', 'direct_model_results')
#         self.saveResults(resultsDir)
#         self.saveParams(params, resultsDir)
    

#     def saveParams(self, params: tuple, resultsDir: str):
#         """
#         Sauvegarde les paramètres du modèle direct dans un fichier csv en local
#         Pour accéder au fichier : pointDir --> results --> direct_model_results --> params.csv
#         """

#         params_dict = {
#             'moinslog10K': [params[0]], 
#             'n': [params[1]], 
#             'lambda_s': [params[2]], 
#             'rhos_cs': [params[3]]
#         }

#         df_params = pd.DataFrame.from_dict(params_dict)

#         params_file = os.path.join(resultsDir, 'params.csv')
#         df_params.to_csv(params_file, index=True)
        
#         '''
#         SQL : INSERT INTO Layer (DepthBed) VALUES (1) WHERE id = layer
#         '''
#         '''
#         Not yet possible
        
#         #Open the database
#         db_point = QSqlDatabase.addDatabase("QSQLITE")
#         db_point.setDatabaseNamedb_point.setDatabaseName(r".\..\..\studies\study_2022\molonari_study_2022 .sqlite")
#         if not db_point.open():
#             print("Error: Cannot open databse")
            
#         #Find the id related to the SamplingPoint
#         query_test = QSqlQuery()
#         query_test.exec_(f"SELECT id FROM Point WHERE SamplingPoint = (SELECT id FROM SamplingPoint WHERE PointName = {self.point.getName()})")
#         query_test.first()
#         self.point_id = query_test.value(0)
        
#         #Find the bestParameter related to the id found
#         query_test.exec_(f"SELECT Layer FROM BestParameters WHERE PointKey = {self.point_id}") # Return 1,2,3
#         query_test.first()
#         while True:
#             l = query_test.value(0)
#             query_de_ins = QSqlQuery()
#             query_de_ins.exec_(f"DELETE FROM BestParameters WHERE PointKey = {self.point_id} AND Layer = {l} ")
#             query_de_ins.exe_(f"""
#                               INSERT INTO BestParameters
#                               VALUES {params_dict["moinslog10K"],params_dict["n"],params_dict["lambda_s"],params_dict["rhos_cs"],l,self.point_id}
#                               """)
#             if not (query_test.next()): break
        
#         query_new = QSqlQuery()
#         query_new.exec_(f"""UPDATE Layer SET DepthBed={self.tableWidget.item(id,0).text()} WHERE id = {layer}""")
        
#         db_point.close()   
#         '''
  
#     def saveBestParams(self, resultsDir: str):
#         """
#         Sauvegarde les meilleurs paramètres inférés par la MMC dans un fichier csv en local
#         Pour accéder au fichier : pointDir --> results --> MCMC_results --> MCMC_best_params.csv
#         """

#         best_params = self.col.get_best_param()

#         best_params_dict = {
#             'moinslog10K':[best_params[0]], 
#             'n':[best_params[1]], 
#             'lambda_s':[best_params[2]], 
#             'rhos_cs':[best_params[3]]
#         }

#         df_best_params = pd.DataFrame.from_dict(best_params_dict)

#         best_params_file = os.path.join(resultsDir, 'MCMC_best_params.csv')
#         df_best_params.to_csv(best_params_file, index=True)

#     def saveAllParams(self, resultsDir: str):

#         all_moins10logK = self.col.get_all_moinslog10K()
#         all_n = self.col.get_all_n()
#         all_lambda_s = self.col.get_all_lambda_s()
#         all_rhos_cs = self.col.get_all_rhos_cs()

#         all_params_dict = {
#             'moinslog10K': all_moins10logK, 
#             'n': all_n, 
#             'lambda_s': all_lambda_s, 
#             'rhos_cs': all_rhos_cs
#         }

#         df_all_params = pd.DataFrame.from_dict(all_params_dict)

#         all_params_file = os.path.join(resultsDir, 'MCMC_all_params.csv')
#         df_all_params.to_csv(all_params_file, index=True)
    


#     def saveFlowWithQuantiles(self, resultsDir: str):

#         times = self.col.times_solve

#         flows = self.col.flows_solve
#         #quantile05 = self.col.get_flows_quantile(0.05)
#         #quantile50 = self.col.get_flows_quantile(0.5)
#         #quantile95 = self.col.get_flows_quantile(0.95)
#         QUANTILES = []
#         for quantile in self.quantiles :
#             QUANTILES.append(self.col.get_flows_quantile(quantile))

#         # Formatage des dates
#         n_dates = len(times)
#         times_string = np.zeros((n_dates,1))
#         times_string = times_string.astype('str')
#         for i in range(n_dates):
#             times_string[i,0] = times[i].strftime('%y/%m/%d %H:%M:%S')

#         # Création du dataframe
#         np_flows_quantiles = np.zeros((n_dates,len(QUANTILES)+1))
#         for i in range(n_dates):
#             np_flows_quantiles[i,0] = flows[i]
#             for k in range(len(QUANTILES)):
#                 np_flows_quantiles[i,k+1] = QUANTILES[k][i]
#         np_flows_times_and_quantiles = np.concatenate((times_string, np_flows_quantiles), axis=1)
#         columns_names = ["Date Heure, GMT+01:00", 
#         "Débit d'eau échangé (m/s) - pour les meilleurs paramètres"]
#         for quantile in self.quantiles :
#             columns_names.append(f"Débit d'eau échangé (m/s) - quantile {quantile}")
#         df_flows_quantiles = pd.DataFrame(np_flows_times_and_quantiles, 
#         columns=columns_names)
    
#         # Sauvegarde sous forme d'un fichier csv
#         flows_quantiles_file = os.path.join(resultsDir, 'MCMC_flows_quantiles.csv')
#         df_flows_quantiles.to_csv(flows_quantiles_file, index=False)
    

#     def saveTempWithQuantiles(self, resultsDir: str):
        
#         times = self.col.times_solve

#         dataframe_list = []

#         # Formatage des dates
#         n_dates = len(times)
#         times_string = np.zeros((n_dates,1))
#         times_string = times_string.astype('str')
#         for i in range(n_dates):
#             times_string[i,0] = times[i].strftime('%y/%m/%d %H:%M:%S')

#         for l in range(self.col.temps_solve.shape[1]):

#             temp = self.col.temps_solve[:,l] #température à la lème profondeur
#             QUANTILES = []
#             for quantile in self.quantiles :
#                 QUANTILES.append(self.col.get_temps_quantile(quantile)[:,l])

#             # Création du dataframe
#             np_temps_quantiles = np.zeros((n_dates,len(QUANTILES)+1))
#             for i in range(n_dates):
#                 np_temps_quantiles[i,0] = temp[i]
#                 for k in range(len(QUANTILES)):
#                     np_temps_quantiles[i, k+1] = QUANTILES[k][i]

#             np_temps_times_and_quantiles = np.concatenate((times_string, np_temps_quantiles), axis=1)
#             columns_names = ["Date Heure, GMT+01:00", 
#             f"Température à la profondeur {l} (K) - pour les meilleurs paramètres"]
#             for quantile in self.quantiles :
#                 columns_names.append(f"Température à la profondeur {l} (K) - quantile {quantile}") #À modifier pour avoir les vrais noms
#             df_temps_quantiles = pd.DataFrame(np_temps_times_and_quantiles, 
#             columns=columns_names)
#             dataframe_list.append(df_temps_quantiles)

#         df_temps_quantiles = dataframe_list[0]
#         for i in range (1, len(dataframe_list)) :
#             dataframe = dataframe_list[i]
#             df_temps_quantiles = pd.concat([df_temps_quantiles, dataframe[dataframe.columns[1:]]], axis=1)
#         # Sauvegarde sous forme d'un fichier csv
#         temps_quantiles_file = os.path.join(resultsDir, 'MCMC_temps_quantiles.csv')
#         df_temps_quantiles.to_csv(temps_quantiles_file, index=False)


#     def saveResults(self, resultsDir: str):

#         """
#         Sauvegarde les différents résultats calculés sous forme de fichiers csv en local :
#         - profils de températures calculés aux différentes profondeurs
#         - chronique des flux d'eau échangés entre la nappe et la rivière

#         Les résultats sont disponibles respectivement dans les fichiers suivants :
#         - pointDir --> results --> solved_temperatures.csv
#         - pointDir --> results --> solved_flows.csv

#         Prend en argument :
#         - la colonne sur laquelle les calculs ont été faits (type: Column)
#         - le chemin d'accès vers le dossier 'results' du point (type: str)
#         Ne retourne rien
#         """
        
#         temps = self.col.temps_solve
#         times = self.col.times_solve
#         flows = self.col.flows_solve
#         advective_flux = self.col.get_advec_flows_solve()
#         conductive_flux = self.col.get_conduc_flows_solve()
#         depths = self.col.get_depths_solve()
        
#         ## Formatage des dates
#         n_dates = len(times)
#         times_string = np.zeros((n_dates,1))
#         times_string = times_string.astype('str')
#         for i in range(n_dates):
#             times_string[i,0] = times[i].strftime('%y/%m/%d %H:%M:%S')
        
#         ## Profondeurs
#         df_depths = pd.DataFrame(depths, columns=['Depth (m)'])
#         depths_file = os.path.join(resultsDir, 'depths.csv')
#         df_depths.to_csv(depths_file, index=False)

#         ## Profils de températures

#         # Création du dataframe
#         np_temps_solve = np.concatenate((times_string, temps), axis=1)
#         df_temps_solve = pd.DataFrame(np_temps_solve, columns=['Date Heure, GMT+01:00']+[f'Température (K) pour la profondeur {depth:.4f} m' for depth in depths])
#         # Sauvegarde sous forme d'un fichier csv
#         temps_solve_file = os.path.join(resultsDir, 'solved_temperatures.csv')
#         df_temps_solve.to_csv(temps_solve_file, index=False)


#         ## Flux d'énergie advectifs

#         # Création du dataframe
#         np_advective_flux = np.concatenate((times_string, advective_flux), axis=1)
#         df_advective_flux = pd.DataFrame(np_advective_flux, columns=['Date Heure, GMT+01:00']+[f'Flux advectif (W/m2) pour la profondeur {depth:.4f} m' for depth in depths])
#         # Sauvegarde sous forme d'un fichier csv
#         advective_flux_file = os.path.join(resultsDir, 'advective_flux.csv')
#         df_advective_flux.to_csv(advective_flux_file, index=False)


#         ## Flux d'énergie conductifs

#         # Création du dataframe
#         np_conductive_flux = np.concatenate((times_string, conductive_flux), axis=1)
#         df_conductive_flux = pd.DataFrame(np_conductive_flux, columns=['Date Heure, GMT+01:00']+[f'Flux conductif (W/m2) pour la profondeur {depth:.4f} m' for depth in depths])
#         # Sauvegarde sous forme d'un fichier csv
#         conductive_flux_file = os.path.join(resultsDir, 'conductive_flux.csv')
#         df_conductive_flux.to_csv(conductive_flux_file, index=False)

#         ## Flux d'énergie totaux

#         # Création du dataframe
#         np_total_flux = np.concatenate((times_string, advective_flux+conductive_flux), axis=1)
#         df_total_flux = pd.DataFrame(np_total_flux, columns=['Date Heure, GMT+01:00']+[f"Flux d'énergie total (W/m2) pour la profondeur {depth:.4f} m" for depth in depths])
#         # Sauvegarde sous forme d'un fichier csv
#         total_flux_file = os.path.join(resultsDir, 'total_flux.csv')
#         df_total_flux.to_csv(total_flux_file, index=False)


#         ## Flux d'eau échangés entre la nappe et la rivière

#         # Création du dataframe
#         np_flows = np.zeros((n_dates,1))
#         for i in range(n_dates):
#             np_flows[i,0] = flows[i]
#         np_flows_solve = np.concatenate((times_string, np_flows), axis=1)
#         df_flows_solve = pd.DataFrame(np_flows_solve, columns=["Date Heure, GMT+01:00", "Débit d'eau échangé (m/s)"])
#         # Sauvegarde sous forme d'un fichier csv
#         flows_solve_file = os.path.join(resultsDir, 'solved_flows.csv')
#         df_flows_solve.to_csv(flows_solve_file, index=False)


