# Molonaviz - Technical guide

## Table of contents
- [Overview](#overview)
- [The backend-frontend distinction](#the-backend-frontend-distinction)
- [API](#api)


## Overview
This is Molonaviz's technical guide. If you are an end user, this is probably not the documentation you are looking for, and you should instead refer to the user guide.

This documents details the current structure of Molonaviz's backend and frontend, as well as the interactions between them (a brief API). Any changes in this API should be written down here so that future maintainers of the project have a clear document giving all the conventions.

This document also lists additional features which could be implemented, remarks or issues, and a few unresolved bugs.

This application is loosely based on the work done during the 2022 edition of the engineering trimester Molonari. However, it was initially entirely reworked Guillaume Vigne during the months following this trimester. Its main purpose is to be enhanced by future editions of the Molonari project.

If you want to get the general ideas about the backend and frontend for this app, you should refer [to this part of the documentation](#the-backend-frontend-distinction). If you prefer to dive directly into API consideration, [see the dedicated paragraphs in the documentation](#api).


## The backend-frontend distinction
### Roles and responsabilities
The Molonaviz app has been divided into two parts: one is the *backend*, which manages the computations and data storage, and the other is the *frontend* which is responsible for displaying graphs corresponding to the computations.

### Backend
The backend has three big responsabilities:
- it is interfaced with the pyheatmy module, and is thus responsible of calling the appropriate methods to compute results.
- it must be able to store and manage information about a virtual laboratory, a virtual study, and the associated detectors' technical specificities.
- it must be able to store the raw measures from detectors, the given cleaned measures and different types of computations. These computations are essentially time series.

Currently, the storage method used is a SQL database. The ERD is given in the *docs* folder.

#### Database structure
The database is mostly divided into two parts: one for managing virtual labs and studies, and one for computations. A laboratory is essentially a set of detectors: currently there are only two types of detectors, pressure sensors and shafts (used to measure temperature). It should be relatively easy to add new detectors simply by creating the associated table with a foreign key onto the laboratory table.

*Note*: a shaft and a pressure sensor are physical detectors (something that will be placed in the river). They both have a thermometer to measure the river's temperature. The thermometer's model is stored in the Thermometer table, as they can have their own specificities (such as error or uncertainties), which can be distinct from the physical detector's specificities.

A sampling point represents a physical place where physical detectors have been placed. Currently, this means that sampling points are places where one (and only one) pressure sensor and one (and only one) shaft have been placed in a river. These detectors must come from the same laboratory. A study is a combination of sampling points and one laboratory.

For each sampling point, there exists a point, which is a virtual object used to encompass all computations. A sampling point represents the physical implementation and gives raw measures from the river; a point represents all processed data coming from theses measures. Adding a new type of computation comes to adding new tables with a foreign key on the Point table, although one must respect a few conventions:
- The Quantile table is used to know if a MCMC or a direct model has been launched. See [Conventions](#conventions).
- To reduce the amount of data stored, the depths and dates have their own table. This way, for each time series, instead of storing two arrays (array of dates and array of data), only one needs to be stored. This can be done because all computations share the same time scale.
- The Layer table follows the same idea. Since it is used both for the parameters distribution (histograms) and for the best parameters (4 values which correspond to the model with minimum of energyS), it has been set in its own table.

The database structure could be greatly criticised, as it is not a great format to store scientific data. Storing such data leads to a database rapidly growing in size, as well as an increasing time complexity. This is further enhanced by PyQt5's way to do queries, as QSqlQuery objects are not iterable. This means that whenever we need to access data, we must:
- query the database via a `QSqlQuery` object
- convert the `QSqlQuery` into a list by manually calling `next()`

Overall, the database structure is not a good choice as it is very slow and impractical to use. However, it forces us to structure the data and have a clear overview of what should or shouldn't be stored.

A more convenient way to store this data would be to use dedicated structures, such as the excellent HDF5 (which has a great Python API): the computation part of the database would be much easier to use, and with some work, the laboratory could also be stored.

### Frontend
The frontend handles communication with the end user using a User Interface (UI). For now, the UI is made using PyQt5. The frontend must be able to
- collect information from the end user and pass it to the backend in a correct format (see API)
- display the computations in graphs by using models
- verify and process the times series. Accordind to the user's choices, the frontend should be able to genereate a time serie corresponding to processed (often denoted as "cleaned") measures, for example by removing anormal points or applying standard treatments (IQR, Z-score) to the raw measures.

#### Frontend organisation
When the user launches Molonaviz, the first thing he has access to is the main window. This is the window responsible for dispatching specific actions to other parts of the code. The main window allows the user to:
- manage virtual laboratories
- manage virtual studies
- open points to view the results
Many actions are automatically done by the models (see API). These models do not require specific instructions to be refreshed, and are instead refreshed whenever the backend register changes.

The SamplingPointViewer is the window which displays all results from a specific sampling point from a study. It is also heavily built on models so that as many things as possible are done automatically. It features a cleanup window to allow end-user to process the raw data from the sensors. The goal of this cleanup window is not to allow any type of processing. Instead, it features a few simple processing (currently Z-score and IQR), allows the user to manually remove nonsensical points, but also select a specific time period. If the end-user whishes to make complex processing, he should instead export the raw measures, process them on his own using whatever method he whishes, then import the cleaned measures into Molonaviz. This is a touchy operation, as the user could make mistakes such as change the name of the columns or put NaNs in the dataframes.

## API
### A few conventions

By default, the backend functions use snake case (snake_case), whereas as frontend functions use camel case (camelCase). Dates are in format ... (Quantile = 0 -> direct model => shouldnt need this!)
Dataframes: cleaned by frontend or may fail.
May fail = either return a strange value or raise unexpected and uncatched error.
Dataframe sensor convention.
sampling point dataframes convention
refresh_spoints = should be used after subscribing to a model or when the user wants to see somthing else (cf rawcheckbox)

### High-level communication methods
#### Models and Views
In order to reduce the amount of code, increase clarity, and prevent nasty bugs, a model/view system has been implemented.

A model is a backend object which can store data. A view is a frontend object which displays data nicely. Views can subscribe to a model: whenever the model has its inner data changed, it notifies all subscribed views that something happened: this is done by emitting a custom pyqt signal called *dataChanged*. It is up to the views to see how they should change their behaviour when receiving the *dataChanged* signal: a model is blind and doesn't need to know who has subscribed to it. Therefore, a model can have any number of registered views; however, a view may only be subscribed to one model.

From a backend perspective, a model doesn't have to do much. It should only implement various getters to return data in a "nice" way (usually list or numpy arrays). A model simply provides data, and has no interest or knowledge of its views.

From a frontend perspective, a view is responsible for subscribing to a specific model. This is done with the `register` method: alternatively, a view could choose to unsubscribe from its model using the `unregister`, although this is not recommended at all. The recommended way to use a view is to create an instance of the view by giving it a model, and not use the methods making the link between the models and the views. Views should always inherit from `MoloView`: on creation, it automatically registers the view to a model if one is given.

From a developper perspective, to implement a new feature:
- create the backend object inheriting from `MoloModel`, the highest abstract class representing a model. This new model should implement:
    - different getters for the frontend
    - if the model has to have some sort of internal data (a list, a dataframe...), then it should implement the `update_data` and `reset_data` functions, which respectively update the inner data when new queries are being executed, and delete all inner data when clearing the model.
- create a frontend object inheriting from `MoloView`, the highest abstract class representing a view. The view may also inherit from other objects: for example, the `GraphView` is a view which can display time series on a matplotlib canvas. It should implement at least:
    - the `on_update` function, which is called whenever the *dataChanged* signal is catched.
    - the `retrieve_data` function which uses the associated model's getters to fetch information
    - the `rest_data` function which clears all internal data in the view (ie revert it to a blank state).
- to use the new view and model, one has to create an instance of the new view by giving it the appropriate instance of the new model. The frontend can now implement aditionnal features (such as matplotlib features) to present data in a nice way.

**There should be no need to change the way views and models communicate with each other (*dataChanged* signal, `register` and `unregister`,`exec`...)**

It is highly recommended to take a look at the `MoloModel` and `MoloView` classes to understand the big structure behind this model/view architecture.

#### Containers and enumerations
Containers are objects allowing an easy communication between backend and frontend: sometimes, structured information must be exchanged, and containers are here just for this. Containers shouldn't be used for non structured data (for example time series). Containers are mostly fancy classes which mimick a dictionnary or a named tuple. Their only goal is to have a list of attributes which can be easily read, and they do not have any method. For example, Molonaviz has to deal with thermometers which have different attributes, such as a brand, a name, an accuracy error... To hold all of these informations, a Thermometer object has been created which contains just what is required to describe a thermometer.

Enumerations are an other way to communicate between backend and frontend. Instead of having error codes (like error 404, 500...), Molonaviz uses enumerations which hide these error codes: from a programmer perpective, we use strings instead, like `RAW_MEASURES`. Currently, this is only used to know which type of computation has been made.

### Low-level API
Here is a list of low-level backend functionalities which can be used by the frontend.

**StudyAndLabManager**: an instance of the StudyAndLabManager class handles high-order operations such as adding a laboratory or creating a new study.
- *Instantiation*
    - ```StudyAndLabManager(con : QSqlDatabase)```. This class requires a connection to the database.
- *Creating*
    - ```create_new_study(studyName : str, labName : str) -> None```:  create a new study with the given name attached to the given laboratory. The laboratory must exist, or this function may fail.
    - ```create_new_lab(labName : str, thermometersDF : list[pd.DataFrame], psensorsDF : list[pd.DataFrame], shaftsDF : list[pd.DataFrame]) -> None```: create a new laboratory with the given sensors. The laboratory name must be new (no other laboratory should have this name) or this function may fail. The lists passed as arguments contains the relevant information for each sensor (one dataframe = one sensor) and must respect the sensor dataframes [conventions](#conventions), or this function may fail.
- *Miscellaneous*
    - ```is_study_in_database(studyName : str)```: Return True if a study with the given name is in the database.
    - ```get_study_names()``` Return a list of all the names of the registered studies.
    - ```get_lab_names(studyName : str|None = None -> list[str])``` Return a list of all the names of the registered laboratories. If the argument studyName is not None, instead return a list whose only element is the name of laboratory attached to the study. This argument must be the name of an existing study, or this function may fail.

**LabEquipementManager**: an instance of the LabEquipementManager class handles operations on the detectors in a specific laboratory (refered to as "current" laboratory).
- *Instantiation*
    - ```LabEquipementManager(con : QSqlDatabase, labName : str)```. This class requires a connection to the database and the name of an existing laboratory. This class will not behave properly if no laboratory with the given name exists.
- *Getting models*
    - ```get_thermo_model() -> ThermometersModel```: return the thermometers model.
    - ```get_psensor_model() -> PressureSensorsModel```: return the pressure sensors model.
    - ```get_shaft_model() -> ShaftsModel```:  return the shafts model.
- *Getting names*
    - ```get_psensors_names() -> list[str]```: return a list of the names of all existing pressure sensors in the current laboratory.
    - ```get_shafts_names() -> list[str]```: return a list of the shafts of all existing shafts in the current laboratory.
- *Refreshing models*
    - ```refresh_detectors() -> None```: this functions forces the backend to refresh the three detectors models.

**SamplingPointManager**: an instance of the SamplingPointManager class handles operations on the sampling points in a specific study (refered to as "current" study).
- *Instantiation*
    - ```SamplingPointManager(con : QSqlDatabase, studyName : str)```. This class requires a connection to the database and the name of a study . This class will not behave properly if no study with the given name exists.
- *Creatin a new sampling point*
    -  ```create_new_spoint(pointName : str, psensorName : str, shaftName :str, noticefile : str, configfile : str, infoDF : pd.DataFrame, rawVoltage : pd.DataFrame, rawTemp : pd.DataFrame`) -> None```: create a new sampling with the given information. The sampling point name must be new (no other sampling point in the current study should have this name) or this function may fail. The associated detectors must also exist in the laboratory associated with the study, or this function may fail. The three dataframes (information about the calibration, raw voltage, and raw temperatures) must respect the sampling point dataframes [conventions](#conventions), or this function may fail.
- *Getting the sampling point model*
    - ```get_spoint_model() -> SamplingPointModel```: return the sampling point model.
- *Refreshing models*
    - ```refresh_spoints() -> None```: this functions forces the backend to refresh the sampling point model.
- *Miscellaneous*
    - ```get_spoints_names() -> list[str]```: return a list of the names of all existing sampling points in the current study.
    - ```get_spoint(spointName : str) -> None``` return a SamplingPoint container representing the sampling point with the given name. This function will fail if no sampling point with the given name exist in the current study.

**SPointCoordinator**: an instance of the SPointCoordinator class handles operations on a specific sampling points (refered to as "current" sampling point).
- *Instantiation*
    - ```SamplingPointManager(con : QSqlDatabase, studyName : str, samplingPointName : str)```. This class requires a connection to the database, the name of a study and the name of a sampling point. This class will not behave properly if no study with the given name exist or no sampling point with the given name exist.
- *Getting models*
    - ```get_pressure_model() -> PressureDataModel```: return the voltage/pressure model.
    - ```get_temp_model() -> TemperatureDataModel```: return the raw measures/cleaned measures temperature model.
    - ```get_water_fluxes_model() -> WaterFluxModel```: return the water flux model.
    - ```get_temp_map_model() -> SolvedTemperatureModel```: return the solved temperatures model.
    - ```get_heatfluxes_model() -> HeatFluxesModel```: return the heat fluxes model (advective, conductive, total).
    - ```get_params_distr_model() -> ParamsDistributionModel```: return the parameters distrbution model.
    - ```get_params_model(layer : float) -> QSqlQueryModel```: this function requires the depth of a layer: if this depth (ie an element of ```layers_depths()```) then this function may fail. Return a model containing the 4 best parameters computed during the MCMC for this layer.
    - ```get_table_model(rawMeasures : bool) -> QSqlQueryModel```: return a table model containing all the measures for all physical quantities. This function requires a boolean: if it is True, then raw measures will be returned; if it is False, then cleaned measures will be returned.
- *Refreshing models*
    - ```refresh_measures_plots(raw_measures : bool) -> None```: this functions forces the backend to refresh the models displaying the measures in graphs. This function requires a boolean: if it is True, then the raw measures will be displayed; if it is False, cleaned measures will be shown.
    - ```refresh_params_distr(layer : float) -> None```: this functions forces the backend to refresh the parameter distribution model for the given layer.
    - ```refresh_all_models(raw_measures_plot : bool, layer : float) -> None```: this functions forces the backend to refresh all the models displaying the measures in graphs. It starts by calling ```refresh_measures_plots``` and ```refresh_params_distr```, then also refreshes all the others models displaying computed data.
- *Getting directly the measures*
    - ```all_raw_measures() -> list[list]```: return the raw measures in an iterable format (as a list of lists). The inner lists hold the following information in the given order: date (respecting the date [conventions](#conventions)), temperature at the first depth, temperature at the second depth, temperature at the third depth, temperature at the fourth depth, temperature at the river bed, voltage.
    - ```all_cleaned_measures() -> list[list], list[list]```: return the cleaned measures in an iterable format (as list of lists). The first element returned is a list holding temperature readings: date (respecting the date [conventions](#conventions)), temperature at the first depth, temperature at the second depth, temperature at the third depth, temperature at the fourth depth. The second element returned is a list holding pressure readings: date (respecting the date [conventions](#conventions)), pressure, temperature ar the river bed.
- *Miscellaneous*
    - ```get_spoint_infos() -> str, str, QSqlQueryModel```: return the path to the scheme, the path to notice and a model containing the informations (calibration date, location...) about the sampling point.
    - ```layers_depths() -> list[float]```: return a list with all the depths of the layers for the given sampling point.
    - ```all_RMSE() -> float, dict[float : float], list[float]```: the first element returned is the RMSE for the direct model. The second if a dictionnary where the keys are the quantile and values are associated RMSE (it may be empty is the MCMC hasn't been computed). The last element returned is a list holding the RMSE of the three thermometers.
    - ```thermo_depth(depth_id : int) -> float```: this functions requires a thermometer number (1, 2, 3). Return the depth of the corresponding thermometer.
    - ```max_depth() -> float```: return the altitude of the deepest point in the river.
    - ```calibration_infos() -> float, float, float```: return three values corresponding to the intercept, the differential pressure (Du/DH), and differential temperature (Du/DT).

**ThermometersModel**: an instance of the ThermometersModel class gives information relative to the existing thermometers in a laboratory.
- *Getting containers*
    - ```get_all_thermometers() -> list[Thermometer]```: return the a list of ```Thermometers``` containers representing all existing thermometers in the current laboratory with the relevant information.

**PressureSensorsModel**: an instance of the PressureSensorsModel class gives information relative to the existing pressure sensors in a laboratory.
- *Getting containers*
    - ```get_all_psensors() -> list[PSensor]```: return the a list of ```PSensor``` containers representing all existing pressure sensors in the current laboratory with the relevant information.

**ShaftsModel**: an instance of the ShaftsModel class gives information relative to the existing shafts in a laboratory.
- *Getting containers*
    - ```get_all_shafts() -> list[Shaft]```: return the a list of ```Shaft``` containers representing all existing shafts in the current laboratory with the relevant information.

**SamplingPointModel**: an instance of the SamplingPointModel class gives information relative to the existing sampling points in a study.
- *Getting containers*
    - ```get_all_sampling_points() -> list[SamplingPoint]```: return the a list of ```SamplingPoint``` containers representing all existing sampling points in the current study with the relevant information.

**PressureDataModel**: an instance of the PressureDataModel class gives times series corresponding to the voltages measured by the pressure sensors. The backend can also force an instance of this class to give instead the times series corresponding to the pressure (ie cleaned measures, as it is during cleanup that the conversion Voltage -> Pressure takes place).
- *Getting time series*
    - ```get_pressure() -> numpy.array```: return an array containing all voltage measures (or pressure measures if data has been cleaned).
    - ```get_dates() -> numpy.array```: return an array of the dates where the measures took place, respecting the date [conventions](#conventions).

**TemperatureDataModel**: an instance of the TemperatureDataModel class gives times series corresponding to the temperatures measured by the pressure sensors: theses measures can either be raw or cleaned.
- *Getting time series*
    - ```get_temperatures() -> numpy.array```: return an array containing all temperatures measures.
    - ```get_dates() -> numpy.array```: return an array of the dates where the measures took place, respecting the date [conventions](#conventions).

**WaterFluxModel**: an instance of the WaterFluxModel class gives times series the water fluxes.
- *Getting time series*
    - ```get_water_flow() -> numpy.array, dict[float : numpy.array]```: the first element returned is an array containing the water flows for the direct model: it can be empty if no direct model has been computed yet. The second element is a dictionnary with keys beings the quantiles and values being the arrays of associated flows:: it can be empty if the MCMC hasn't been computed yet.
    - ```get_dates() -> numpy.array```: return an array of the dates corresponding to the time series, respecting the date [conventions](#conventions).

**SolvedTemperatureModel**: an instance of the SolvedTemperatureModel class gives the solved temperatures computed by the direct model (or the direct model with best params if the MCMC has been used) as a function of depth and time.
- *Getting time series*
    - ```get_temperatures_cmap(quantile : float) -> numpy.array```: this function requires a quantile (ie a float) to be passed as argument. Returns the heatmap (2D array) corresponding to this quantile. A row corresponds to a fixed depth. A column corresponds to a fixed date. To ask for the direct model, instead pass ```0``` as argument. Note: for now this is mostly useless as we do not store the heatmpas computed for a quantile other than the direct model.
    - ```get_depths() -> numpy.array```: return an array of all the depths considered for this heatmap
    - ```get_dates() -> numpy.array```: return an array of all the dates considered for this heatmap, respecting the date [conventions](#conventions).
    - ```get_temp_by_date(date, quantile : float) -> numpy.array```: return the temperatures for a given date and quantile. The date must respect the date [conventions](#conventions), and must be precisely a date considered for the heatmap (ie it must be an element of the list returned by ```get_dates```) To ask for the direct model, pass ```0``` as argument for the quantile.
    - ```get_depth_by_temp(nb_dates : int) -> numpy.array, dict[int : numpy.array]```: return a number equal to ```nb_dates``` of equally spaced series of the temperature as a function of the depth. The first element returned is an array of the common depths for all these series. The second is a dictionnaries whose keys are the equally spaced dates, and values are arrays corresponding to the temperature values.

**HeatFluxesModel**: an instance of the HeatFluxesModel class gives the advective, conductive and total heat fluxes as functions of depth and time.
- *Getting time series*
    - ```get_depths() -> numpy.array```: return an array of all the depths considered for the fluxes
    - ```get_dates() -> numpy.array```: return an array of all the dates considered for the fluxes, respecting the date [conventions](#conventions).
    - ```get_advective_flow() -> numpy.array``` return the advective flow as a function of both time and depth (2D array). A row corresponds to a fixed depth. A column corresponds to a fixed date.
    - ```get_conductive_flow() -> numpy.array``` return the conductive flow as a function of both time and depth (2D array). A row corresponds to a fixed depth. A column corresponds to a fixed date.
    - ```get_total_flow() -> numpy.array``` return the advective flow as a function of both time and depth (2D array). A row corresponds to a fixed depth. A column corresponds to a fixed date.

**ParamsDistributionModel**: an instance of the ParamsDistributionModel class gives the distribution for 4 parameters: permeability, conductiviy, capacity, porosity
- *Getting time series*
    - ```get_log10k() -> numpy.array```: return an array corresponding to the permeability's distribution.
    - ```get_conductivity() -> numpy.array```: return an array corresponding to the conductivity's distribution.
    - ```get_porosity() -> numpy.array``` return an array corresponding to the porosity's distribution.
    - ```get_capacity() -> numpy.array``` return an array corresponding to the thermal capacity's distribution.

## Additional notes
Importing a point and importing a laboratory are currently very fragile features, as they heavily depend on the format of .csv file. A better option would be to have the user fill out different fields in a Qt window, then get the information and send it to the backend. This way, the only files which will be imported will be the measures: however, they have a predetermined format, as it is the Sensor group which builds them.

An other alternative would be to have these windows be independent of Molonaviz, but to make it so that they build .csv files in a predetermined format so as to remove any user-induced error.

### Where should we go from now?
There are many features which could be implemented to make molonaviz even better! Here are a few ideas:
- More robust import of .csv files. The tests to check if the input files have the correct format or structure still are a bit too permisive. Ideally, we shouldn't deal with any user .csv file at all, as it is too much of an open-ended format. We should only be using them when getting data from the sensors (see the API created with the Sensors group) and cleaned data if the user whishes to do some complicated processing. To import laboratories or sensors, the user should fill out Qt forms instead.
- Better error handling. This has barely been done, so Molonaviz will often either crash or give to the user a very generic error message.
- Work on the cleanup window, by allowing for example multiple manual selections at a time, or by creating an undo feature.
- Turn the information model (information about a sampling point) and the table model into a true MoloModel.
- Add some tooltips! This can be done using only Qt Designer, and would be really useful for the compute window.
- Allow the user to save the code he used when cleaning the raw data. The fields in the database exist, so it should be quite easy to simply save the python script.
- Allow the user to save the modifications he made when cleaning the raw data. This means 2 things:
    - If the user did his only cleaning, save the dataframe corresponding to the measures (hdf5 format?)
    - If he only used the features in the cleanup window, since they are deterministic, we only need to save the boundary dates, the flags for each variable, and the dataframe corresponding to the removed points (hdf5 format?).
- Add more physical values or curve: overall, populate the SamplingPointViewer window by adding more tabs.
- Add a way to manage virtual laboratories if this is needed.
- Think about NULL and UNIQUE constraints for the database. For example, shouldn't detectors, studies, laboratories have non-NULL names? UNIQUE names? What about the foreign keys pointing on the detectors for example?
- -Make the database insensitive to the name of the points/studies. Currently 2 points, pressure sensors... could have the same name, but the frontend's only way to identify these objects is by their name. Names should propably be UNIQUE and non-NULL.
- Work on the backend, especially concerning performance purposes. Either use another format (hdf5?) or create a custom iterable object from a QSQLquery. This is relatively easy, as we only have to reimplement the ```__iter__``` method. Would this be compatible with matplotib?
- Enhance the documentation: user guide, technical guide, API... Eventually, we could use an automatic documentation tool like sphinx to extract the docstrings.
- Deploy Molonaviz on pip. This way instead of having to clone a repository and manually launch *python main.py*, one could install molonaviz via pip (*pip install molonaviz*) then simply type *molonaviz* in a terminal.


### Known issues
- Currently, the actions to switch between tabbed, cascade and subwindows views are quite broken:
    - Cascade view is completely broken and it will stretch the graphs immensely (not usable at all)
    - At first glance, subwindow view seems good. However, switching to another view (any one), then switching back to subwindow view will cause each view to have a small scrollbar. This scrollbar is not needed, is very ugly and can be confusing as some graphs will seem to be cropped, or the matplotlib toolbars will not appear.
    - Only tabbed view is good: there is no scrollbar and the graphs aren't stretched. This is probably because of the SamplingPointViewer's ui, more specifically it's size. It's size is unbound (maximumSize = 16777215 x 16777215)
- For some obscure Qt reason, the app segfaults when clicking the quit button. This barely does anything (the app is terminated either way) but means something bad is happening somewhere. It could be because of the way we use Qt's threading, or because of the database connection which isn't closed properly.