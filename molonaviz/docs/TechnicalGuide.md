# Molonaviz - Technical guide

## Table of contents
- [Overview](#overview)
- [API](#api)


## Overview
This is Molonaviz's technical guide. If you are an end user, this is probably not the documentation you are looking for, and you should instead refer to the user guide.

This documents details the current structure of Molonaviz's backend and frontend, as well as the interactions between them (API). Any changes in this API should be written down here so that future maintainers of the project have a clear document giving all the conventions.

This document also lists additional features which could be implemented, remarks or issues, and a few unresolved bugs. 

This application is loosely based on the work done during the 2022 edition of the engineering trimester Molonari. However, it was initially entirely reworked Guillaume Vigne during the months following this trimester. Its goal is to be enhanced by future editions of the Molonari project.

## The backend/frontend distinction
### Roles and responsabilities
The Molonaviz app has been divided into two parts: one is the *backend*, which manages the computations and data storage, and the other is the *frontend* which is responsible for displaying graphs corresponding to the computations.

### Backend
The backend has three big responsabilities:
- it is interfaced with the pyheatmy module, and is thus responsible of calling the appropriate methods used to obtain results from the measures.
- it must be able to store and manage information about a virtual laboratory, a virtual study, and the associated detectors' technical specificities.
- it must be able to store the raw measures from detectors, the given cleaned measures and different types of computations. These computations are essentially time series.

Currently, the storage method used is a SQL database. The ERD is given in the *docs* folder.

#### Database structure
The database is mostly divided into two parts: one for managing virtual labs and studies, and one for computations. A laboratory is essentially a set of detectors: currently there are only two types of detectors, pressure sensors and shafts (used to measure temperature). It should be relatively easy to add new detectors simply by creating the associated table with a foreign key onto the laboratory table.  

*Note*: a shaft and a pressure sensor are physical detectors (something that will be placed in the river). They both have a thermometer to measure the river's temperature. The thermometer's model is stored in the Thermometer table, as they can have their own specificities (such as error or uncertainties), which can be distinct from the physical detectors'.

A sampling point represents a physical place where physical detectors have been placed. Currently, this means that sampling points are places where one (and only one) pressure sensor and one (and only one) shaft have been placed in a river. These detectors must come from the same laboratory. A study is a combination of sampling points and one laboratory.

For each sampling point, there exists a point, which is a virtual object used to encompass all computations. A sampling point represents the physical implementation and gives raw measures from the river; a point represents all processed data coming from theses measures. Adding a new type of computation comes to adding new tables with a foreign key on the Point table, although one most respect a few conventions:
- The Quantile table is used to know if a MCMC or a direct model has been launched. See [Conventions](#conventions).
- To reduce the amount of data stored, the depths and dates have their own table. This way, for each time series, instead of storing two arrays (array of dates and array of data), only one needs to be stored. This can be done because all computations share the same time scale.
- The Layer table follows the same idea. Since it used both for the parameters distribution (histograms) and for the best parameters (4 values which correspond to the model with minimum of energyS), it was regrouped in its own table.

The database structure could be greatly criticised, as it is not a format used to store scientific data. This leads to a database rapidly growing in size, as well as an increasing time complexity. This is further enhanced by PyQt5's way to do queries, as a QSqlQuery objects are not iterable. This means that whenever we need to access data, we must
- query the database via a `QSqlQuery` object
- convert the `QSqlQuery` into a list by manually calling `next()`

Overall, the database structure is not a good choice as it is very slow and impractical to use. However, it forces to structure the data and have a clear overview of what should or shouldn't be stored.

A more convenient way would be to use storage methods dedicated to scientific data storage, such as the excellent HDF5 (which has a great Python API): the computation part of the database would be much easier to use, and with some work, the laboratory could also be stored.

### Frontend
The frontend is handles communication with the end user using a User Interface (UI). For now, the UI is made using PyQt5. The frontend must be able to
- collect information from the end user and pass it to the backend in a correct format (see API)
- display the computations in graphs by using models
- verify and clean the times series given by the user. For example, the frontend must process the raw measures from the sensors, and is also responsible for cleaning the measures in the dedicated window.

#### Frontend organisation
When the user launches Molonaviz, the first thing he has access to is the main window. This is the window responsible for dispatching specific actions to other parts of the code. The main window allows the user to:
- manage virtual laboratories
- manage virtual studies
- open points to view the results
Many actions are automatically done by the models (see API). These models do not require specific instructions to be refreshed, and are instead refreshed whenever the backend register changes.

The SamplingPointViewer is the window which displays all results from a specific sampling point from a study. It is also heavily built on models so that as mnay things as possible can be done automatically. It features a cleanup window to allow end-user to process the raw data from the sensors. The goal of this cleanup window is not to allow any type of processing. Instead, it features a few simple processing (currently Z-score and IQR), allows the user to manually remove nonsensical points, but also select a specific time period. If the end-user whishes to make complex processing, he should instead export the raw measures, process them on his own using whatever method he whishes, then import the cleaned measures into Molonaviz. This is a touchy operation, as the user could make mistakes such as change the name of the columns or put NaNs in the dataframes.

## Conventions

### Convention
### Rule of thumb

## API
### Models and Views
In order to reduce the amount of code, increase clarity, and prevent nasty bugs, a model/view system has been implemented.

A model is a backend object which can store data. A view is a frontend object which displays data nicely. Views can be subscribed to a model: a model can have any number of registered views; however, a view may only be subscribed to one model. The real strength of this organisation is that a model can automatically notify all related views when some of its data has changed. This is done by emitting a custom pyqt signal called dataChanged: views can catch this signal as react accordingly.

From a backend perspective, a model doesn't have to do anything except implement various getters to return data in a "nice" way (usually list or numpy arrays). A model simply gives data, and has no interest or knowledge of its views.

From a frontend perspective, a view is responsible for subscribing to a specific model. This is done with the `register` method: alternatively, a view could choose to unsubscribe from its model using the `unregister`, although this is not recommended at all. The recommended way to use a view is to create an instance of the view by giving it a model, and not use the methods making the link between the models and the views. Views should always inherit from `MoloView`: on creation, it automatically registers the view to a model if one is given.

From a developper perspective, to implement a new feature:
- create the backend object inheriting from `MoloModel`, the highest abstract class representing a model. This new model should implement different getters.
- create a frontend object inheriting from `MoloView`, the highest abstract class representing a view. The view may also inherit from other objects: for example, the `GraphView` is a view which can display time series on a matplotlib canvas.
- create an instance of the new view by giving it the appropriate instance of the new model. The frontend can now use aditionnal features (such as matplotlib features) to present data in a nice way.

### Containers and enum
Containers are objects allowing an easy communication between backend and frontent: sometimes, structured information must be exchanged, and containers are here just for this. Containers shouldn't be used for non structured data (for example time series). Containers are mostly fancy classes which mimick a dictionnary or a named tuple. Their only goal is to have a list of attributes which can be easily read, and they do not have any method. For example, Molonaviz had to deal with thermometers which have different attributes, such as a brand, a name, an accuracy error... To hold all of these informations, a Thermometer object has been created which contains just what is required to describe a thermometer.

Enum are an other way to communicate between backend and frontend. Instead of having error codes (like error 404, 500...), Molonaviz uses enum which hide these error codes: from a programmer perpective, we use strings instead, like `RAW_MEASURES`. Currently, this is only used to know which type of computation has been made.

## Additional notes
Importing a point and importing a laboratory are currently very fragile features, as they heavily depend on the format of .csv file. A better option would be to have the user fill out different fields in a Qt window, then get the information and send it to the backend. This way, the only files which will be imported will be the measures: however, they have a predetermined format, as it is the Sensor group which builds them.

An other alternative would be to have these windows be independent of Molonaviz, but to make it so that they build .csv files in a predetermined format so as to remove any user-induced error. 

### Known issues
Currently, the actions to switch between tabbed, cascade and subwindows views are quite broken:
- Cascade view is completely broken and it will stretch the graphs immensely (not usable at all)
- At first glance, subwindow view seems good. However, switching to another view (any one), then switching back to subwindow view will cause each view to have a small scrollbar. This scrollbar is not needed, is very ugly and can be confusing as some graphs will seem to be cropped, or the matplotlib toolbars will not appear.
- Only tabbed view is good: there is no scrollbar and the graphs aren't stretched
This is probably because of the SamplingPointViewer's ui, more specifically it's size. It's size is unbound (maxsize = )
