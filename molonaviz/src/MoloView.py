import matplotlib
import matplotlib.pyplot as plt
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
import matplotlib.dates as mdates
import matplotlib.cm as cm
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator
import numpy as np
from src.MoloModel import MoloModel
from utils.utils import date_to_mdates

class MoloView(FigureCanvasQTAgg):
    """
    Abstract class to implement a view.
    """
    def __init__(self, molomodel : MoloModel, width=5, height=5, dpi=100):
        #Subscribe to the model
        self.model = molomodel
        self.model.register(self)

        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super(MoloView, self).__init__(self.fig)
        self.fig.tight_layout(h_pad=5, pad=5)
        self.axes = self.fig.add_subplot(111)

    def on_update(self):
        """
        This method is called when the data is changed. It must be overloaded for the child classes.
        """
        pass
    
    def retrieve_data(self):
        """
        This method should only be overloaded for concrete classes to fetch data from the model.
        """
        pass

class MoloView1D(MoloView):
    """
    Abstract class to represent 1D views (such the pressure and temperature plots).
    If time_dependent is true, then the x-array is expected to be an array of dates and will be displayed as such.

    There are two main attributes in this class:
        -self.x is a 1D array and will be displayed one the x-axis
        -self.y is a dictionnary of 1D array : the keys are the labels which should be displayed. This is useful to plot many graphs on the same view (quantiles for example). 
    """
    def __init__(self, molomodel: MoloModel,time_dependent=False,title="",ylabel="",xlabel=""):
        super().__init__(molomodel)
        #x and y correspond to the data which should be displayed on the x-axis and y-axis (ex: x=Date,y=Pressure)

        self.x = []
        self.y = {}
        self.xlabel = xlabel
        self.ylabel=ylabel
        self.title = title
        self.time_dependent = time_dependent

    def on_update(self):
        self.axes.clear()
        self.retrieve_data()
        self.setup_x()
        self.plot_data()
        self.draw()
    
    def setup_x(self):
        """
        This method allows to apply changes to the data on the x-axis (for example, format a date).
        """
        if self.time_dependent:
            self.x = date_to_mdates(self.x)
            formatter = mdates.DateFormatter("%y/%m/%d %H:%M")
            self.axes.xaxis.set_major_formatter(formatter)
            self.axes.xaxis.set_major_locator(MaxNLocator(4))
            plt.setp(self.axes.get_xticklabels(), rotation = 15)
        else:
            pass
    
    def plot_data(self):
        for index, (label, data) in enumerate(self.y.items()):
            if len(self.x) == len(data):
                self.axes.plot(self.x, data, label=label)
        self.axes.legend(loc='best')
        self.axes.set_ylabel(self.ylabel)

        self.axes.set_xlabel(self.xlabel)
        self.axes.set_title(self.title)
        self.axes.grid(True)

class MoloView2D(MoloView):
    """
    Abstract class to represent 2D views (such the temperature heat maps).
    There are three main attributes in this class:
        -self.x is a 1D array and will be displayed on the x-axis
        -self.y is a 1D array and will be displayed one the y-axis
        -self.cmap is a 2D array: the value self.y[i,j] is actually the value of a pixel.
    """
    def __init__(self, molomodel: MoloModel,time_dependent=False,title="",xlabel = "",ylabel=""):
        super().__init__(molomodel)

        self.time_dependent = time_dependent
        self.title = title
        self.ylabel = ylabel
        self.xlabel = xlabel
        self.x = []
        self.y = []
        self.cmap = []
    
    def on_update(self):
        self.axes.clear()
        self.retrieve_data()
        self.setup_x()
        self.plot_data()
        self.draw()

    def setup_x(self):
        """
        This method allows to apply changes to the data on the x-axis (for example, format a date).
        """
        if self.time_dependent:
            self.x = date_to_mdates(self.x)
            formatter = mdates.DateFormatter("%y/%m/%d %H:%M")
            self.axes.xaxis.set_major_formatter(formatter)
            self.axes.xaxis.set_major_locator(MaxNLocator(4))
            plt.setp(self.axes.get_xticklabels(), rotation = 15)
        else:
            pass

    def plot_data(self):
        if self.cmap.shape[1] ==len(self.x) and self.cmap.shape[0] == len(self.y):
            #View is not empty and should display something
            image = self.axes.imshow(self.cmap, cmap=cm.Spectral_r, aspect="auto", extent=[self.x[0], self.x[-1], float(self.y[-1]), float(self.y[0])], data="float")
            plt.colorbar(image)
            self.axes.xaxis_date()
            self.axes.set_title(self.title)
            self.axes.set_ylabel(self.ylabel)
            self.axes.set_xlabel(self.xlabel)

class MoloViewHisto(MoloView):
    """
    Abstract class to display histograms
    """
    def __init__(self, molomodel: MoloModel, bins=60, color ='green', title=""):
        super().__init__(molomodel)
        self.bins = bins
        self.data = []
        self.color = color
        self.title = title
    
    def update_bins(self,bins):
        self.bins = bins
    
    def on_update(self):
        self.axes.clear()
        self.retrieve_data()
        self.plot_data()
        self.draw()
    
    def plot_data(self):
        self.axes.hist(self.data, edgecolor='black', bins=self.bins, alpha=.3, density=True, color=self.color)
        self.axes.set_title(self.title)

class PressureView(MoloView1D):
    """
    Concrete class to display the Pressure in "Data arrays and plots" tab.
    """
    def __init__(self, molomodel: MoloModel, time_dependent=True, title="", ylabel="Pression différentielle (m)", xlabel=""):
        super().__init__(molomodel, time_dependent, title, ylabel, xlabel)
    
    def retrieve_data(self):
        self.x  = self.model.get_dates()
        self.y  = {"":np.float64(self.model.get_pressure())} #No label required for this one.

class TemperatureView(MoloView1D):
    """
    Concrete class to display the Pressure in "Data arrays and plots" tab.
    """
    def __init__(self, molomodel: MoloModel, time_dependent=True, title="", ylabel="Temperature (K)", xlabel=""):
        super().__init__(molomodel, time_dependent, title, ylabel, xlabel)
    
    def retrieve_data(self):
        self.x  = self.model.get_dates()
        self.y  = {f"Sensor n°{i}":np.float64(temp) for i,temp in enumerate(self.model.get_temperatures())}

class UmbrellaView(MoloView1D):
    """
    Concrete class for the umbrellas plots.
    """
    def __init__(self, molomodel: MoloModel, time_dependent=False, title="", ylabel="Depth (m)", xlabel="Temperature (K)", nb_dates =10):
        super().__init__(molomodel, time_dependent, title, ylabel, xlabel)
        self.nb_dates = nb_dates
    
    def retrieve_data(self):
        self.x,self.y = self.model.get_depth_by_temp(self.nb_dates)
    
    def plot_data(self):
        """
        This function needs to be overloaded for the umbrellas, as the plot function must be like plot(temps, depth) with depths being fixed.
        """
        for index, (label, data) in enumerate(self.y.items()):
            if len(self.x) == len(data):
                self.axes.plot( data,self.x, label=label)
        self.axes.legend(loc='best')
        self.axes.set_ylabel(self.ylabel)

        self.axes.set_xlabel(self.xlabel)
        self.axes.set_title(self.title)
        self.axes.grid(True)

class TempDepthView(MoloView1D):
    """
    Concrete class for the temperature to a given depth as a function of time.
    An important attribut for this class is option, which reflects what the user wants to display: either quantiles or depths for the thermometer. Option is a list of two elements:
        - the first one is a depth corresponding to a thermometer
        - a list of values representing the quantiles. If this list is empty, then nothing will be displayed
    """
    def __init__(self, molomodel: MoloModel, time_dependent=True, title="", ylabel="Température en K", xlabel="",options=[0,[]]):
        super().__init__(molomodel, time_dependent, title, ylabel, xlabel)
        self.options = options
    
    def update_options(self,options):
        self.options = options
        self.y = {} #Refresh the plots

    def retrieve_data(self):
        thermo_depth = self.options[0]
        self.x = self.model.get_dates()
        for quantile in self.options[1]:
            self.y[f"Température à la profondeur {thermo_depth:.3f} m - quantile {quantile}"] = self.model.get_temp_by_date(thermo_depth, quantile)

class WaterFluxView(MoloView1D):
    """
    Concrete class for the water flux as a function of time.
    """
    def __init__(self, molomodel: MoloModel, time_dependent=True, title="", ylabel="Water flow  (m/s)", xlabel=""):
        super().__init__(molomodel, time_dependent, title, ylabel, xlabel)
    
    def retrieve_data(self):
        self.x = self.model.get_dates()
        all_flows = self.model.get_water_flow()
        if all_flows != {}:
            #The model is not empty so the view should display something
            self.y = {f"Quantile {key}":value for index, (key,value) in enumerate(all_flows.items()) if key!=0}
            self.y["Direct model"] = all_flows[0]

class TempMapView(MoloView2D):
    """
    Concrete class for the heat map.
    """
    def __init__(self, molomodel: MoloModel, time_dependent=True, title="", xlabel="", ylabel="Depth (m)"):
        super().__init__(molomodel, time_dependent, title, xlabel, ylabel)
    
    def retrieve_data(self):
        self.cmap = self.model.get_temperatures_cmap(0)
        self.x = self.model.get_dates() 
        self.y = self.model.get_depths()

class AdvectiveFlowView(MoloView2D):
    """
    Concrete class for the advective flow map.
    """
    def __init__(self, molomodel: MoloModel, time_dependent=True, title="Advective flow (W/m²)", xlabel="", ylabel="Depth (m)"):
        super().__init__(molomodel, time_dependent, title, xlabel, ylabel)
    
    def retrieve_data(self):
        self.cmap = self.model.get_advective_flow()
        self.x = self.model.get_dates()
        self.y = self.model.get_depths()

class ConductiveFlowView(MoloView2D):
    """
    Concrete class for the conductive flow map.
    """
    def __init__(self, molomodel: MoloModel, time_dependent=True, title="Convective flow (W/m²)", xlabel="", ylabel="Depth (m)"):
        super().__init__(molomodel, time_dependent, title, xlabel, ylabel)
    
    def retrieve_data(self):
        self.cmap = self.model.get_conductive_flow()
        self.x = self.model.get_dates()
        self.y = self.model.get_depths()

class TotalFlowView(MoloView2D):
    """
    Concrete class for the total heat flow map.
    """
    def __init__(self, molomodel: MoloModel, time_dependent=True, title="Total energy flow (W/m²)", xlabel="", ylabel="Depth (m)"):
        super().__init__(molomodel, time_dependent, title, xlabel, ylabel)
    
    def retrieve_data(self):
        self.cmap = self.model.get_total_flow()
        self.x = self.model.get_dates()
        self.y = self.model.get_depths()

class Log10KView(MoloViewHisto):
    """
    Concrete class to display the distribution of the -Log10K paramter
    """
    def __init__(self, molomodel: MoloModel, bins=60, color='green', title="Histogramme a posteriori des -log10K"):
        super().__init__(molomodel, bins, color, title)
    
    def retrieve_data(self):
        self.data = self.model.get_log10k()

class PorosityView(MoloViewHisto):
    """
    Concrete class to display the distribution of the porosity paramter
    """
    def __init__(self, molomodel: MoloModel, bins=60, color='blue', title="Histogramme a posteriori des n"):
        super().__init__(molomodel, bins, color, title)
    
    def retrieve_data(self):
        self.data = self.model.get_porosity()

class ConductivityView(MoloViewHisto):
    """
    Concrete class to display the distribution of the conductivity paramter
    """
    def __init__(self, molomodel: MoloModel, bins=60, color='orange', title="Histogramme a posteriori des lambda_s"):
        super().__init__(molomodel, bins, color, title)
    
    def retrieve_data(self):
        self.data = self.model.get_conductivity()

class CapacityView(MoloViewHisto):
    """
    Concrete class to display the distribution of the capacity paramter
    """
    def __init__(self, molomodel: MoloModel, bins=60, color='pink', title="Histogramme a posteriori des rho_s * c_s"):
        super().__init__(molomodel, bins, color, title)
    
    def retrieve_data(self):
        self.data = self.model.get_capacity()