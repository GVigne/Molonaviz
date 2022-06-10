"""
Some useful functions which can be used throughout the code.
"""
from PyQt5 import QtWidgets
import os

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