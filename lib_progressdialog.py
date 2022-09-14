"""
Contains two classes for i. detailed description of progress of
analysis and ii. a generic progress dialog.

Classes:
	ProgressDialog
	GenericProgress

"""

import wx
import lib_colourscheme as cs
from lib_custombuttons import CustomBitmapButton
from os import path
from time import sleep

class ProgressDialog(wx.Dialog):
	"""
	Progress dialog for data analysis.
	Mini-log of analysis prcgress gets shown here.
	"""

	def __init__(self, parent):
		"""
        Initialises class attributes.
        
        Arguments:
            parent -> wx object; parent object
        """
		wx.Dialog.__init__ (self, parent, id = wx.ID_ANY,
							title = wx.EmptyString,
							pos = wx.DefaultPosition,
							size = wx.Size(515,490),
							style = 0|wx.TAB_TRAVERSAL)
		
		self.SetSizeHints(wx.DefaultSize, wx.DefaultSize)

		self.szr_Frame = wx.BoxSizer(wx.VERTICAL)
		self.pnl_Panel = wx.Panel(self, style = wx.TAB_TRAVERSAL)
		self.pnl_Panel.SetBackgroundColour(cs.Black)

		self.szr_Surround = wx.BoxSizer(wx.VERTICAL)
		# TITLE BAR #####################################################################
		self.pnl_TitleBar = wx.Panel(self.pnl_Panel)
		self.pnl_TitleBar.SetBackgroundColour(cs.BgUltraDark)
		self.pnl_TitleBar.SetForegroundColour(cs.White)
		self.szr_TitleBar = wx.BoxSizer(wx.HORIZONTAL)
		self.lbl_Title = wx.StaticText(self.pnl_TitleBar,
									   label = u"Analysis is running...")
		self.lbl_Title.Wrap(-1)
		self.szr_TitleBar.Add(self.lbl_Title, 0, wx.ALL, 5)
		self.szr_TitleBar.Add((-1,0), 1, wx.EXPAND, 5)
		self.btn_X = CustomBitmapButton(self.pnl_TitleBar, type = "small_x", index = 0,
										size = (25,25), pathaddendum = u"titlebar")
		self.btn_X.Bind(wx.EVT_BUTTON, lambda event: self.Close(event, parent))
		self.szr_TitleBar.Add(self.btn_X, 0, wx.ALL, 0)
		self.pnl_TitleBar.SetSizer(self.szr_TitleBar)
		self.pnl_TitleBar.Layout()
		self.szr_Surround.Add(self.pnl_TitleBar, 0, wx.EXPAND, 5)

		# PROCESS LOG ###################################################################
		self.pnl_Process = wx.Panel(self.pnl_Panel, size = wx.Size(-1,-1))
		self.szr_Process = wx.BoxSizer(wx.HORIZONTAL)
		self.lbx_Log = wx.ListBox(self.pnl_Process,
								  size = wx.Size(-1,430),
								  choices = [],
								  style = 0|wx.VSCROLL)
		self.lbx_Log.SetBackgroundColour(cs.BgMedium)
		self.szr_Process.Add(self.lbx_Log, 1, wx.EXPAND, 5)
		self.pnl_Process.SetSizer(self.szr_Process)
		#self.pnl_Process.Layout()
		self.szr_Surround.Add(self.pnl_Process, 1, wx.EXPAND, 5)

		self.pnl_Button = wx.Panel(self.pnl_Panel)
		self.pnl_Button.SetBackgroundColour(cs.BgMediumDark)
		self.szr_Button = wx.BoxSizer(wx.HORIZONTAL)
		self.szr_Button.Add((0, 0), 1, wx.EXPAND, 5)
		self.btn_Close = CustomBitmapButton(self.pnl_Button, "Close", 0, (100,30))
		self.btn_Close.Bind(wx.EVT_BUTTON, lambda event: self.Close(event, parent))
		self.szr_Button.Add(self.btn_Close, 0, wx.ALL, 5)
		self.pnl_Button.SetSizer(self.szr_Button)
		self.pnl_Button.Layout()
		self.szr_Surround.Add(self.pnl_Button, 0, wx.EXPAND, 5)

		self.pnl_Panel.SetSizer(self.szr_Surround)
		self.pnl_Panel.Layout()
		self.szr_Frame.Add(self.pnl_Panel,0,wx.EXPAND,1)

		self.SetSizer(self.szr_Frame)
		self.Layout()
		self.Centre(wx.BOTH)

		self.btn_Close.Enable(False)
		self.btn_X.Enable(False)
		self.Bind(wx.EVT_CLOSE, lambda event: self.Close(event, parent))
		# Required for window dragging:
		self.delta = wx.Point(0,0)
		self.pnl_TitleBar.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
		self.lbl_Title.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
		self.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
		self.Bind(wx.EVT_MOTION, self.OnMouseMove)
		self.dragging = False

	def __del__(self):
		pass

	def Close(self, event, parent):
		"""
		Event handler. Destroys dialog box and thaws parent object.
		
		Arguments:
			event -> unused
			parent -> parent object that needs to be thawed
		
		"""
		parent.Thaw()
		self.Destroy()

	# The following three function are taken from a tutorial on the wxPython Wiki: https://wiki.wxpython.org/How%20to%20create%20a%20customized%20frame%20-%20Part%201%20%28Phoenix%29
	# They have been modified if and where appropriate.

	def OnMouseMove(self, event):
		"""
		Event handler to capture mouse movements when dragging window
		and change position based on movement.
		"""
		if self.dragging == True:
			if event.Dragging() and event.LeftIsDown():
				x,y = self.ClientToScreen(event.GetPosition())
				newPos = (x - self.delta[0], y - self.delta[1])
				self.Move(newPos)

	def OnLeftDown(self, event):
		"""
		Event handler to capture mouse for window dragging.
		"""
		self.CaptureMouse()
		x, y = self.ClientToScreen(event.GetPosition())
		originx, originy = self.GetPosition()
		dx = x - originx
		dy = y - originy
		self.delta = [dx, dy]
		self.dragging = True

	def OnLeftUp(self, event):
		"""
		Event handler to release mouse after window dragging.
		"""
		if self.HasCapture():
			self.ReleaseMouse()
		self.dragging = False

class GenericProgress (wx.Frame):
	"""
	Generic progress bar popup dialog
	"""
	def __init__(self, parent, label = "Fnord"):
		"""
        Initialises class attributes.
        
        Arguments:
            parent -> wx object; parent object
			label -> string; text to show above bar
        """
		wx.Frame.__init__ (self, parent,
						   id = wx.ID_ANY,
						   title = wx.EmptyString,
						   pos = wx.DefaultPosition,
						   size = wx.Size(340,80),
						   style = 0|wx.TAB_TRAVERSAL)

		self.SetSizeHints(wx.DefaultSize, wx.DefaultSize)
		self.szr_Populate = wx.BoxSizer(wx.VERTICAL)
		self.szr_Top = wx.BoxSizer(wx.VERTICAL)
		self.szr_Top.Add((0, 0), 1, wx.EXPAND, 5)
		self.szr_Populate.Add(self.szr_Top, 1, wx.EXPAND, 5)
		self.szr_Middle = wx.BoxSizer(wx.HORIZONTAL)
		self.szr_Left = wx.BoxSizer(wx.VERTICAL)
		self.szr_Left.Add((0, 0), 1, wx.EXPAND, 5)
		self.szr_Middle.Add(self.szr_Left, 1, wx.EXPAND, 5)
		self.szr_Centre = wx.BoxSizer(wx.VERTICAL)
		self.lbl_Description = wx.StaticText(self, label = label)
		self.lbl_Description.Wrap(-1)
		self.szr_Centre.Add(self.lbl_Description, 0, wx.ALL, 5)
		self.gauge = wx.Gauge(self, range = 200,
							  size = wx.Size(300,-1),
							  style = wx.GA_HORIZONTAL)
		self.gauge.SetValue(0)
		self.szr_Centre.Add(self.gauge, 0, wx.ALL, 5)
		self.szr_Middle.Add(self.szr_Centre, 1, wx.EXPAND, 5)
		self.szr_Right = wx.BoxSizer(wx.VERTICAL)
		self.szr_Right.Add((0, 0), 1, wx.EXPAND, 5)
		self.szr_Middle.Add(self.szr_Right, 1, wx.EXPAND, 5)
		self.szr_Populate.Add(self.szr_Middle, 1, wx.EXPAND, 5)
		self.szr_Bottom = wx.BoxSizer(wx.VERTICAL)
		self.szr_Bottom.Add((0, 0), 1, wx.EXPAND, 5)
		self.szr_Populate.Add(self.szr_Bottom, 1, wx.EXPAND, 5)
		self.SetSizer(self.szr_Populate)
		self.Layout()
		self.Centre(wx.BOTH)

	def __del__(self):
		pass