"""
Some useful functions which can be used throughout the code.
"""
from PyQt5 import QtWidgets

def displayCriticalMessage(mainMessage: str, infoMessage: str = ''):
    """
    Display a critical message (with a no entry sign). This should be used to tell the user that an important error occured and he has to actively do something.
    """
    msg = QtWidgets.QMessageBox()
    msg.setIcon(QtWidgets.QMessageBox.Critical)
    msg.setText(mainMessage)
    msg.setInformativeText(infoMessage)
    msg.exec_()

def displayWarningMessage(mainMessage: str, infoMessage: str = ''):
    """
    Display a warning message. This should be used to tell the user that an error occured but it is not detrimental to the app's features.
    """
    msg = QtWidgets.QMessageBox()
    msg.setIcon(QtWidgets.QMessageBox.Warning)
    msg.setText(mainMessage)
    msg.setInformativeText(infoMessage)
    msg.exec_() 