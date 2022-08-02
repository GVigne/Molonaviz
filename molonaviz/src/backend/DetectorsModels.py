"""
This file regroups different models used to represent the available detectors in a virtual lab. 
For now, such detectors are listed in a Tree View.
"""
from src.MoloModel import MoloModel
from src.Containers import Thermometer

class ThermometersModel(MoloModel):
    """
    A model to display the presure as given by the captors (raw or cleaned data).
    """
    def __init__(self, queries):
        super().__init__(queries)
        self.data = [] #List of Thermometer objects
    
    def update_data(self):
        while self.queries[0].next():
            newTherm = Thermometer(self.queries[0].value(0), self.queries[0].value(1),self.queries[0].value(2),self.queries[0].value(3))
            self.data.append(newTherm)
    
    def get_all_thermometers(self):
        return self.data
    
    def reset_data(self):
        self.data = []