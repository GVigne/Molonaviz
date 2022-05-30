PRAGMA foreign_keys = off;
BEGIN TRANSACTION;

-- Table: BestParameters
CREATE TABLE BestParameters (
            ID            INTEGER  PRIMARY KEY AUTOINCREMENT,
            log10KBest         REAL,
            LambdaSBest         REAL,
            NBest           REAL,
            Cap             REAL,
            Layer           INTEGER REFERENCES Layer (ID),
            PointKey        INTEGER REFERENCES Point (ID)
        );

-- Table: CleanedMeasures
CREATE TABLE CleanedMeasures (
            ID            INTEGER  PRIMARY KEY AUTOINCREMENT,
            Date          INTEGER REFERENCES Date (ID),
            TempBed      REAL     NOT NULL,
            Temp1            REAL     NOT NULL,
            Temp2            REAL     NOT NULL,
            Temp3            REAL     NOT NULL,
            Temp4            REAL     NOT NULL,
            Pressure      REAL     NOT NULL,
            PointKey     INTEGER REFERENCES Sampling_point (ID)
        );

-- Table: Date
CREATE TABLE Date (
            ID             INTEGER  PRIMARY KEY AUTOINCREMENT,
            Date           DATETIME
        );

-- Table: Depth
CREATE TABLE Depth (
            ID            INTEGER  PRIMARY KEY AUTOINCREMENT,
            Depth         REAL
        );

-- Table: Labo
CREATE TABLE Labo (
            ID   INTEGER PRIMARY KEY AUTOINCREMENT,
            Name VARCHAR NOT NULL
        );

-- Table: Layer
CREATE TABLE Layer (
            ID            INTEGER  PRIMARY KEY AUTOINCREMENT,
            Layer           INTEGER,
            DepthBed        REAL
        );

-- Table: ParametersDistribution
CREATE TABLE ParametersDistribution (
            ID            INTEGER  PRIMARY KEY AUTOINCREMENT,
            log10K         REAL,
            LambdaS         REAL,
            N               REAL,
            Cap             REAL,
            Layer           INTEGER REFERENCES Layer (ID),
            PointKey        INTEGER REFERENCES Point (ID)
        );

-- Table: Point
CREATE TABLE Point (
            ID            INTEGER  PRIMARY KEY AUTOINCREMENT,
            SamplingPoint   INTEGER REFERENCES SamplingPoint (ID),
            IncertK         REAL,
            IncertLambda    REAL,
            IncertN         REAL,
            IncertRho       REAL,
            IncertT         REAL,
            IncertPressure  REAL
        );

-- Table: PressureSensor
CREATE TABLE PressureSensor (
            ID           INTEGER  PRIMARY KEY AUTOINCREMENT,
            Name         VARCHAR,
            Datalogger   VARCHAR,
            Calibration  DATETIME,
            Intercept    REAL,
            [Du/Dh]      REAL,
            [Du/Dt]      REAL,
            Precision    REAL,
            Thermo_model INTEGER  REFERENCES Thermometer (ID),
            Labo         INTEGER  REFERENCES Labo (ID)
        );

-- Table: Quantile
CREATE TABLE Quantile (
            ID          INTEGER PRIMARY KEY AUTOINCREMENT,
            Quantile    REAL NOT NULL
        );

-- Table: RawMeasuresPress
CREATE TABLE RawMeasuresPress (
            ID          INTEGER UNIQUE
                                PRIMARY KEY AUTOINCREMENT,
            Date        DATETIME    NOT NULL
                                UNIQUE,
            TempBed     REAL,
            Tension    REAL,
            PointKey   INTEGER
        );

-- Table: RawMeasuresTemp
CREATE TABLE RawMeasuresTemp (
            ID          INTEGER PRIMARY KEY AUTOINCREMENT,
            Date        DATETIME,
            Temp1       REAL,
            Temp2       REAL,
            Temp3       REAL,
            Temp4       REAL,
            PointKey    INTEGER REFERENCES SamplingPoint (ID)
        );

-- Table: RMSE
CREATE TABLE RMSE (
            ID                  INTEGER  PRIMARY KEY AUTOINCREMENT,
            Date                INTEGER REFERENCES Date (ID),
            Depth1              INTEGER REFERENCES Depth (ID),
            Depth2              INTEGER REFERENCES Depth (ID),
            Depth3              INTEGER REFERENCES Depth (ID),
            Temp1RMSE           REAL,
            Temp2RMSE           REAL,
            Temp3RMSE           REAL,
            RMSET               REAL,
            PointKey            INTEGER REFERENCES Point (ID),
            Quantile            INTEGER REFERENCES Quantile (ID)
        );

-- Table: SamplingPoint
CREATE TABLE SamplingPoint (ID INTEGER PRIMARY KEY AUTOINCREMENT, Name VARCHAR, Notice VARCHAR, Longitude REAL, Latitude REAL, Implentation DATETIME, LastTransfer DATETIME, DeltaH REAL, RiverBed REAL, Shaft INTEGER REFERENCES Shaft (ID), PressureSensor INTEGER REFERENCES PressureSensor (ID), Study INTEGER REFERENCES Study (ID), Scheme VARCHAR, CleanupScript VARCHAR);

-- Table: Shaft
CREATE TABLE Shaft (ID INTEGER PRIMARY KEY AUTOINCREMENT, Name VARCHAR NOT NULL, Datalogger VARCHAR NOT NULL, Depth1 REAL NOT NULL, Depth2 REAL NOT NULL, Depth3 REAL NOT NULL, Depth4 REAL NOT NULL, Thermo_model INTEGER REFERENCES Thermometer (ID), Labo INTEGER REFERENCES Labo (ID));

-- Table: Study
CREATE TABLE Study (
            ID   INTEGER PRIMARY KEY AUTOINCREMENT,
            Name VARCHAR NOT NULL,
            Labo INTEGER REFERENCES Labo (ID)
        );

-- Table: TemperatureAndHeatFlows
CREATE TABLE TemperatureAndHeatFlows (
            ID              INTEGER  PRIMARY KEY AUTOINCREMENT,
            Date            INTEGER REFERENCES Date (ID),
            Depth           INTEGER REFERENCES Depth (ID),
            Temperature     REAL,
            AdvectiveFlow   REAL,
            ConductiveFlow  REAL,
            TotalFlow       REAL,
            PointKey        INTEGER REFERENCES Point (ID),
            Quantile        INTEGER REFERENCES Quantile (ID)
        );

-- Table: Thermometer
CREATE TABLE Thermometer (ID INTEGER PRIMARY KEY AUTOINCREMENT, Name VARCHAR NOT NULL, Manu_name VARCHAR NOT NULL, Manu_ref VARCHAR NOT NULL, Error REAL NOT NULL, Labo INTEGER REFERENCES Labo (ID));

-- Table: WaterFlow
CREATE TABLE WaterFlow (
            ID            INTEGER  PRIMARY KEY AUTOINCREMENT,
            WaterFlow           REAL,
            Date                INTEGER REFERENCES Date (ID),
            PointKey            INTEGER REFERENCES Point (ID),
            Quantile            INTEGER REFERENCES Quantile (ID)
        );

COMMIT TRANSACTION;
PRAGMA foreign_keys = on;
