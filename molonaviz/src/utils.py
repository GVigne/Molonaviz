"""
Some useful functions which can be used throughout the code.
"""
from PyQt5 import QtWidgets

def displayCriticalMessage(mainMessage: str, infoMessage: str=''):
    msg = QtWidgets.QMessageBox()
    msg.setIcon(QtWidgets.QMessageBox.Critical)
    msg.setText(mainMessage)
    msg.setInformativeText(infoMessage)
    msg.exec_()