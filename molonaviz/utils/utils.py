"""
Some useful functions which can be used throughout the code.
"""
from PyQt5 import QtWidgets
import os
from datetime import datetime
import pandas as pd
import numpy as np

def displayCriticalMessage(mainMessage: str, infoMessage: str = ''):
    """
    Display a critical message (with a no entry sign). This should be used to tell the user that an important error occured and he has to actively do something.
    """
    msg = QtWidgets.QMessageBox()
    msg.setIcon(QtWidgets.QMessageBox.Critical)
    msg.setText(mainMessage)
    msg.setInformativeText(infoMessage)
    msg.exec()

def displayWarningMessage(mainMessage: str, infoMessage: str = ''):
    """
    Display a warning message. This should be used to tell the user that an error occured but it is not detrimental to the app's features.
    """
    msg = QtWidgets.QMessageBox()
    msg.setIcon(QtWidgets.QMessageBox.Warning)
    msg.setText(mainMessage)
    msg.setInformativeText(infoMessage)
    msg.exec() 

def createDatabaseDirectory(directory, databaseName):
    """
    Given a directory and the name of the database, create a folder with the name databaseName and the correct structure.
    Return True if the directory was successfully created, False otherwise
    """
    databaseFolder = os.path.join(directory, databaseName)
    if os.path.isdir(databaseFolder):
        return False
    os.mkdir(databaseFolder)
    os.mkdir(os.path.join(databaseFolder, "Notices"))
    os.mkdir(os.path.join(databaseFolder, "Schemes"))
    os.mkdir(os.path.join(databaseFolder, "Scripts"))
    f = open(os.path.join(databaseFolder, "Molonari.sqlite"),"x")
    f.close()
    return True

def checkDbFolderIntegrity(dbPath):
    """
    Given the path to a database folder, check if it has all the subfolders and the database in it.
    """
    return os.path.isfile(os.path.join(dbPath, "Molonari.sqlite")) and os.path.isdir(os.path.join(dbPath, "Notices")) and os.path.isdir(os.path.join(dbPath, "Schemes")) and os.path.isdir(os.path.join(dbPath, "Scripts"))

def inputToDatabaseDate(date: str):
    """
    This function should only be used when importing raw measures from a CSV file (data coming from sensors) into the database. Convert the dates from the CSV file into a string of format YYYY/MM/DD HH:MM:SS (this is the convention for the database dates).
    The dates in the CSV file should be in format  YYYY/MM/DD HH:MM:SS: however, this function can also deal with other types of format.
    """
    formats = ("%Y/%m/%d %H:%M:%S",  "%Y/%m/%d %I:%M:%S %p",
                "%y/%m/%d %H:%M:%S", "%Y/%m/%d %H:%M:%S",
                "%m/%d/%y %H:%M:%S", "%m/%d/%y %I:%M:%S %p",
               "%d/%m/%y %H:%M",    "%d/%m/%y %I:%M %p",
               "%m/%d/%Y %H:%M:%S", "%m/%d/%Y %I:%M:%S %p", 
               "%d/%m/%Y %H:%M",    "%d/%m/%Y %I:%M %p",
                                     "%y/%m/%d %I:%M:%S %p", 
               "%y/%m/%d %H:%M",    "%y/%m/%d %I:%M %p",
               "%Y/%m/%d %H:%M",    "%Y/%m/%d %I:%M %p",
               "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %I:%M:%S %p",
               "%Y:%m:%d %H:%M:%S", "%Y:%m:%d %I:%M:%S %p",
                "%m:%d:%Y %I:%M:%S %p")
    for f in formats:
        try:
            dtObj = datetime.strptime(date, f) 
            return datetime.strftime(dtObj, "%Y/%m/%d %H:%M:%S") #This is the database date convention
        except Exception as e:
            continue
        
def convertDates(df):
    """
    Convert dates from a list of strings by testing several different input formats
    Try all date formats already encountered in data points
    If none of them is OK, try the generic way (None)
    If the generic way doesn't work, this method fails
    (in that case, you should add the new format to the list)
    
    This function works directly on the giving Pandas dataframe (in place)
    This function assumes that the first column of the given Pandas dataframe
    contains the dates as characters string type
    
    For datetime conversion performance, see:
    See https://stackoverflow.com/questions/40881876/python-pandas-convert-datetime-to-timestamp-effectively-through-dt-accessor
    """
    formats = ("%m/%d/%y %H:%M:%S", "%m/%d/%y %I:%M:%S %p",
               "%d/%m/%y %H:%M",    "%d/%m/%y %I:%M %p",
               "%m/%d/%Y %H:%M:%S", "%m/%d/%Y %I:%M:%S %p", 
               "%d/%m/%Y %H:%M",    "%d/%m/%Y %I:%M %p",
               "%y/%m/%d %H:%M:%S", "%y/%m/%d %I:%M:%S %p", 
               "%y/%m/%d %H:%M",    "%y/%m/%d %I:%M %p",
               "%Y/%m/%d %H:%M:%S", "%Y/%m/%d %I:%M:%S %p", 
               "%Y/%m/%d %H:%M",    "%Y/%m/%d %I:%M %p",
               "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %I:%M:%S %p",
               "%Y:%m:%d %H:%M:%S", "%Y:%m:%d %I:%M:%S %p",
               "%m:%d:%Y %H:%M:%S", "%m:%d:%Y %I:%M:%S %p",None)
    times = df[df.columns[0]]
    for f in formats:
        try:
            # Convert strings to datetime objects
            new_times = pd.to_datetime(times, format=f)
            # Convert datetime series to numpy array of integers (timestamps)
            new_ts = new_times.values.astype(np.int64)
            # If times are not ordered, this is not the appropriate format
            test = np.sort(new_ts) - new_ts
            if np.sum(abs(test)) != 0 :
                #print("Order is not the same")
                raise ValueError()
            # Else, the conversion is a success
            #print("Found format ", f)
            df[df.columns[0]] = new_times
            return
        
        except ValueError:
            #print("Format ", f, " not valid")
            continue
    
    # None of the known format are valid
    raise ValueError("Cannot convert dates: No known formats match your data!")


def databaseDateToDatetime(date : str):
    """
    Given a date in the database format (YYYY/MM/DD HH:MM:SS), return the corresponding datetime object.
    """
    return datetime.strptime(date, "%Y/%m/%d %H:%M:%S")
