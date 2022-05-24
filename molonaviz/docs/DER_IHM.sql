PRAGMA foreign_keys = off;
BEGIN TRANSACTION;

-- Table: BestParameters
CREATE TABLE BestParameters (
            id            INTEGER  PRIMARY KEY AUTOINCREMENT,
            log10KBest         REAL,
            LambdaSBest         REAL,
            NBest           REAL,
            Cap             REAL,
            Layer           INTEGER REFERENCES Layer (id),
            PointKey        INTEGER REFERENCES Point (id)
        );

-- Table: CleanedMeasures
CREATE TABLE CleanedMeasures (
            id            INTEGER  PRIMARY KEY AUTOINCREMENT,
            Date          INTEGER REFERENCES Date (id),
            TempBed      REAL     NOT NULL,
            Temp1            REAL     NOT NULL,
            Temp2            REAL     NOT NULL,
            Temp3            REAL     NOT NULL,
            Temp4            REAL     NOT NULL,
            Pressure      REAL     NOT NULL,
            PointKey     INTEGER REFERENCES Sampling_point (id)
        );

-- Table: Date
CREATE TABLE Date (
            id             INTEGER  PRIMARY KEY AUTOINCREMENT,
            Date           DATETIME
        );

-- Table: Depth
CREATE TABLE Depth (
            id            INTEGER  PRIMARY KEY AUTOINCREMENT,
            Depth         REAL
        );

-- Table: Labo
CREATE TABLE Labo (
            id   INTEGER PRIMARY KEY AUTOINCREMENT,
            Name VARCHAR NOT NULL
        );

-- Table: Layer
CREATE TABLE Layer (
            id            INTEGER  PRIMARY KEY AUTOINCREMENT,
            Layer           INTEGER,
            DepthBed        REAL
        );

-- Table: ParametersDistribution
CREATE TABLE ParametersDistribution (
            id            INTEGER  PRIMARY KEY AUTOINCREMENT,
            log10K         REAL,
            LambdaS         REAL,
            N               REAL,
            Cap             REAL,
            Layer           INTEGER REFERENCES Layer (id),
            PointKey        INTEGER REFERENCES Point (id)
        );

-- Table: Point
CREATE TABLE Point (
            id            INTEGER  PRIMARY KEY AUTOINCREMENT,
            SamplingPoint   INTEGER REFERENCES SamplingPoint (id),
            IncertK         REAL,
            IncertLambda    REAL,
            IncertN         REAL,
            IncertRho       REAL,
            IncertT         REAL,
            IncertPressure  REAL
        );

-- Table: PressureSensor
CREATE TABLE PressureSensor (
            id           INTEGER  PRIMARY KEY AUTOINCREMENT,
            Name         VARCHAR,
            Datalogger   VARCHAR,
            Calibration  DATETIME,
            Intercept    REAL,
            [Du/Dh]      REAL,
            [Du/Dt]      REAL,
            Precision    REAL,
            Thermo_model INTEGER  REFERENCES Thermometer (id),
            Labo         INTEGER  REFERENCES Labo (id)
        );

-- Table: Quantile
CREATE TABLE Quantile (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            Quantile    REAL NOT NULL
        );

-- Table: RawMeasuresPress
CREATE TABLE RawMeasuresPress (
            id          INTEGER UNIQUE
                                PRIMARY KEY AUTOINCREMENT,
            Date        DATETIME    NOT NULL
                                UNIQUE,
            TempBed     REAL,
            Tension    REAL,
            PointKey   INTEGER
        );

-- Table: RawMeasuresTemp
CREATE TABLE RawMeasuresTemp (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            Date        DATETIME,
            Temp1       REAL,
            Temp2       REAL,
            Temp3       REAL,
            Temp4       REAL,
            PointKey    INTEGER REFERENCES SamplingPoint (id)
        );

-- Table: RMSE
CREATE TABLE RMSE (
            id                  INTEGER  PRIMARY KEY AUTOINCREMENT,
            Date                INTEGER REFERENCES Date (id),
            Depth1              INTEGER REFERENCES Depth (id),
            Depth2              INTEGER REFERENCES Depth (id),
            Depth3              INTEGER REFERENCES Depth (id),
            Temp1RMSE           REAL,
            Temp2RMSE           REAL,
            Temp3RMSE           REAL,
            RMSET               REAL,
            PointKey            INTEGER REFERENCES Point (id),
            Quantile            INTEGER REFERENCES Quantile (id)
        );

-- Table: SamplingPoint
CREATE TABLE SamplingPoint (id INTEGER PRIMARY KEY AUTOINCREMENT, Name VARCHAR, Notice VARCHAR, Longitude REAL, Latitude REAL, Implentation DATETIME, LastTransfer DATETIME, DeltaH REAL, RiverBed REAL, Shaft INTEGER REFERENCES Shaft (id), PressureSensor INTEGER REFERENCES PressureSensor (id), Study INTEGER REFERENCES Study (id), Scheme VARCHAR, CleanupScript VARCHAR);

-- Table: Shaft
CREATE TABLE Shaft (id INTEGER PRIMARY KEY AUTOINCREMENT, Name VARCHAR NOT NULL, Datalogger VARCHAR NOT NULL, Depth1 REAL NOT NULL, Depth2 REAL NOT NULL, Depth3 REAL NOT NULL, Depth4 REAL NOT NULL, Thermo_model INTEGER REFERENCES Thermometer (id), Labo INTEGER REFERENCES Labo (id));

-- Table: Study
CREATE TABLE Study (
            id   INTEGER PRIMARY KEY AUTOINCREMENT,
            Name VARCHAR NOT NULL,
            Labo INTEGER REFERENCES Labo (id)
        );

-- Table: TemperatureAndHeatFlows
CREATE TABLE TemperatureAndHeatFlows (
            id              INTEGER  PRIMARY KEY AUTOINCREMENT,
            Date            INTEGER REFERENCES Date (id),
            Depth           INTEGER REFERENCES Depth (id),
            Temperature     REAL,
            AdvectiveFlow   REAL,
            ConductiveFlow  REAL,
            TotalFlow       REAL,
            PointKey        INTEGER REFERENCES Point (id),
            Quantile        INTEGER REFERENCES Quantile (id)
        );

-- Table: Thermometer
CREATE TABLE Thermometer (id INTEGER PRIMARY KEY AUTOINCREMENT, Name VARCHAR NOT NULL, Manu_name VARCHAR NOT NULL, Manu_ref VARCHAR NOT NULL, Error REAL NOT NULL, Labo INTEGER REFERENCES Labo (id));

-- Table: WaterFlow
CREATE TABLE WaterFlow (
            id            INTEGER  PRIMARY KEY AUTOINCREMENT,
            WaterFlow           REAL,
            Date                INTEGER REFERENCES Date (id),
            PointKey            INTEGER REFERENCES Point (id),
            Quantile            INTEGER REFERENCES Quantile (id)
        );

COMMIT TRANSACTION;
PRAGMA foreign_keys = on;
