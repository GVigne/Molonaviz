from PyQt5.QtCore import QObject
from src.MoloModel import MoloModel #Used only for type hints

class MoloView(QObject):
    """
    Abstract class representing a frontend view, which can be anything used to display data (a tree view, a matlpotlib canvas, a combo box...).
    """
    def __init__(self, molomodel : MoloModel | None):
        QObject.__init__(self)

        #Subscribe to the model
        if molomodel is not None:
            self.register(molomodel)
        self.model = molomodel
    
    def register(self, model : MoloModel):
        """
        Subscribe this view to the given MoloModel.
        """
        model.dataChanged.connect(self.on_update)

    def unregister(self):
        """
        Unsubscribe this view to its model, if there is one.
        """
        if self.model is not None:
            self.model.dataChanged.disconnect(self.on_update)
    
    def subscribe_model(self, molomodel : MoloModel):
        """
        Replace the current model by given model and subscribe to it. Then, revert the view to an empty state.
        WARNING: if this function was not called and no model was given when creating an instance of this class, there is no guarentee the view will work or won't throw exceptions. Before trying to display or update anything, a model MUST be set.
        """
        self.reset_internal_data()
        self.unregister()
        self.register(molomodel)
        self.model = molomodel

    def on_update(self):
        """
        This method is called when the model notifies that some data has changed. It must be overloaded for the child classes.
        """
        pass
    
    def retrieve_data(self):
        """
        Fetch appropriate data from model. This must be overloaded for child classes, and should probably be called by on_update.
        """
        pass
    
    def reset_internal_data(self):
        """
        This should only be called when changing model (ie when subscribe_model is called).
        Reset all internal data to a base state representing an empty view.
        """
        pass