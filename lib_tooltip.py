"""
Contains classes and functions for custom tooltips (as instances of wx.Dialog)

Classes:

	dlg_ToolTip
	plt_ToolTip
	dlg_InfoToolTip

Function:

	CallInfoToolTip

"""

import wx
import lib_colourscheme as cs
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas 
from matplotlib.figure import Figure
import lib_custombuttons as btn

class dlg_ToolTip(wx.Dialog):
	def __init__(self, parent, str_ToolTipText):
		wx.Dialog.__init__ (self, parent, id = wx.ID_ANY,
						    title = u"Tooltip",
							pos = wx.DefaultPosition,
							size = wx.DefaultSize,
							style = wx.STAY_ON_TOP)
		self.SetSizeHints(wx.DefaultSize, wx.DefaultSize)
		self.SetBackgroundColour(cs.White)

		self.szr_Main = wx.BoxSizer(wx.VERTICAL)
		self.lbl_Main = wx.StaticText(self, label = str_ToolTipText)
		self.szr_Main.Add(self.lbl_Main,0,wx.ALL,5)

		self.SetSizer(self.szr_Main)
		self.Layout()
		self.szr_Main.Fit(self)

		self.Centre( wx.BOTH )
		MousePosition = wx.GetMousePosition()
		TooltipPosition = wx.Point(MousePosition[0], MousePosition[1]+18) # (x,y)
		self.SetPosition(TooltipPosition)

	def __del__( self ):
		pass

class plt_ToolTip(wx.Dialog):
	"""
	Tooltip dialog showing a matplotlib plot
	"""
	def __init__(self, parent, xdata, ydata, derivative):
		"""
        Initialises class attributes.
        
        Arguments:
            parent -> parent object in wx
			xdata -> list/array; xdata for plot
			ydata -> list/array; ydata for plot
			derivative -> list/array; derivative of plotted data
        """
		wx.Dialog.__init__(self, parent, id=wx.ID_ANY,
						   title = u"Tooltip",
						   pos = wx.DefaultPosition,
						   size = wx.Size(150,150),
						   style = wx.STAY_ON_TOP)
		self.SetBackgroundColour(cs.White)

		self.szr_Main = wx.BoxSizer(wx.VERTICAL)
		self.lbl_Main = wx.StaticText(self, 
									  label = "", 
									  size = wx.Size(150,150))
		self.figure = Figure(figsize=(149/100,149/100),dpi=100)
		self.canvas = FigureCanvas(self, -1, self.figure)
		self.ax = self.figure.add_subplot()
		self.fluo, self.deri = self.figure.subplots(nrows=2, ncols=1, sharex=True,
													gridspec_kw={"height_ratios":[2,1],"hspace":0.0})
		self.fluo.plot(xdata, ydata, label="Fluorescence", color="#872154")
		self.deri.plot(xdata, derivative, label="Derivative", color="#ddcc77")
		# Horizontal lines
		#self.pnl_Plot.fluo.axvline(flt_Tm,0,1,linestyle="--",linewidth=1.0,color="grey")
		#self.pnl_Plot.deri.axvline(flt_Tm,0,1,linestyle="--",linewidth=1.0,color="grey")
		self.figure.subplots_adjust(left=0.0, right=1.0, top=1.0 , bottom=0.0)
		self.figure.set_facecolor("#fFfFfF")

		# Add check: If the mouse is not on the list anymore (check coordinates), destroy the dialog!
		# Alternatively, destroy dialog after set time

		self.szr_Main.Add(self.lbl_Main, 1, wx.EXPAND, 0)

		self.SetSizer(self.szr_Main)
		self.Layout()
		self.szr_Main.Fit(self)

		self.Centre( wx.BOTH )
		MousePosition = wx.GetMousePosition()
		TooltipPosition = wx.Point(MousePosition[0]+20, MousePosition[1]+20) # (x,y)
		self.SetPosition(TooltipPosition)

	def __del__( self ):
		pass

class dlg_InfoToolTip(wx.Dialog):
	"""
	Tooltip dialog showing an image file, has "x" button to be
	closed by user
	"""
	def __init__(self, parent, str_ImagePath):
		"""
        Initialises class attributes.
        
        Arguments:
            parent -> parent object in wx
			str_ImagePath -> string; path of image to be displayed
        """
		wx.Dialog.__init__ (self, parent, id = wx.ID_ANY,
							title = u"Title",
							pos = wx.DefaultPosition,
							size = wx.DefaultSize,
							style = wx.STAY_ON_TOP)
		self.SetSizeHints(wx.DefaultSize, wx.DefaultSize)
		self.SetBackgroundColour(cs.White)
		self.parent = parent

		self.szr_Main = wx.BoxSizer(wx.HORIZONTAL)
		self.bmp_Main = wx.StaticBitmap(self,
										bitmap = wx.Bitmap(str_ImagePath, wx.BITMAP_TYPE_ANY))
		self.szr_Main.Add(self.bmp_Main,0,wx.ALL,5)
		self.btn_TinyX = btn.TinyXButton(self)
		self.szr_Main.Add(self.btn_TinyX, 0, wx.ALL, 1)

		self.SetSizer(self.szr_Main)
		self.Layout()
		self.szr_Main.Fit(self)

		self.Centre(wx.BOTH)
		MousePosition = wx.GetMousePosition()
		TooltipPosition = wx.Point(MousePosition[0] - self.GetSize()[0], MousePosition[1]) # (x,y)
		self.SetPosition(TooltipPosition)
		self.SetFocus()
		self.Bind(wx.EVT_KILL_FOCUS, self.End)
		self.btn_TinyX.Bind(wx.EVT_BUTTON, self.End)

	def __del__( self ):
		pass

	def End(self, event):
		"""
		Event handler to destroy object.
		"""
		self.Destroy()

def CallInfoToolTip(event):
	"""
	Event handling function. Launches info tooltip dialog for
	event object.

	Arguments:
		event -> object in wx; image path for dlg_InfoToolTip must be
				 stored as .ImagePath properpty in event obejct.
	"""
	self = event.GetEventObject()
	try: self.dlg_InfoToolTip.Destroy()
	except: None
	self.dlg_InfoToolTip = dlg_InfoToolTip(self, event.GetEventObject().ImagePath)
	self.dlg_InfoToolTip.Show()