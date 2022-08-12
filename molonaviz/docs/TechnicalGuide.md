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

## Conventions

## API

## Additional notes

