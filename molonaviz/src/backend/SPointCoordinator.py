from asyncio import selector_events
from select import select
from PyQt5.QtSql import QSqlQueryModel, QSqlQuery, QSqlDatabase #QSqlDatabase in used only for type hints
from src.backend.GraphsModels import PressureDataModel, TemperatureDataModel, SolvedTemperatureModel, HeatFluxesModel, WaterFluxModel, ParamsDistributionModel

class SPointCoordinator:
    """
    A concrete class to handle communication between the database and the views in the window displaying a sampling point's results.
    This class can:
        -return informations about the current sampling point
        -manage, fill and clear all models in the subwindow
        -deal with end user's actions in the subwindow. Currently, this means SPointCoordinator can insert cleaned measures in the database.
    This class does not:
        -interact with the pyheatmy module. For this purpose, see Compute.
    """
    def __init__(self, con : QSqlDatabase, studyName : str, samplingPointName : str):
        self.con = con

        spointID_query = self.build_sampling_point_id(studyName, samplingPointName)
        spointID_query.exec()
        spointID_query.next()
        self.samplingPointID = spointID_query.value(0)

        self.pointID = self.findOrCreatePointID()

        #Create all models (empty for now)
        self.pressuremodel = PressureDataModel([])
        self.tempmodel = TemperatureDataModel([])
        self.tempmap_model = SolvedTemperatureModel([])
        self.fluxes_model = HeatFluxesModel([])
        self.waterflux_model = WaterFluxModel([])
        self.paramsdistr_model = ParamsDistributionModel([])
    
    def findOrCreatePointID(self):
        """
        Return the Point ID corresponding to this sampling point OR if this is the first time this sampling point is opened, create the relevant entry in the Point table.
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
    
    def getPressureModel(self):
        return self.pressuremodel
    
    def getTempModel(self):
        return self.tempmodel
    
    def getTempMapModel(self):
        return self.tempmap_model
    
    def getWaterFluxesModel(self):
        return self.waterflux_model
    
    def getFluxesModel(self):
        return self.fluxes_model
    
    def getParamsDistrModel(self):
        return self.paramsdistr_model
    
    def getSPointInfos(self):
        """
        Return the path to the scheme, the path to notice and a model containing the informations about the sampling point.
        """
        select_paths, select_infos = self.build_infos_queries()
        #Installation image
        select_paths.exec()
        select_paths.next()
        schemePath = select_paths.value(0)
        noticePath = select_paths.value(1)

        select_infos.exec()
        infosModel = QSqlQueryModel()
        infosModel.setQuery(select_infos)

        return schemePath, noticePath, infosModel
    
    def getParamsModel(self, layer : float):
        """
        Given a layer (identified by its depth), return the associated best parameters.
        """
        select_params = self.build_params_query(layer)
        select_params.exec()
        self.paramsModel = QSqlQueryModel()
        self.paramsModel.setQuery(select_params)
    
    def getTableModel(self, raw_measures : bool):
        """
        Return a model with all direct information from the database.
        If raw_measures is true, the raw measures from the point are displayed, else cleaned measures are displayed
        """
        if raw_measures:
            select_query = self.build_raw_measures(full_query=True)
        else:
            select_query = self.build_cleaned_measures(full_query=True)
        select_query.exec()
        self.tableModel = QSqlQueryModel()
        self.tableModel.setQuery(select_query)
        return self.tableModel 
    
    def allCleanedMeasures(self):
        """
        Return the cleaned measures in an iterable format. The result is a list of tuple:
        -the first element is a list holding temperature readings (date, Temp1, Temp2, Temp3, Temp4)
        -the second element is a list holding pressure readings (date, pressure, temperature)
        """
        select_data = self.build_cleaned_measures(full_query=True)
        result = []
        while select_data.next():
            result.append(([select_data.value(i) for i in range(5)],[select_data.value(0), select_data.value(6),select_data.value(5)]))
        return result
    
    def layersDepths(self):
        """
        Return a list with all the depths of the layers. It may be empty.
        """
        select_depths_layers = self.build_layers_query()
        select_depths_layers.exec()
        layers = []
        while select_depths_layers.next():
            layers.append(select_depths_layers.value(0))
        return layers
    
    def allRMSE(self):
        """
        Return
        -a dictionnary where the keys are the quantile (with the convention 0 = Direct model) and values are associated RMSE.
        -a list corresponding to the RMSE of the three thermometers
        """
        select_globalRMSE = self.build_global_RMSE_query()
        select_globalRMSE.exec()
        gloablRmse = {}
        while select_globalRMSE.next():
            gloablRmse[select_globalRMSE.value(0)] = select_globalRMSE.value(1)
        
        select_thermRMSE = self.build_therm_RMSE()
        select_thermRMSE.exec()
        select_thermRMSE.next()

        return gloablRmse, [select_thermRMSE.value(i) for i in range(3)]
    
    def thermoDepth(self, depth_id : int):
        """
        Given a thermometer number (1, 2, 3), return depth of associated thermometer.
        """
        select_thermo_depth = self.build_thermo_depth(depth_id)
        select_thermo_depth.exec()
        select_thermo_depth.next()
        return select_thermo_depth.value(0)
    
    def refreshMeasuresPlots(self, raw_measures):
        """
        Refresh the models displaying the measures in graphs.
        If raw_measures is true, then the raw measures will be displayed, else cleaned measures will be shown.
        """
        if raw_measures:
            select_pressure = self.build_raw_measures(field ="Pressure")
            select_temp = self.build_raw_measures(field ="Temp")
        else:
            select_pressure = self.build_cleaned_measures(field ="Pressure")
            select_temp = self.build_cleaned_measures(field ="Temp")

        self.pressuremodel.newQueries([select_pressure])
        self.tempmodel.newQueries([select_temp])

    def refreshParamsDistr(self, layer : float):
        """
        Refresh the parameter distribution model for the given layer.
        """
        select_params = self.build_params_distribution(layer)
        self.paramsdistr_model.newQueries([select_params])
    
    def refreshAllModels(self, raw_measures_plot : bool, layer : float):
        """
        Refresh all models.
        If some models have their own function to be refreshed, then these functions should be called to prevent code duplication
        """
        self.refreshMeasuresPlots(raw_measures_plot)
        
        #Plot the heat fluxes
        select_heatfluxes= self.build_result_queries(result_type="2DMap",option="HeatFlows") #This is a list
        select_depths = self.build_depths()
        select_dates = self.build_dates()
        self.fluxes_model.newQueries([select_dates,select_depths]+select_heatfluxes)

        #Plot the water fluxes
        select_waterflux= self.build_result_queries(result_type="WaterFlux") #This is already a list
        self.waterflux_model.newQueries(select_waterflux)

        #Plot the temperatures
        select_tempmap = self.build_result_queries(result_type="2DMap",option="Temperature") #This is a list of temperatures for all quantiles
        select_depths = self.build_depths()
        select_dates = self.build_dates()
        self.tempmap_model.newQueries([select_dates,select_depths]+select_tempmap)

        #Histogramms
        self.refreshParamsDistr(layer)
    
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
    
    def build_sampling_point_id(self, studyName : int | str, spointName : str):
        """
        Build and return a query giving the ID of the sampling point called spointName in the study with the name studyName.
        """
        query = QSqlQuery(self.con)
        query.prepare(f"""SELECT SamplingPoint.ID FROM SamplingPoint
                        JOIN Study 
                        ON SamplingPoint.Study = Study.ID
                        WHERE Study.Name = '{studyName}' AND SamplingPoint.Name = '{spointName}'""")
        return query
    
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
    
    def build_params_query(self, depth : float):
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
    
    def build_params_distribution(self, layer : float):
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
    
    def build_global_RMSE_query(self):
        """
        Build and return all the quantiles as well as the associated global RMSE.
        """
        query = QSqlQuery(self.con)
        query.prepare(f"""
            SELECT Quantile.Quantile, RMSE.RMSETotal FROM RMSE 
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
    
    def build_insert_point(self):
        """
        Build and return a query creating a Point. For now, most fields are empty.
        """
        query = QSqlQuery(self.con)
        query.prepare(f""" INSERT INTO Point (SamplingPoint)  VALUES (:SamplingPoint)
        """)
        return query