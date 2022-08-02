from PyQt5 import QtCore
from PyQt5.QtCore import QObject
from PyQt5.QtSql import QSqlQuery #Used only for type hints

class MoloModel(QObject):
    """
    Abstract class representing a backend model onto which one or several views may be subscribed.
    A MoloModel is mainly a list of queries which need to be executed. It may also contain data, a processed form of the queries (for example a list, numpy array or panda dataframe of elements orginating from the queries).
    A MoloModel automatically notifies its views when it executes its queries, meaning there is new data to be fetched.
    """
    dataChanged = QtCore.pyqtSignal()

    def __init__(self, queries : list[QSqlQuery]):
        QObject.__init__(self)
        self.queries = queries
        self.data = None
    
    def newQueries(self,queries):
        """
        This function should only be called by frontend users.
        Define a new set of queries and reset all data. Then, execute the queries so new data is available.
        """
        self.queries = queries
        self.reset_data()
        self.exec()
    
    def exec(self):
        """
        Execute all queries and notify the subscribed views that the data has been modified.
        """
        for q in self.queries:
            q.exec()
        self.update_data()
        self.dataChanged.emit()

    def update_data(self):
        """
        This function must be overloaded if the data field is not trivial and must be updated when executing queries.
        """
        pass
    
    def reset_data(self):
        """
        Reinitialise all data. This should only be called when the frontend user wants a new set of queries to be executed.
        """
        pass
