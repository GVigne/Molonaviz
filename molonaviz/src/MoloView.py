from src.MoloModel import MoloModel #Used only for type hints

class MoloView:
    """
    Abstract class representing a frontend view, which can be anything used to display data (a tree view, a matlpotlib canvas, a combo box...).
    It is the view's responsability to subscribe to a model. This can be done with the register and unregister function. For convenience, a high-level function subscribe_model is implemented to replace the model by another one.
    Views must also be able to handle empty iterables or objects given by the models.
    """
    def __init__(self, molomodel : MoloModel | None = None, figure = None):
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
            self.model = None
    
    def subscribe_model(self, molomodel : MoloModel):
        """
        Revert the view to an empty state, then subscribe to the new given model.
        WARNING: if this function was not called and no model was given when creating an instance of this class, there is no guarentee the view will work or won't throw exceptions. Before trying to display or update anything, a model MUST be set.
        """
        self.reset()
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
    
    def reset(self):
        """
        This should only be called when changing model (ie when subscribe_model is called) or when clearing the model.
        Reset all internal data to a base state representing an empty view.
        """
        self.unregister()