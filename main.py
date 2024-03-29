'''
To-Do
- ability to change parameters mid cycle (ideally implemented the moment we switch it, but can be implemented in following cycle)
'''

print ('importing sys...')
import sys
print ('importing os...')
import os
print ('importing platform...')
import platform
print ('importing datetime...')
import datetime
print ('importing numpy...')
import numpy as np
print ('importing pandas...')
import pandas as pd
######################################################################################################
print ('importing PyQt5...')
from PyQt5 import QtCore, QtWidgets, QtGui
######################################################################################################
print ('importing Matplotlib...')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

from matplotlib.backend_bases import Event
from matplotlib.figure import Figure
######################################################################################################
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib
matplotlib.use("Qt5Agg")
######################################################################################################
print ('importing myKeithleyFunctions...')
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)),'Keithley Code'))
import myKeithleyFunctions as mkf
print ('importing pyvisa')
import pyvisa
######################################################################################################

pan = NavigationToolbar.pan
def new_pan (self, *args, **kwargs):
	s = 'pan_event'
	event = Event(s, self)
	self.canvas.callbacks.process(s, event)
	pan(self, *args, **kwargs)
NavigationToolbar.pan = new_pan

zoom = NavigationToolbar.zoom
def new_zoom (self, *args, **kwargs):
	s = 'zoom_event'
	event = Event(s, self)
	self.canvas.callbacks.process(s, event)
	zoom(self, *args, **kwargs)
NavigationToolbar.zoom = new_zoom

configureSubplots = NavigationToolbar.configure_subplots
def new_config (self, *args, **kwargs):
	s = 'config_event'
	event = Event(s, self)
	self.canvas.callbacks.process(s, event)
	config(self, *args, **kwargs)
NavigationToolbar.config = new_config
# save = NavigationToolbar.save_figure

class myProgressBar(QtWidgets.QProgressBar):
	def text(self):
		self.totalSteps = self.maximum() - self.minimum()
		if self.totalSteps <= 0:
			self.progress = 0
		else:
			self.progress = 100*(self.value()-self.minimum())/(self.maximum() - self.minimum())
			self.progress = np.floor(100*self.progress)/100
		self.progressString = f'{self.progress:.2f}'
		self.progressBarString = self.format().replace('%p', str(self.value())).replace('%m',str(self.totalSteps)).replace('%v',self.progressString)
		return self.progressBarString

class Worker(QtCore.QObject):
	def __init__(self, parent=None, totalLoops=1):
		super(Worker, self).__init__(parent)

	finished = QtCore.pyqtSignal()
	progress = QtCore.pyqtSignal(int,object)

	def run(self):
		self.keithley = window.keithley
		mkf.prepareCurrent(self.keithley)
		# self.times = []
		# self.referenceTime = datetime.datetime.now()

		self.status = None

		# Convert Strings to Ints
		self.initialWait = int(window.initialWaitLineEdit.text())
		self.totalLoops = int(window.totalLoopsLineEdit.text())
		self.depositionTime = int(window.depositionTimeLineEdit.text())
		self.depositionWait = int(window.depositionWaitLineEdit.text())
		self.stripTime = int(window.stripTimeLineEdit.text())
		self.stripWait = int(window.stripWaitLineEdit.text())

		# Convert Strings to Floats
		self.depositionVoltage = float(window.depositionVoltageLineEdit.text())
		self.stripVoltage = float(window.stripVoltageLineEdit.text())
		self.depositionCurrentCutoff = float(window.depositionCutoffILineEdit.text())
		self.stripCurrentCutoff = float(window.stripCutoffILineEdit.text())

		self.loopTime = self.depositionTime + self.depositionWait + self.stripTime + self.stripWait
		self.totalTime = self.initialWait + self.totalLoops*self.loopTime

		self.timeInterval = window.timeInterval
		self.totalIterations = 1000*self.totalTime//self.timeInterval
		self.currentIteration = 0
		self.currentLoop = min(self.totalLoops,max(0,1 + (self.currentIteration - 1000*self.initialWait//self.timeInterval)//(1000*self.loopTime//self.timeInterval)))

		self.timer = QtCore.QTimer(self)
		self.timer.setInterval(self.timeInterval)
		self.timer.setTimerType(QtCore.Qt.PreciseTimer)
		self.timer.timeout.connect(self.doScience)
		self.timer.start()

	def doScience(self):
		# self.deltaTime = datetime.datetime.now()-self.referenceTime
		# self.times.append(self.deltaTime.total_seconds())
		# if len(self.times) >=2:
		# 	self.timeDiffs = 1000*np.diff(self.times)
		# 	self.timeErrors = self.timeDiffs-self.timeInterval
		# 	self.timeS = self.timeErrors**2
		# 	self.timeMS = np.mean(self.timeS)
		# 	self.timeRMS = np.sqrt(self.timeMS)
		# 	self.maxError = np.max(np.abs(self.timeDiffs-self.timeInterval))

		# 	print (f'{self.timeRMS:.2f}\t{self.maxError:.2f}')

		# Read charge cutoff flags
		self.depositionChargeCutoffFlag = window.depositionChargeCutoffFlag
		self.stripChargeCutoffFlag = window.stripChargeCutoffFlag

		# Trigger Keithley Events
		self.currentLoop = min(self.totalLoops,max(0,1 + (self.currentIteration - 1000*self.initialWait//self.timeInterval)//(1000*self.loopTime//self.timeInterval)))
		if self.currentIteration - 1000*self.initialWait//self.timeInterval < 0:
			if self.currentIteration == 0:
				self.status = 'Status: Initial Wait'
				print (self.status)
				self.setVolt = 0
				self.simCurrent = 0
				mkf.setVoltage(self.keithley, voltage = self.setVolt)
		else:
			self.elapsedCycleIterations = (max(0,self.currentIteration - 1000*self.initialWait//self.timeInterval))%(self.loopTime*1000//self.timeInterval)
			if self.elapsedCycleIterations == 0 and self.currentIteration != self.totalIterations:
				self.status = 'Status: Start Cycle'
				print (self.status)

			if self.depositionTime != 0 and self.elapsedCycleIterations == 0 and self.currentIteration != self.totalIterations:
				self.status = 'Status: Start Deposition'
				print (self.status)
				self.setVolt = self.depositionVoltage
				self.simCurrent = self.setVolt * 2
				mkf.setVoltage(self.keithley, voltage = self.setVolt)

			elif self.depositionWait != 0 and self.elapsedCycleIterations == self.depositionTime*1000//self.timeInterval:
				self.status = 'Status: Deposition Wait'
				print (self.status)
				self.setVolt = 0
				self.simCurrent = 0
				mkf.setVoltage(self.keithley, voltage = self.setVolt)

			elif self.stripTime != 0 and self.elapsedCycleIterations == (self.depositionTime + self.depositionWait)*1000//self.timeInterval:
				self.status = 'Status: Start Stripping'
				print (self.status)
				self.setVolt = self.stripVoltage
				self.simCurrent = self.setVolt *2
				mkf.setVoltage(self.keithley, voltage = self.setVolt)

			elif self.stripWait != 0 and self.elapsedCycleIterations == (self.depositionTime + self.depositionWait + self.stripTime)*1000//self.timeInterval:
				self.status = 'Status: Strip Wait'
				print (self.status)
				self.setVolt = 0
				self.simCurrent = 0
				mkf.setVoltage(self.keithley, voltage = self.setVolt)

			elif self.currentIteration == self.totalIterations:
				self.status = 'Status: Cycling Completed'
				print (self.status)
				self.setVolt = 0
				self.simCurrent = 0
				mkf.setVoltage(self.keithley, voltage = self.setVolt)

		# Measure from the Keithley
		if self.currentIteration == 0:
			mkf.setOutput(self.keithley, True)
			self.start = datetime.datetime.now()
			self.timeStamp = 0
		else:
			self.timeStamp = (datetime.datetime.now()-self.start).total_seconds()

		if self.keithley == 'test':
			self.rawData = np.array([self.setVolt,self.simCurrent,9.91e+37, self.timeStamp, 0b00000000])
		else:
			self.rawData = mkf.measureCurrent(self.keithley)
			self.rawData[3] = self.timeStamp
            

		if self.keithley == 'test':
			if self.currentIteration == 10:
				self.rawData[1] = -0.5
		if self.status == 'Status: Start Deposition':
			if not self.elapsedCycleIterations == 0:
				if abs(self.rawData[1]) <= self.depositionCurrentCutoff:
					self.status = 'Status: Deposition Cutoff Current Condition Met'
					print (self.status)
					self.setVolt = 0
					self.simCurrent = 0
					mkf.setVoltage(self.keithley, voltage = self.setVolt)
					self.currentIteration = ((self.currentLoop-1)*self.loopTime + self.initialWait + self.depositionTime)*1000//self.timeInterval
					self.currentIteration += -1
				elif self.depositionChargeCutoffFlag:
					self.status = 'Status: Deposition Cutoff Charge Condition Met'
					print (self.status)
					self.setVolt = 0
					self.simCurrent = 0
					mkf.setVoltage(self.keithley, voltage = self.setVolt)
					self.currentIteration = ((self.currentLoop-1)*self.loopTime + self.initialWait + self.depositionTime)*1000//self.timeInterval
					self.currentIteration += -1
		if self.status == 'Status: Start Stripping':
			if abs(self.rawData[1]) <= self.stripCurrentCutoff:
				self.status = 'Status: Stripping Cutoff Current Condition Met'
				print (self.status)
				self.setVolt = 0
				self.simCurrent = 0
				mkf.setVoltage(self.keithley, voltage = self.setVolt)
				self.currentIteration = ((self.currentLoop-1)*self.loopTime + self.initialWait + self.depositionTime + self.depositionWait + self.stripTime)*1000//self.timeInterval
				self.currentIteration += -1
			elif self.stripChargeCutoffFlag:
				self.status = 'Status: Stripping Cutoff Charge Condition Met'
				print (self.status)
				self.setVolt = 0
				self.simCurrent = 0
				mkf.setVoltage(self.keithley, voltage = self.setVolt)
				self.currentIteration = ((self.currentLoop-1)*self.loopTime + self.initialWait + self.depositionTime + self.depositionWait + self.stripTime)*1000//self.timeInterval
				self.currentIteration += -1

		self.progress.emit(self.currentIteration,self.rawData)
		self.currentIteration += 1
		if self.currentIteration > self.totalIterations:
			self.timer.stop()
			mkf.setVoltage(self.keithley, voltage = 0)
			mkf.setOutput(self.keithley, False)
			self.finished.emit()
		if window.stopScienceFlag == True:
			self.timer.stop()
			mkf.setVoltage(self.keithley, voltage = 0)
			mkf.setOutput(self.keithley, False)
			print ('Abort detected!')
			self.finished.emit()
class EditLiveSettingsWindow(QtWidgets.QWidget):
	def __init__(self, parent=None):
		super(EditLiveSettingsWindow, self).__init__(parent)
		QtWidgets.QApplication.setStyle(QtWidgets.QStyleFactory.create("Fusion"))

		self.titleIVParameters = "Edit Settings"
		self.initEditSettingsUI()

	def initEditSettingsUI(self):
		self.setWindowTitle(self.titleIVParameters)

		# Define the parent widget
		self.editMainWidget = QtWidgets.QWidget()
		# Define a layout for the parent widget
		self.editGridLayout = QtWidgets.QGridLayout(self.editMainWidget)



		self.show()
		self.move(50,50)
		# self.resize(400,800)

class Window(QtWidgets.QMainWindow):
	def __init__(self,parent=None):
		QtWidgets.QMainWindow.__init__(self)
		QtWidgets.QApplication.setStyle(QtWidgets.QStyleFactory.create("Fusion"))
		# QtWidgets.QApplication.setStyle(QtWidgets.QStyleFactory.create("macintosh"))
		# QtWidgets.QApplication.setStyle(QtWidgets.QStyleFactory.create("windowsvista"))
		# print(QtWidgets.QStyleFactory.keys())
		# sys.exit()

		self.title = 'Windows Cycling'
		self.timeInterval = 250
		self.initUI()

	def initUI(self):
		self.setWindowTitle(self.title)
		self.setWindowIcon(QtGui.QIcon('simple_icon.png'))
		self.resize(1280,720)
		# Define the parent widget
		self.mainWidget = QtWidgets.QWidget()
		# Define a layout for the parent widget
		self.gridLayout = QtWidgets.QGridLayout(self.mainWidget)

		# Create widgets to hold the form layouts and to be placed in the grid
		self.inputFormWidget = QtWidgets.QWidget(self)
		self.inputFormLayout = QtWidgets.QFormLayout(self.inputFormWidget)

		self.depositionGroupBox = QtWidgets.QGroupBox('Deposition Parameters')
		self.depositionFormLayout = QtWidgets.QFormLayout(self.depositionGroupBox)
		self.depositionGroupBox.setLayout(self.depositionFormLayout)

		self.stripGroupBox = QtWidgets.QGroupBox('Stripping Parameters')
		self.stripFormLayout = QtWidgets.QFormLayout(self.stripGroupBox)
		self.stripGroupBox.setLayout(self.stripFormLayout)

		self.measurementGroupBox = QtWidgets.QGroupBox('Measurement Information')
		self.measurementFormLayout = QtWidgets.QFormLayout(self.measurementGroupBox)
		self.measurementGroupBox.setLayout(self.measurementFormLayout)

		self.timeGroupBox = QtWidgets.QGroupBox('Time Information')
		self.timeFormLayout = QtWidgets.QFormLayout(self.timeGroupBox)
		self.timeGroupBox.setLayout(self.timeFormLayout)

		# Set Form Layout Properties
		self.inputFormLayout.setFormAlignment(QtCore.Qt.AlignRight)
		self.depositionFormLayout.setFormAlignment(QtCore.Qt.AlignRight)
		self.stripFormLayout.setFormAlignment(QtCore.Qt.AlignRight)
		self.measurementFormLayout.setFormAlignment(QtCore.Qt.AlignRight)
		self.timeFormLayout.setFormAlignment(QtCore.Qt.AlignRight)

		self.inputFormLayout.setLabelAlignment(QtCore.Qt.AlignRight)
		self.depositionFormLayout.setLabelAlignment(QtCore.Qt.AlignRight)
		self.stripFormLayout.setLabelAlignment(QtCore.Qt.AlignRight)
		self.measurementFormLayout.setLabelAlignment(QtCore.Qt.AlignRight)
		self.timeFormLayout.setLabelAlignment(QtCore.Qt.AlignRight)

		# Create Matplotlib Canvas for I vs t
		self.IvtWidget = QtWidgets.QWidget(self)
		self.IvtGridLayout = QtWidgets.QGridLayout(self.IvtWidget)	
		self.Ivtcanvas = FigureCanvas(Figure(figsize=(5, 3)))
		self.Ivtcanvas.mpl_connect('pan_event', self.IvtToolbarClicked)
		self.Ivtcanvas.mpl_connect('zoom_event', self.IvtToolbarClicked)
		self.Ivtcanvas.mpl_connect('config_event', self.IvtToolbarClicked)
		
		self.Ivttoolbar = NavigationToolbar(self.Ivtcanvas, self)
		self.Ivttoolbar.setMinimumWidth(500)

		self.Ivtaxes = self.Ivtcanvas.figure.subplots()
		self.Ivtaxes.set_title('I v t')
		self.Ivtaxes.set_xlabel('Time (seconds)')
		self.Ivtaxes.set_ylabel('Current (A)')
		self.Ivtaxes.axhline(0,c='k')
		self.Ivtaxes.axvline(0,c='k')

		self.IvtPlay = QtWidgets.QPushButton(self.mainWidget)
		self.IvtPlay.setIcon(QtGui.QIcon(os.path.join('assets','play.png')))
		self.IvtPlay.setCheckable(True)
		self.IvtPlay.setChecked(True)
		self.IvtStop = QtWidgets.QPushButton(self.mainWidget)
		self.IvtStop.setIcon(QtGui.QIcon(os.path.join('assets','stop.png')))
		self.IvtStop.setCheckable(True)
		self.IvtStop.setChecked(False)

		self.IvtGridLayout.addWidget(self.Ivttoolbar, 0,0,1,1)
		self.IvtGridLayout.addWidget(self.IvtPlay, 0,1,1,1)
		self.IvtGridLayout.addWidget(self.IvtStop, 0,2,1,1)
		self.IvtGridLayout.addWidget(self.Ivtcanvas, 1,0,1,3)



		# Create Matplotlib Canvas for Q vs t
		self.QvtWidget = QtWidgets.QWidget(self)
		self.QvtGridLayout = QtWidgets.QGridLayout(self.QvtWidget)
		self.Qvtcanvas = FigureCanvas(Figure(figsize=(5, 3)))
		self.Qvtcanvas.mpl_connect('pan_event', self.QvtToolbarClicked)
		self.Qvtcanvas.mpl_connect('zoom_event', self.QvtToolbarClicked)
		self.Qvtcanvas.mpl_connect('config_event', self.QvtToolbarClicked)
		
		self.Qvttoolbar = NavigationToolbar(self.Qvtcanvas, self)
		self.Qvttoolbar.setMinimumWidth(500)

		self.Qvtaxes = self.Qvtcanvas.figure.subplots()
		self.Qvtaxes.set_title('Q v t')
		self.Qvtaxes.set_xlabel('Time (seconds)')
		self.Qvtaxes.set_ylabel('Charge (C)')
		self.Qvtaxes.axhline(0,c='k')
		self.Qvtaxes.axvline(0,c='k')

		self.QvtPlay = QtWidgets.QPushButton(self.mainWidget)
		self.QvtPlay.setIcon(QtGui.QIcon(os.path.join('assets','play.png')))
		self.QvtPlay.setCheckable(True)
		self.QvtPlay.setChecked(True)

		self.QvtStop = QtWidgets.QPushButton(self.mainWidget)
		self.QvtStop.setIcon(QtGui.QIcon(os.path.join('assets','stop.png')))
		self.QvtStop.setCheckable(True)
		self.QvtStop.setChecked(False)

		self.QvtGridLayout.addWidget(self.Qvttoolbar, 0,0,1,1)
		self.QvtGridLayout.addWidget(self.QvtPlay, 0,1,1,1)
		self.QvtGridLayout.addWidget(self.QvtStop, 0,2,1,1)
		self.QvtGridLayout.addWidget(self.Qvtcanvas, 1,0,1,3)



		# Create Matplotlib Canvas for Q vs t
		self.QvtCycleWidget = QtWidgets.QWidget(self)
		self.QvtCycleGridLayout = QtWidgets.QGridLayout(self.QvtCycleWidget)
		self.QvtCyclecanvas = FigureCanvas(Figure(figsize=(5, 3)))
		self.QvtCyclecanvas.mpl_connect('pan_event', self.QvtCycleToolbarClicked)
		self.QvtCyclecanvas.mpl_connect('zoom_event', self.QvtCycleToolbarClicked)
		self.QvtCyclecanvas.mpl_connect('config_event', self.QvtCycleToolbarClicked)
		
		self.QvtCycletoolbar = NavigationToolbar(self.QvtCyclecanvas, self)
		self.QvtCycletoolbar.setMinimumWidth(500)

		self.QvtCycleaxes = self.QvtCyclecanvas.figure.subplots()
		self.QvtCycleaxes.set_title('Q v t (Current Cycle)')
		self.QvtCycleaxes.set_xlabel('Time (seconds)')
		self.QvtCycleaxes.set_ylabel('Charge (C)')
		self.QvtCycleaxes.axhline(0,c='k')
		self.QvtCycleaxes.axvline(0,c='k')

		self.QvtCyclePlay = QtWidgets.QPushButton(self.mainWidget)
		self.QvtCyclePlay.setIcon(QtGui.QIcon(os.path.join('assets','play.png')))
		self.QvtCyclePlay.setCheckable(True)
		self.QvtCyclePlay.setChecked(True)

		self.QvtCycleStop = QtWidgets.QPushButton(self.mainWidget)
		self.QvtCycleStop.setIcon(QtGui.QIcon(os.path.join('assets','stop.png')))
		self.QvtCycleStop.setCheckable(True)
		self.QvtCycleStop.setChecked(False)

		self.QvtCycleGridLayout.addWidget(self.QvtCycletoolbar, 0,0,1,1)
		self.QvtCycleGridLayout.addWidget(self.QvtCyclePlay, 0,1,1,1)
		self.QvtCycleGridLayout.addWidget(self.QvtCycleStop, 0,2,1,1)
		self.QvtCycleGridLayout.addWidget(self.QvtCyclecanvas, 1,0,1,3)



		self.cycleProfilecanvas = FigureCanvas(Figure(figsize=(5,3)))
		self.cycleProfileaxes = self.cycleProfilecanvas.figure.subplots()
		self.cycleProfileaxes.axhline(0, c='k')
		self.cycleProfileaxes.axvline(0, c='k')



		# Create Tab Widget to hold multiple plots
		self.tabWidget = QtWidgets.QTabWidget(self)
		self.tabWidget.addTab(self.IvtWidget,'I v t')
		self.tabWidget.addTab(self.QvtWidget, 'Q v t')
		self.tabWidget.addTab(self.QvtCycleWidget, 'Q v t (Current Cycle)')
		self.tabWidget.addTab(self.cycleProfilecanvas, 'Cycle Profile')



		# Create Buttons
		self.settingsPushButton = QtWidgets.QPushButton(self.mainWidget)
		self.settingsPushButton.setIcon(QtGui.QIcon(os.path.join('assets','settings.png')))
		self.settingsPushButton.setToolTip('Edit Parameters While Taking Data.')
		self.settingsPushButton.setEnabled(False)

		self.cdPushButton = QtWidgets.QPushButton(self.mainWidget)
		self.cdPushButton.setIcon(QtGui.QIcon(os.path.join('assets','save.png')))
		self.cdPushButton.setToolTip('Go to a specific directory.')

		self.keithleyPushButton = QtWidgets.QPushButton(self.mainWidget)
		self.keithleyPushButton.setText('No Keithley Selected')
		# self.keithleyPushButton.setIcon(QtGui.QIcon(os.path.join('assets','keithley.png')))
		self.keithleyPushButton.setToolTip('Select the Keithley to use.')

		self.saveLocationLineEdit = QtWidgets.QLineEdit()
		self.saveLocationLineEdit.setReadOnly(True)
		self.startScienceButton = QtWidgets.QPushButton(self.mainWidget)
		self.startScienceButton.setText('Start')
		self.stopScienceButton = QtWidgets.QPushButton(self.mainWidget)
		self.stopScienceButton.setText('STOP')
		self.stopScienceButton.setEnabled(False)

		self.loopProgressBar = myProgressBar(self)
		self.myLoopValue = 0
		self.loopProgressBar.setMaximum(100)
		self.loopProgressBar.setValue(self.myLoopValue)
		self.loopProgressBar.setFormat('%v%')

		self.totalProgressBar = myProgressBar(self)
		self.myTotalValue = 0
		self.totalProgressBar.setMaximum(100)
		self.totalProgressBar.setValue(self.myTotalValue)
		self.totalProgressBar.setFormat('%v%')


		self.buttonSizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed,QtWidgets.QSizePolicy.Fixed)
		self.buttonSizePolicy.setHorizontalStretch(0)
		self.buttonSizePolicy.setVerticalStretch(0)

		# self.depositionGroupBox.setSizePolicy(self.buttonSizePolicy)
		# self.stripGroupBox.setSizePolicy(self.buttonSizePolicy)
		# self.measurementGroupBox.setSizePolicy(self.buttonSizePolicy)
		# self.timeGroupBox.setSizePolicy(self.buttonSizePolicy)

		self.settingsPushButton.setSizePolicy(self.buttonSizePolicy)
		self.cdPushButton.setSizePolicy(self.buttonSizePolicy)
		self.keithleyPushButton.setSizePolicy(self.buttonSizePolicy)
		# self.startScienceButton.setSizePolicy(self.buttonSizePolicy)
		self.IvtPlay.setSizePolicy(self.buttonSizePolicy)
		self.IvtStop.setSizePolicy(self.buttonSizePolicy)
		self.QvtPlay.setSizePolicy(self.buttonSizePolicy)
		self.QvtStop.setSizePolicy(self.buttonSizePolicy)
		self.QvtCyclePlay.setSizePolicy(self.buttonSizePolicy)
		self.QvtCycleStop.setSizePolicy(self.buttonSizePolicy)

		# Add Widgets to the grid
		self.gridLayout.addWidget(self.settingsPushButton, 0,0,1,1)
		self.gridLayout.addWidget(self.cdPushButton, 0,1,1,1)
		self.gridLayout.addWidget(self.keithleyPushButton, 0,2,1,1)
		self.gridLayout.addWidget(self.saveLocationLineEdit, 0,3,1,6)
		self.gridLayout.addWidget(self.inputFormWidget, 1,0,1,6)
		self.gridLayout.addWidget(self.depositionGroupBox, 2,0,1,4)
		self.gridLayout.addWidget(self.stripGroupBox, 3,0,1,4)
		self.gridLayout.addWidget(self.measurementGroupBox, 2,4,1,2)
		self.gridLayout.addWidget(self.timeGroupBox, 3,4,1,2)
		self.gridLayout.addWidget(self.tabWidget, 1,6,7,1)
		self.gridLayout.addWidget(self.startScienceButton, 4,0,1,6)
		self.gridLayout.addWidget(self.stopScienceButton, 5,0,1,6)
		self.gridLayout.addWidget(self.loopProgressBar, 6,0,1,6)
		self.gridLayout.addWidget(self.totalProgressBar, 7,0,1,6)

		# Create Labels
		self.userLabel = QtWidgets.QLabel(self.mainWidget)
		self.userLabel.setText('User')

		self.depositionTimeLabel = QtWidgets.QLabel(self.mainWidget)
		self.depositionTimeLabel.setText('t<sub>deposition</sub> (s)')
		self.depositionVoltageLabel = QtWidgets.QLabel(self.mainWidget)
		self.depositionVoltageLabel.setText('V<sub>deposition</sub> (V)')
		self.depositionWaitLabel = QtWidgets.QLabel(self.mainWidget)
		self.depositionWaitLabel.setText('t<sub>deposition, wait</sub> (s)')
		self.cutoffDepositionILabel = QtWidgets.QLabel(self.mainWidget)
		self.cutoffDepositionILabel.setText('I<sub>deposition, cutoff</sub> (A)')
		self.cutoffDepositionCLabel = QtWidgets.QLabel(self.mainWidget)
		self.cutoffDepositionCLabel.setText('Q<sub>deposition, cutoff</sub> (C)')

		self.stripTimeLabel = QtWidgets.QLabel(self.mainWidget)
		self.stripTimeLabel.setText('t<sub>strip</sub> (s)')
		self.stripVoltageLabel = QtWidgets.QLabel(self.mainWidget)
		self.stripVoltageLabel.setText('V<sub>strip</sub> (V)')
		self.stripWaitLabel = QtWidgets.QLabel(self.mainWidget)
		self.stripWaitLabel.setText('t<sub>strip, wait</sub> (s)')
		self.cutoffStripILabel = QtWidgets.QLabel(self.mainWidget)
		self.cutoffStripILabel.setText('I<sub>strip, cutoff</sub> (A)')
		self.cutoffStripCLabel = QtWidgets.QLabel(self.mainWidget)
		self.cutoffStripCLabel.setText('Q<sub>strip, cutoff</sub> (C)')


		self.totalLoopsLabel = QtWidgets.QLabel(self.mainWidget)
		self.totalLoopsLabel.setText('Loop Count')

		self.initialWaitLabel = QtWidgets.QLabel(self.mainWidget)
		self.initialWaitLabel.setText('t<sub>initial</sub> (s)')

		self.activeVoltageLabel = QtWidgets.QLabel(self.mainWidget)
		self.activeVoltageLabel.setText('V (V)')
		self.activeCurrentLabel = QtWidgets.QLabel(self.mainWidget)
		self.activeCurrentLabel.setText('I (A)')
		self.activeChargeLabel = QtWidgets.QLabel(self.mainWidget)
		self.activeChargeLabel.setText('Q (C)')
		self.activeChargeCycleLabel = QtWidgets.QLabel(self.mainWidget)
		self.activeChargeCycleLabel.setText('Q (C) (Current Cycle)')

		self.currentLoopLabel = QtWidgets.QLabel(self.mainWidget)
		self.currentLoopLabel.setText('Current Cycle')
		
		self.elapsedCycleTimeLabel = QtWidgets.QLabel(self.mainWidget)
		self.elapsedCycleTimeLabel.setText('Elapsed Cycle Time (s)')
		self.totalCycleTimeLabel = QtWidgets.QLabel(self.mainWidget)
		self.totalCycleTimeLabel.setText('Total Cycle Time (s)')
		self.remainingCycleTimeLabel = QtWidgets.QLabel(self.mainWidget)
		self.remainingCycleTimeLabel.setText('Remaining Cycle Time (s)')
		
		self.elapsedTimeLabel = QtWidgets.QLabel(self.mainWidget)
		self.elapsedTimeLabel.setText('Elapsed Time (s)')
		self.totalTimeLabel = QtWidgets.QLabel(self.mainWidget)
		self.totalTimeLabel.setText('Total Time (s)')
		self.remainingTimeLabel = QtWidgets.QLabel(self.mainWidget)
		self.remainingTimeLabel.setText('Time Remaining (s)')

		# Add Labels to the Form
		self.inputFormLayout.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.userLabel)
		self.inputFormLayout.setWidget(1, QtWidgets.QFormLayout.LabelRole, self.totalLoopsLabel)
		self.inputFormLayout.setWidget(2, QtWidgets.QFormLayout.LabelRole, self.initialWaitLabel)

		self.depositionFormLayout.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.depositionTimeLabel)
		self.depositionFormLayout.setWidget(1, QtWidgets.QFormLayout.LabelRole, self.depositionVoltageLabel)
		self.depositionFormLayout.setWidget(2, QtWidgets.QFormLayout.LabelRole, self.depositionWaitLabel)
		self.depositionFormLayout.setWidget(3, QtWidgets.QFormLayout.LabelRole, self.cutoffDepositionILabel)
		self.depositionFormLayout.setWidget(4, QtWidgets.QFormLayout.LabelRole, self.cutoffDepositionCLabel)

		self.stripFormLayout.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.stripTimeLabel)
		self.stripFormLayout.setWidget(1, QtWidgets.QFormLayout.LabelRole, self.stripVoltageLabel)
		self.stripFormLayout.setWidget(2, QtWidgets.QFormLayout.LabelRole, self.stripWaitLabel)
		self.stripFormLayout.setWidget(3, QtWidgets.QFormLayout.LabelRole, self.cutoffStripILabel)
		self.stripFormLayout.setWidget(4, QtWidgets.QFormLayout.LabelRole, self.cutoffStripCLabel)


		self.measurementFormLayout.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.activeVoltageLabel)
		self.measurementFormLayout.setWidget(1, QtWidgets.QFormLayout.LabelRole, self.activeCurrentLabel)
		self.measurementFormLayout.setWidget(2, QtWidgets.QFormLayout.LabelRole, self.activeChargeLabel)
		self.measurementFormLayout.setWidget(3, QtWidgets.QFormLayout.LabelRole, self.activeChargeCycleLabel)

		self.timeFormLayout.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.currentLoopLabel)
		self.timeFormLayout.setWidget(1, QtWidgets.QFormLayout.LabelRole, self.elapsedCycleTimeLabel)
		self.timeFormLayout.setWidget(2, QtWidgets.QFormLayout.LabelRole, self.totalCycleTimeLabel)
		self.timeFormLayout.setWidget(3, QtWidgets.QFormLayout.LabelRole, self.remainingCycleTimeLabel)
		self.timeFormLayout.setWidget(4, QtWidgets.QFormLayout.LabelRole, self.elapsedTimeLabel)
		self.timeFormLayout.setWidget(5, QtWidgets.QFormLayout.LabelRole, self.totalTimeLabel)
		self.timeFormLayout.setWidget(6, QtWidgets.QFormLayout.LabelRole, self.remainingTimeLabel)

		# Create Line Edits
		self.userLineEdit = QtWidgets.QLineEdit()
		self.userLineEdit.setText('Dr. Tyler Hernandez')

		self.totalLoopsLineEdit = QtWidgets.QLineEdit()
		self.totalLoopsLineEdit.setText('10')
		self.totalLoopsLineEdit.setAlignment(QtCore.Qt.AlignRight)

		self.initialWaitLineEdit = QtWidgets.QLineEdit()
		self.initialWaitLineEdit.setText('4')
		self.initialWaitLineEdit.setAlignment(QtCore.Qt.AlignRight)

		self.depositionTimeLineEdit = QtWidgets.QLineEdit()
		self.depositionTimeLineEdit.setText('20')
		self.depositionTimeLineEdit.setAlignment(QtCore.Qt.AlignRight)

		self.depositionVoltageLineEdit = QtWidgets.QLineEdit()
		self.depositionVoltageLineEdit.setText('-0.7')
		self.depositionVoltageLineEdit.setAlignment(QtCore.Qt.AlignRight)

		self.depositionWaitLineEdit = QtWidgets.QLineEdit()
		self.depositionWaitLineEdit.setText('2')
		self.depositionWaitLineEdit.setAlignment(QtCore.Qt.AlignRight)

		self.depositionCutoffILineEdit = QtWidgets.QLineEdit()
		self.depositionCutoffILineEdit.setText('0')
		self.depositionCutoffILineEdit.setAlignment(QtCore.Qt.AlignRight)

		self.depositionCutoffCLineEdit = QtWidgets.QLineEdit()
		self.depositionCutoffCLineEdit.setText('-999')
		self.depositionCutoffCLineEdit.setAlignment(QtCore.Qt.AlignRight)

		self.stripTimeLineEdit = QtWidgets.QLineEdit()
		self.stripTimeLineEdit.setText('60')
		self.stripTimeLineEdit.setAlignment(QtCore.Qt.AlignRight)

		self.stripVoltageLineEdit = QtWidgets.QLineEdit()
		self.stripVoltageLineEdit.setText('1')
		self.stripVoltageLineEdit.setAlignment(QtCore.Qt.AlignRight)

		self.stripWaitLineEdit = QtWidgets.QLineEdit()
		self.stripWaitLineEdit.setText('2')
		self.stripWaitLineEdit.setAlignment(QtCore.Qt.AlignRight)

		self.stripCutoffILineEdit = QtWidgets.QLineEdit()
		self.stripCutoffILineEdit.setText('0')
		self.stripCutoffILineEdit.setAlignment(QtCore.Qt.AlignRight)

		self.stripCutoffCLineEdit = QtWidgets.QLineEdit()
		self.stripCutoffCLineEdit.setText('999')
		self.stripCutoffCLineEdit.setAlignment(QtCore.Qt.AlignRight)

		self.activeVoltageLineEdit = QtWidgets.QLineEdit()
		self.activeVoltageLineEdit.setReadOnly(True)
		self.activeVoltageLineEdit.setText('open')
		self.activeVoltageLineEdit.setAlignment(QtCore.Qt.AlignRight)

		self.activeCurrentLineEdit = QtWidgets.QLineEdit()
		self.activeCurrentLineEdit.setReadOnly(True)
		self.activeCurrentLineEdit.setText('0')
		self.activeCurrentLineEdit.setAlignment(QtCore.Qt.AlignRight)

		self.activeChargeLineEdit = QtWidgets.QLineEdit()
		self.activeChargeLineEdit.setReadOnly(True)
		self.activeChargeLineEdit.setText('0')
		self.activeChargeLineEdit.setAlignment(QtCore.Qt.AlignRight)

		self.activeChargeCycleLineEdit = QtWidgets.QLineEdit()
		self.activeChargeCycleLineEdit.setReadOnly(True)
		self.activeChargeCycleLineEdit.setText('0')
		self.activeChargeCycleLineEdit.setAlignment(QtCore.Qt.AlignRight)

		self.currentLoopLineEdit = QtWidgets.QLineEdit()
		self.currentLoopLineEdit.setReadOnly(True)
		self.currentLoopLineEdit.setText('0')
		self.currentLoopLineEdit.setAlignment(QtCore.Qt.AlignRight)

		self.elapsedCycleTimeLineEdit = QtWidgets.QLineEdit()
		self.elapsedCycleTimeLineEdit.setReadOnly(True)
		self.elapsedCycleTimeLineEdit.setText('00:00:00')
		self.elapsedCycleTimeLineEdit.setAlignment(QtCore.Qt.AlignRight)

		self.totalCycleTimeLineEdit = QtWidgets.QLineEdit()
		self.totalCycleTimeLineEdit.setReadOnly(True)
		self.totalCycleTimeLineEdit.setAlignment(QtCore.Qt.AlignRight)

		self.remainingCycleTimeLineEdit = QtWidgets.QLineEdit()
		self.remainingCycleTimeLineEdit.setReadOnly(True)
		self.remainingCycleTimeLineEdit.setAlignment(QtCore.Qt.AlignRight)

		self.elapsedTimeLineEdit = QtWidgets.QLineEdit()
		self.elapsedTimeLineEdit.setReadOnly(True)
		self.elapsedTimeLineEdit.setText('00:00:00')
		self.elapsedTimeLineEdit.setAlignment(QtCore.Qt.AlignRight)

		self.totalTimeLineEdit = QtWidgets.QLineEdit()
		self.totalTimeLineEdit.setReadOnly(True)
		self.totalTimeLineEdit.setAlignment(QtCore.Qt.AlignRight)

		self.remainingTimeLineEdit = QtWidgets.QLineEdit()
		self.remainingTimeLineEdit.setReadOnly(True)
		self.remainingTimeLineEdit.setAlignment(QtCore.Qt.AlignRight)

		# Add Validators the Line Edits
		self.intValidator = QtGui.QIntValidator()
		self.floatValidator = QtGui.QDoubleValidator()

		self.depositionTimeLineEdit.setValidator(self.intValidator)
		self.depositionVoltageLineEdit.setValidator(self.floatValidator)
		self.depositionWaitLineEdit.setValidator(self.intValidator)
		self.depositionCutoffILineEdit.setValidator(self.floatValidator)
		self.depositionCutoffCLineEdit.setValidator(self.floatValidator)
		self.stripTimeLineEdit.setValidator(self.intValidator)
		self.stripVoltageLineEdit.setValidator(self.floatValidator)
		self.stripWaitLineEdit.setValidator(self.intValidator)
		self.stripCutoffILineEdit.setValidator(self.floatValidator)
		self.stripCutoffCLineEdit.setValidator(self.floatValidator)
		self.totalLoopsLineEdit.setValidator(self.intValidator)
		self.initialWaitLineEdit.setValidator(self.intValidator)

		# Add Line Edits to the Form
		self.inputFormLayout.setWidget(0, QtWidgets.QFormLayout.FieldRole, self.userLineEdit)
		self.inputFormLayout.setWidget(1, QtWidgets.QFormLayout.FieldRole, self.totalLoopsLineEdit)
		self.inputFormLayout.setWidget(2, QtWidgets.QFormLayout.FieldRole, self.initialWaitLineEdit)

		self.depositionFormLayout.setWidget(0, QtWidgets.QFormLayout.FieldRole, self.depositionTimeLineEdit)
		self.depositionFormLayout.setWidget(1, QtWidgets.QFormLayout.FieldRole, self.depositionVoltageLineEdit)
		self.depositionFormLayout.setWidget(2, QtWidgets.QFormLayout.FieldRole, self.depositionWaitLineEdit)
		self.depositionFormLayout.setWidget(3, QtWidgets.QFormLayout.FieldRole, self.depositionCutoffILineEdit)
		self.depositionFormLayout.setWidget(4, QtWidgets.QFormLayout.FieldRole, self.depositionCutoffCLineEdit)

		self.stripFormLayout.setWidget(0, QtWidgets.QFormLayout.FieldRole, self.stripTimeLineEdit)
		self.stripFormLayout.setWidget(1, QtWidgets.QFormLayout.FieldRole, self.stripVoltageLineEdit)
		self.stripFormLayout.setWidget(2, QtWidgets.QFormLayout.FieldRole, self.stripWaitLineEdit)
		self.stripFormLayout.setWidget(3, QtWidgets.QFormLayout.FieldRole, self.stripCutoffILineEdit)
		self.stripFormLayout.setWidget(4, QtWidgets.QFormLayout.FieldRole, self.stripCutoffCLineEdit)


		self.measurementFormLayout.setWidget(0, QtWidgets.QFormLayout.FieldRole, self.activeVoltageLineEdit)
		self.measurementFormLayout.setWidget(1, QtWidgets.QFormLayout.FieldRole, self.activeCurrentLineEdit)
		self.measurementFormLayout.setWidget(2, QtWidgets.QFormLayout.FieldRole, self.activeChargeLineEdit)
		self.measurementFormLayout.setWidget(3, QtWidgets.QFormLayout.FieldRole, self.activeChargeCycleLineEdit)

		self.timeFormLayout.setWidget(0, QtWidgets.QFormLayout.FieldRole, self.currentLoopLineEdit)
		self.timeFormLayout.setWidget(1, QtWidgets.QFormLayout.FieldRole, self.elapsedCycleTimeLineEdit)
		self.timeFormLayout.setWidget(2, QtWidgets.QFormLayout.FieldRole, self.totalCycleTimeLineEdit)
		self.timeFormLayout.setWidget(3, QtWidgets.QFormLayout.FieldRole, self.remainingCycleTimeLineEdit)
		self.timeFormLayout.setWidget(4, QtWidgets.QFormLayout.FieldRole, self.elapsedTimeLineEdit)
		self.timeFormLayout.setWidget(5, QtWidgets.QFormLayout.FieldRole, self.totalTimeLineEdit)
		self.timeFormLayout.setWidget(6, QtWidgets.QFormLayout.FieldRole, self.remainingTimeLineEdit)

		# Set Font Properties
		if platform.system() == 'Windows':
			self.groupBoxFontSize = 16
			self.myFontSize = 12
		if platform.system() == 'Darwin':
			self.groupBoxFontSize = 24
			self.myFontSize = 20

		self.groupBoxFont = QtGui.QFont()
		self.groupBoxFont.setFamily('Arial')
		self.groupBoxFont.setPointSize(self.groupBoxFontSize)

		# Apply Font to GroupBoxes
		self.depositionGroupBox.setFont(self.groupBoxFont)
		self.stripGroupBox.setFont(self.groupBoxFont)
		self.measurementGroupBox.setFont(self.groupBoxFont)
		self.timeGroupBox.setFont(self.groupBoxFont)

		self.font = QtGui.QFont()
		self.font.setFamily('Arial')
		self.font.setPointSize(self.myFontSize)

		# Apply Font to Widgets
		self.keithleyPushButton.setFont(self.font)

		self.userLabel.setFont(self.font)
		self.depositionTimeLabel.setFont(self.font)
		self.depositionVoltageLabel.setFont(self.font)
		self.depositionWaitLabel.setFont(self.font)
		self.cutoffDepositionILabel.setFont(self.font)
		self.cutoffDepositionCLabel.setFont(self.font)
		self.stripTimeLabel.setFont(self.font)
		self.stripVoltageLabel.setFont(self.font)
		self.stripWaitLabel.setFont(self.font)
		self.cutoffStripILabel.setFont(self.font)
		self.cutoffStripCLabel.setFont(self.font)
		self.totalLoopsLabel.setFont(self.font)
		self.initialWaitLabel.setFont(self.font)
		
		self.userLineEdit.setFont(self.font)
		self.depositionTimeLineEdit.setFont(self.font)
		self.depositionVoltageLineEdit.setFont(self.font)
		self.depositionWaitLineEdit.setFont(self.font)
		self.depositionCutoffILineEdit.setFont(self.font)
		self.depositionCutoffCLineEdit.setFont(self.font)
		self.stripTimeLineEdit.setFont(self.font)
		self.stripVoltageLineEdit.setFont(self.font)
		self.stripWaitLineEdit.setFont(self.font)
		self.stripCutoffILineEdit.setFont(self.font)
		self.stripCutoffCLineEdit.setFont(self.font)
		self.totalLoopsLineEdit.setFont(self.font)
		self.initialWaitLineEdit.setFont(self.font)

		self.activeVoltageLabel.setFont(self.font)
		self.activeCurrentLabel.setFont(self.font)
		self.activeChargeLabel.setFont(self.font)
		self.activeChargeCycleLabel.setFont(self.font)

		self.currentLoopLabel.setFont(self.font)

		self.elapsedCycleTimeLabel.setFont(self.font)
		self.totalCycleTimeLabel.setFont(self.font)
		self.remainingCycleTimeLabel.setFont(self.font)

		self.elapsedTimeLabel.setFont(self.font)
		self.totalTimeLabel.setFont(self.font)
		self.remainingTimeLabel.setFont(self.font)

		self.activeVoltageLineEdit.setFont(self.font)
		self.activeCurrentLineEdit.setFont(self.font)
		self.activeChargeLineEdit.setFont(self.font)
		self.activeChargeCycleLineEdit.setFont(self.font)

		self.currentLoopLineEdit.setFont(self.font)
		
		self.elapsedCycleTimeLineEdit.setFont(self.font)
		self.totalCycleTimeLineEdit.setFont(self.font)
		self.remainingCycleTimeLineEdit.setFont(self.font)
		
		self.elapsedTimeLineEdit.setFont(self.font)
		self.totalTimeLineEdit.setFont(self.font)
		self.remainingTimeLineEdit.setFont(self.font)

		self.saveLocationLineEdit.setStyleSheet("QLineEdit { background: rgb(223, 223, 223);}")
		self.activeVoltageLineEdit.setStyleSheet("QLineEdit { background: rgb(223, 223, 223);}")
		self.activeCurrentLineEdit.setStyleSheet("QLineEdit { background: rgb(223, 223, 223);}")
		self.activeChargeLineEdit.setStyleSheet("QLineEdit { background: rgb(223, 223, 223);}")
		self.activeChargeCycleLineEdit.setStyleSheet("QLineEdit { background: rgb(223, 223, 223);}")
		self.currentLoopLineEdit.setStyleSheet("QLineEdit { background: rgb(223, 223, 223);}")
		self.elapsedCycleTimeLineEdit.setStyleSheet("QLineEdit { background: rgb(223, 223, 223);}")
		self.totalCycleTimeLineEdit.setStyleSheet("QLineEdit { background: rgb(223, 223, 223);}")
		self.remainingCycleTimeLineEdit.setStyleSheet("QLineEdit { background: rgb(223, 223, 223);}")
		self.elapsedTimeLineEdit.setStyleSheet("QLineEdit { background: rgb(223, 223, 223);}")
		self.totalTimeLineEdit.setStyleSheet("QLineEdit { background: rgb(223, 223, 223);}")
		self.remainingTimeLineEdit.setStyleSheet("QLineEdit { background: rgb(223, 223, 223);}")

		#Apply Line Edit Widths
		self.fm = QtGui.QFontMetrics(self.font)
		self.pixelsWide = self.fm.width('8888:88:88')

		self.depositionTimeLineEdit.setFixedWidth(self.pixelsWide)
		self.depositionVoltageLineEdit.setFixedWidth(self.pixelsWide)
		self.depositionWaitLineEdit.setFixedWidth(self.pixelsWide)
		self.depositionCutoffILineEdit.setFixedWidth(self.pixelsWide)
		self.depositionCutoffCLineEdit.setFixedWidth(self.pixelsWide)
		self.stripTimeLineEdit.setFixedWidth(self.pixelsWide)
		self.stripVoltageLineEdit.setFixedWidth(self.pixelsWide)
		self.stripWaitLineEdit.setFixedWidth(self.pixelsWide)
		self.stripCutoffILineEdit.setFixedWidth(self.pixelsWide)
		self.stripCutoffCLineEdit.setFixedWidth(self.pixelsWide)
		self.activeVoltageLineEdit.setFixedWidth(self.pixelsWide)
		self.activeCurrentLineEdit.setFixedWidth(self.pixelsWide)
		self.activeChargeLineEdit.setFixedWidth(self.pixelsWide)
		self.activeChargeCycleLineEdit.setFixedWidth(self.pixelsWide)
		self.currentLoopLineEdit.setFixedWidth(self.pixelsWide)
		self.elapsedCycleTimeLineEdit.setFixedWidth(self.pixelsWide)
		self.totalCycleTimeLineEdit.setFixedWidth(self.pixelsWide)
		self.remainingCycleTimeLineEdit.setFixedWidth(self.pixelsWide)
		self.elapsedTimeLineEdit.setFixedWidth(self.pixelsWide)
		self.totalTimeLineEdit.setFixedWidth(self.pixelsWide)
		self.remainingTimeLineEdit.setFixedWidth(self.pixelsWide)

		# Define and set the size policies of the Plot
		self.plotWindowSizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding,QtWidgets.QSizePolicy.Expanding)
		self.plotWindowSizePolicy.setHorizontalStretch(1)
		self.plotWindowSizePolicy.setVerticalStretch(1)
		self.Ivtcanvas.setSizePolicy(self.plotWindowSizePolicy)

		# Connect Signals
		self.settingsPushButton.clicked.connect(self.editLiveSettings)
		self.cdPushButton.clicked.connect(self.setSaveLocation)
		self.keithleyPushButton.clicked.connect(self.selectKeithley)
		self.startScienceButton.clicked.connect(self.startScience)
		self.stopScienceButton.clicked.connect(self.stopScienceButtonFunc)
		self.myIvtAutoscale = True
		self.myQvtAutoscale = True
		self.myQvtCycleAutoscale = True
		self.IvtPlay.clicked.connect(self.startIvtAutoscale)
		self.IvtStop.clicked.connect(self.stopIvtAutoscale)
		self.QvtPlay.clicked.connect(self.startQvtAutoscale)
		self.QvtStop.clicked.connect(self.stopQvtAutoscale)
		self.QvtCyclePlay.clicked.connect(self.startQvtCycleAutoscale)
		self.QvtCycleStop.clicked.connect(self.stopQvtCycleAutoscale)

		self.depositionTimeLineEdit.textEdited.connect(self.parametersEdited)
		self.depositionVoltageLineEdit.textEdited.connect(self.parametersEdited)
		self.depositionWaitLineEdit.textEdited.connect(self.parametersEdited)
		self.depositionCutoffILineEdit.textEdited.connect(self.parametersEdited)
		self.depositionCutoffCLineEdit.textEdited.connect(self.parametersEdited)
		self.stripTimeLineEdit.textEdited.connect(self.parametersEdited)
		self.stripVoltageLineEdit.textEdited.connect(self.parametersEdited)
		self.stripWaitLineEdit.textEdited.connect(self.parametersEdited)
		self.stripCutoffILineEdit.textEdited.connect(self.parametersEdited)
		self.stripCutoffCLineEdit.textEdited.connect(self.parametersEdited)
		self.totalLoopsLineEdit.textEdited.connect(self.parametersEdited)
		self.initialWaitLineEdit.textEdited.connect(self.parametersEdited)

		self.setCentralWidget(self.mainWidget)
		self.show()
		self.move(50,50)

		try:
			self.rm = pyvisa.ResourceManager()
			self.resourceListTuple = self.rm.list_resources()
		except:
			self.resourceListTuple = ('K1',)
			self.resourceListTuple = ('K1', 'K2', 'K3', 'K4')
		self.resourceListTupleList = list(self.resourceListTuple)
		self.resourceListTupleList.append('test')
		self.resourceListTuple = self.resourceListTupleList

		if len(self.resourceListTuple) == 1:
			self.button1.setText(self.resourceListTuple[0])
		else:
			self.selectKeithley()

		# self.keithley = mkf.connectToKeithley('GPIB0::22::INSTR')
		self.keithley = mkf.connectToKeithley('test')

		# Initialize Default Values
		self.parametersEdited()
		self.adjustSize()
		plt.show()

	def setSaveLocation(self):
		self.myFilter = 'Text Files (*.txt)'
		self.option = QtWidgets.QFileDialog.DontConfirmOverwrite
		self.newSaveLocation = QtWidgets.QFileDialog.getSaveFileName(None, 'Select the Folder', filter = self.myFilter, options = self.option)[0]
		if self.newSaveLocation != '':
			print ('updating save location')
			self.saveLocationLineEdit.setText(self.newSaveLocation)
		else:
			print ('keeping old save location')
			return 'canceled'

	def selectKeithley(self):
		self.selectKeithleyWidget = QtWidgets.QDialog(self.mainWidget)
		self.selectKeithleyWidget.setAttribute(QtCore.Qt.WA_DeleteOnClose)
		self.selectKeithleyWidget.setWindowTitle('Select a Keithley to use for cycling')
		self.selectKeithleyWidgetFont = self.selectKeithleyWidget.font()
		self.selectKeithleyWidgetFont.setPointSize(16)
		self.selectKeithleyWidget.setFont(self.selectKeithleyWidgetFont)
		self.selectKeithleyWidget.setWindowFlags(QtCore.Qt.Dialog | QtCore.Qt.WindowTitleHint | QtCore.Qt.WindowCloseButtonHint)
		self.selectKeithleyWidget.finished.connect(self.dialogFinished)

		self.selectKeithleyWidgetGridLayout = QtWidgets.QGridLayout(self.selectKeithleyWidget)

		self.selectKeithleyList = QtWidgets.QListWidget(self.selectKeithleyWidget)
		self.selectKeithleyList.itemDoubleClicked.connect(self.keithleySelected)
		self.selectKeithleyList.setFont(self.selectKeithleyWidgetFont)
		self.selectKeithleyList.addItems(self.resourceListTuple)

		self.selectButton = QtWidgets.QPushButton(self.selectKeithleyWidget)
		self.selectButton.setText('Select')
		self.selectButton.clicked.connect(self.keithleySelected)

		self.selectKeithleyWidgetGridLayout.addWidget(self.selectKeithleyList, 0,0,1,2)
		self.selectKeithleyWidgetGridLayout.addWidget(self.selectButton, 1,0,1,2)

		self.selectKeithleyWidget.open()

	def keithleySelected(self):
		print ('Keithley Selected')
		self.selectKeithleyWidget.done(QtWidgets.QDialog.Accepted)
		self.keithleyPushButton.setText(self.selectKeithleyList.currentItem().text())

	def dialogFinished(self, r):
		print ('done with dialog')
		print (r)
		if r == 0:
			print ('No Keithley Selected')
			self.close()
		else:
			self.selection = self.selectKeithleyList.currentItem().text()
			self.keithley = mkf.connectToKeithley(self.selection)
			print (self.selection)

	def startScience(self):
		self.stopScienceFlag = False
		self.depositionChargeCutoffFlag = False
		self.stripChargeCutoffFlag = False
		if self.saveLocationLineEdit.text() == '':
			status = self.setSaveLocation()
			if status == 'canceled':
				self.stopScience()
				return
		# Check if file exists
		if os.path.exists(self.saveLocationLineEdit.text()) == True:
			# Ask if they want to proceed.
			self.fileExistsMessageBox = QtWidgets.QMessageBox()
			self.fileExistsMessageBox.setWindowTitle('File Already Exists!')
			self.fileExistsMessageBox.setText('The chosen file name already exists. Would you like to overwrite?')
			self.fileExistsMessageBox.setIcon(QtWidgets.QMessageBox.Warning)
			self.fileExistsMessageBox.setStandardButtons(QtWidgets.QMessageBox.NoButton)
			self.fileExistsMessageBox.addButton('Overwrite', QtWidgets.QMessageBox.YesRole)
			self.fileExistsMessageBox.addButton('Cancel', QtWidgets.QMessageBox.NoRole)
			self.choice = self.fileExistsMessageBox.exec_()
			if self.choice == 1:
				self.stopScience()
				return


		self.startScienceButton.setEnabled(False)
		self.stopScienceButton.setEnabled(True)
		self.settingsPushButton.setEnabled(True)
		self.currentLoopLineEdit.setText("0")

		self.userLineEdit.setReadOnly(True)
		self.depositionTimeLineEdit.setReadOnly(True)
		self.depositionVoltageLineEdit.setReadOnly(True)
		self.depositionWaitLineEdit.setReadOnly(True)
		self.depositionCutoffILineEdit.setReadOnly(True)
		self.depositionCutoffCLineEdit.setReadOnly(True)
		self.stripTimeLineEdit.setReadOnly(True)
		self.stripVoltageLineEdit.setReadOnly(True)
		self.stripWaitLineEdit.setReadOnly(True)
		self.stripCutoffILineEdit.setReadOnly(True)
		self.stripCutoffCLineEdit.setReadOnly(True)
		self.totalLoopsLineEdit.setReadOnly(True)
		self.initialWaitLineEdit.setReadOnly(True)

		self.userLineEdit.setStyleSheet("QLineEdit { background: rgb(223, 223, 223);}")
		self.depositionTimeLineEdit.setStyleSheet("QLineEdit { background: rgb(223, 223, 223);}")
		self.depositionVoltageLineEdit.setStyleSheet("QLineEdit { background: rgb(223, 223, 223);}")
		self.depositionWaitLineEdit.setStyleSheet("QLineEdit { background: rgb(223, 223, 223);}")
		self.depositionCutoffILineEdit.setStyleSheet("QLineEdit { background: rgb(223, 223, 223);}")
		self.depositionCutoffCLineEdit.setStyleSheet("QLineEdit { background: rgb(223, 223, 223);}")
		self.stripTimeLineEdit.setStyleSheet("QLineEdit { background: rgb(223, 223, 223);}")
		self.stripVoltageLineEdit.setStyleSheet("QLineEdit { background: rgb(223, 223, 223);}")
		self.stripWaitLineEdit.setStyleSheet("QLineEdit { background: rgb(223, 223, 223);}")
		self.stripCutoffILineEdit.setStyleSheet("QLineEdit { background: rgb(223, 223, 223);}")
		self.stripCutoffCLineEdit.setStyleSheet("QLineEdit { background: rgb(223, 223, 223);}")
		self.totalLoopsLineEdit.setStyleSheet("QLineEdit { background: rgb(223, 223, 223);}")
		self.initialWaitLineEdit.setStyleSheet("QLineEdit { background: rgb(223, 223, 223);}")

		with open(self.saveLocationLineEdit.text(),'w') as file:
			file.write(f'User:\t'+'Dr. Tyler Hernandez'+'\n')
			file.write(datetime.datetime.now().strftime('Date:\t%Y/%m/%d\nTime:\t%H:%M:%S\n'))
			file.write('\n')
			file.write(f'Loop Count:\t{self.totalLoops}\n')
			file.write(f'Initial Delay (s):\t{self.initialWait:d}\n')
			file.write('\n')
			file.write('Deposition Parameters\n')
			file.write(f'Voltage (V):\t{self.depositionVoltage:f}\n')
			file.write(f'Deposition Time (s):\t{self.depositionTime:d}\n')
			file.write(f'Deposition Wait Time (s):\t{self.depositionWait:d}\n')
			file.write(f'Deposition Cutoff Current (A):\t{self.depositionCurrentCutoff:f}\n')
			file.write(f'Deposition Cutoff Charge (Q):\t{self.depositionChargeCutoff:f}\n')
			file.write('\n')
			file.write('Stripping Parameters\n')
			file.write(f'Voltage (V):\t{self.stripVoltage:f}\n')
			file.write(f'Strip Time (s):\t{self.stripTime:d}\n')
			file.write(f'Strip Wait Time (s):\t{self.stripWait:d}\n')
			file.write(f'Strip Cutoff Current (A):\t{self.stripCurrentCutoff:f}\n')
			file.write(f'Strip Cutoff Charge (Q):\t{self.stripChargeCutoff:f}\n')
			file.write('\n')

		self.activeVoltageList = []
		self.activeCurrentList = []
		self.activeTimeList = []
		self.activeChargeList = []
		self.activeChargeCycleList = []
		self.m = 0
		self.startCycleIndex = self.m

		if self.tabWidget.currentIndex() == 3:
			self.tabWidget.setCurrentIndex(0)
		self.thread = QtCore.QThread()
		self.worker = Worker()
		self.worker.moveToThread(self.thread)
		self.worker.progress.connect(self.stepIteration)
		self.worker.finished.connect(self.thread.quit)
		self.worker.finished.connect(self.worker.deleteLater)
		self.thread.started.connect(self.worker.run)
		self.thread.finished.connect(self.stopScience)
		self.thread.finished.connect(self.thread.deleteLater)
		self.thread.start()

		print ('Science Started')

	def stopScienceButtonFunc(self):
		self.stopScienceFlag = True

	def stopScience(self):
		if self.stopScienceFlag == True:
			print ('Abort detected! Thread finished.')
		self.stopScienceButton.setEnabled(False)
		self.settingsPushButton.setEnabled(False)
		self.startScienceButton.setEnabled(True)

		self.userLineEdit.setReadOnly(False)
		self.depositionTimeLineEdit.setReadOnly(False)
		self.depositionVoltageLineEdit.setReadOnly(False)
		self.depositionWaitLineEdit.setReadOnly(False)
		self.depositionCutoffILineEdit.setReadOnly(False)
		self.depositionCutoffCLineEdit.setReadOnly(False)
		self.stripTimeLineEdit.setReadOnly(False)
		self.stripVoltageLineEdit.setReadOnly(False)
		self.stripWaitLineEdit.setReadOnly(False)
		self.stripCutoffILineEdit.setReadOnly(False)
		self.stripCutoffCLineEdit.setReadOnly(False)
		self.totalLoopsLineEdit.setReadOnly(False)
		self.initialWaitLineEdit.setReadOnly(False)

		self.userLineEdit.setStyleSheet("QLineEdit { background: rgb(255, 255, 255);}")
		self.depositionTimeLineEdit.setStyleSheet("QLineEdit { background: rgb(255, 255, 255);}")
		self.depositionVoltageLineEdit.setStyleSheet("QLineEdit { background: rgb(255, 255, 255);}")
		self.depositionWaitLineEdit.setStyleSheet("QLineEdit { background: rgb(255, 255, 255);}")
		self.depositionCutoffILineEdit.setStyleSheet("QLineEdit { background: rgb(255, 255, 255);}")
		self.depositionCutoffCLineEdit.setStyleSheet("QLineEdit { background: rgb(255, 255, 255);}")
		self.stripTimeLineEdit.setStyleSheet("QLineEdit { background: rgb(255, 255, 255);}")
		self.stripVoltageLineEdit.setStyleSheet("QLineEdit { background: rgb(255, 255, 255);}")
		self.stripWaitLineEdit.setStyleSheet("QLineEdit { background: rgb(255, 255, 255);}")
		self.stripCutoffILineEdit.setStyleSheet("QLineEdit { background: rgb(255, 255, 255);}")
		self.stripCutoffCLineEdit.setStyleSheet("QLineEdit { background: rgb(255, 255, 255);}")
		self.totalLoopsLineEdit.setStyleSheet("QLineEdit { background: rgb(255, 255, 255);}")
		self.initialWaitLineEdit.setStyleSheet("QLineEdit { background: rgb(255, 255, 255);}")

	def IvtToolbarClicked(self, event):
		print ('IVT toolbar clicked')
		self.stopIvtAutoscale()

	def startIvtAutoscale(self):
		self.myIvtAutoscale = True
		self.IvtPlay.setChecked(True)
		self.IvtStop.setChecked(False)
		print ('start ivt autoscale')

	def stopIvtAutoscale(self):
		self.myIvtAutoscale = False
		self.IvtPlay.setChecked(False)
		self.IvtStop.setChecked(True)
		print ('stop ivt autoscale')

	def QvtToolbarClicked(self, event):
		print ('QVT toolbar clicked')
		self.stopQvtAutoscale()

	def startQvtAutoscale(self):
		self.myQvtAutoscale = True
		self.QvtPlay.setChecked(True)
		self.QvtStop.setChecked(False)
		print ('start qvt autoscale')

	def stopQvtAutoscale(self):
		self.myQvtAutoscale = False
		self.QvtPlay.setChecked(False)
		self.QvtStop.setChecked(True)
		print ('stop qvt autoscale')

	def QvtCycleToolbarClicked(self, event):
		print ('QVTCycle toolbar clicked')
		self.stopQvtCycleAutoscale()

	def startQvtCycleAutoscale(self):
		self.myQvtCycleAutoscale = True
		self.QvtCyclePlay.setChecked(True)
		self.QvtCycleStop.setChecked(False)
		print ('start qvtCycle autoscale')

	def stopQvtCycleAutoscale(self):
		self.myQvtCycleAutoscale = False
		self.QvtCyclePlay.setChecked(False)
		self.QvtCycleStop.setChecked(True)
		print ('stop qvtCycle autoscale')

	def editLiveSettings(self):
		self.editLiveSettingsWindow = EditLiveSettingsWindow()

	def parametersEdited(self):
		if self.tabWidget.currentIndex() != 3:
			self.tabWidget.setCurrentIndex(3)
		
		initialWait = 0
		depositionTime = 0
		depositionWait = 0
		depositionVoltage = 0

		stripTime = 0
		stripWait = 0
		stripVoltage = 0

		try:
			self.initialWait = int(self.initialWaitLineEdit.text())
			self.totalLoops = int(self.totalLoopsLineEdit.text())
			self.depositionTime = int(self.depositionTimeLineEdit.text())
			self.depositionWait = int(self.depositionWaitLineEdit.text())
			self.stripTime = int(self.stripTimeLineEdit.text())
			self.stripWait = int(self.stripWaitLineEdit.text())

			self.loopTime = self.depositionTime + self.depositionWait + self.stripTime + self.stripWait
			self.totalTime = self.initialWait + self.totalLoops*self.loopTime

			self.totalIterations = 1000*self.totalTime//self.timeInterval
			# Convert Strings to Floats
			self.depositionVoltage = float(self.depositionVoltageLineEdit.text())
			self.stripVoltage = float(self.stripVoltageLineEdit.text())
			self.depositionCurrentCutoff = float(self.depositionCutoffILineEdit.text())
			self.stripCurrentCutoff = float(self.stripCutoffILineEdit.text())
			self.depositionChargeCutoff = float(self.depositionCutoffCLineEdit.text())
			self.stripChargeCutoff = float(self.stripCutoffCLineEdit.text())

			self.x0 = -self.initialWait
			self.x1 = self.depositionTime
			self.x2 = self.x1 + self.depositionWait
			self.x3 = self.x2 + self.stripTime
			self.x4 = self.x3 + self.stripWait

			self.y0 = self.depositionVoltage
			self.y1 = self.stripVoltage

			self.cycleProfileaxes.clear()
			self.cycleProfileaxes.set_title('Cycle Profile')
			self.cycleProfileaxes.set_xlabel('Time (seconds)')
			self.cycleProfileaxes.set_ylabel('Voltage (V)')
			self.cycleProfileaxes.axhline(0, c='k')
			self.cycleProfileaxes.axvline(0, c='k')
			self.cycleProfileaxes.plot([self.x0, 0, 0, self.x1, self.x1, self.x2, self.x2, self.x3, self.x3, self.x4],[0, 0, self.y0, self.y0, 0, 0 ,self.y1, self.y1, 0, 0], c='r', linewidth = 4)
			self.cycleProfileaxes.relim()
			self.cycleProfileaxes.autoscale(True)
			self.cycleProfileaxes.set_ylim(-1.5,1.5)
			self.cycleProfilecanvas.draw()

			# Update ETA
			self.loopHours = self.loopTime//3600
			self.loopMinutes = (self.loopTime - 3600*self.loopHours)//60
			self.loopSeconds = self.loopTime - 3600*self.loopHours - 60*self.loopMinutes
			self.elapsedCycleTimeLineEdit.setText('00:00:00')
			self.totalCycleTimeLineEdit.setText(f'{self.loopHours:02}:{self.loopMinutes:02}:{self.loopSeconds:02}')
			self.remainingCycleTimeLineEdit.setText(f'{self.loopHours:02}:{self.loopMinutes:02}:{self.loopSeconds:02}')
			self.loopProgressBar.setMaximum(1000*self.loopTime//self.timeInterval)
			self.loopProgressBar.setValue(0)

			self.totalHours = self.totalTime//3600
			self.totalMinutes = (self.totalTime - 3600*self.totalHours)//60
			self.totalSeconds = self.totalTime - 3600*self.totalHours - 60*self.totalMinutes
			self.elapsedTimeLineEdit.setText('00:00:00')
			self.totalTimeLineEdit.setText(f'{self.totalHours:02}:{self.totalMinutes:02}:{self.totalSeconds:02}')
			self.remainingTimeLineEdit.setText(f'{self.totalHours:02}:{self.totalMinutes:02}:{self.totalSeconds:02}')
			self.totalProgressBar.setMaximum(self.totalIterations)
			self.totalProgressBar.setValue(0)
		except Exception as e: print(e)

	def stepIteration(self, n, rawData):
		self.activeVoltage = rawData[0]
		self.activeVoltageList.append(self.activeVoltage)
		self.activeVoltageLineEdit.setText(f'{self.activeVoltage:.3f}')

		self.activeCurrent = rawData[1]
		self.activeCurrentList.append(self.activeCurrent)
		self.activeCurrentLineEdit.setText(f'{self.activeCurrent:.3f}')

		if self.m == 0:
			self.startTime = rawData[3]
		self.activeTime = rawData[3] - self.initialWait - self.startTime
		self.activeTimeList.append(self.activeTime)

		if self.m == 0:
			self.changeCharge = 0
			self.cumulativeCharge = 0
		else:
			self.changeCharge = (self.activeCurrentList[-2] + self.activeCurrentList[-1])*(self.activeTimeList[-1] - self.activeTimeList[-2])/2
			self.cumulativeCharge = self.activeChargeList[-1] + self.changeCharge
		self.activeChargeLineEdit.setText(f'{self.cumulativeCharge:.3f}')
		self.activeChargeList.append(self.cumulativeCharge)

		self.elapsedCycleIterations = (max(0,n - 1000*self.initialWait//self.timeInterval))%(self.loopTime*1000//self.timeInterval)
		if self.elapsedCycleIterations == 0:
			self.changeChargeCycle = 0
			self.cumulativeChargeCycle = 0
			self.depositionChargeCutoffFlag = False
			self.stripChargeCutoffFlag = False
			self.startCycleIndex = self.m
		else:
			self.changeChargeCycle = (self.activeCurrentList[-2] + self.activeCurrentList[-1])*(self.activeTimeList[-1] - self.activeTimeList[-2])/2
			self.cumulativeChargeCycle = self.activeChargeCycleList[-1] + self.changeChargeCycle
		self.activeChargeCycleLineEdit.setText(f'{self.cumulativeChargeCycle:.3f}')
		self.activeChargeCycleList.append(self.cumulativeChargeCycle)

		if self.cumulativeChargeCycle <= self.depositionChargeCutoff:
			self.depositionChargeCutoffFlag = True
		if self.cumulativeChargeCycle >= self.stripChargeCutoff:
			if self.stripTime != 0 and self.elapsedCycleIterations >= (self.depositionTime + self.depositionWait)*1000//self.timeInterval:
				self.stripChargeCutoffFlag = True

		if n!= self.totalIterations:
			self.elapsedCycleTime = ((self.m - self.startCycleIndex)*self.timeInterval//1000)
		else:
			self.elapsedCycleTime = self.loopTime
		self.elapsedCycleHours = self.elapsedCycleTime//3600
		self.elapsedCycleMinutes = (self.elapsedCycleTime - self.elapsedCycleHours*3600)//60
		self.elapsedCycleSeconds = self.elapsedCycleTime - self.elapsedCycleHours*3600 - self.elapsedCycleMinutes*60
		
		self.remainingCycleTime = self.loopTime - self.elapsedCycleIterations*self.timeInterval//1000
		if n == self.totalIterations:
			self.remainingCycleTime = 0
		self.remainingCycleHours = self.remainingCycleTime//3600
		self.remainingCycleMinutes = (self.remainingCycleTime - self.remainingCycleHours*3600)//60
		self.remainingCycleSeconds = self.remainingCycleTime - self.remainingCycleHours*3600 - self.remainingCycleMinutes*60

		self.elapsedTime = self.m*self.timeInterval//1000
		self.elapsedHours = self.elapsedTime//3600
		self.elapsedMinutes = (self.elapsedTime - self.elapsedHours*3600)//60
		self.elapsedSeconds = self.elapsedTime - self.elapsedHours*3600 - self.elapsedMinutes*60

		if self.loopTime == 0:
			self.currentLoop = 0
		else:
			self.currentLoop = min(self.totalLoops,max(0,1 + (n - 1000*self.initialWait//self.timeInterval)//(1000*self.loopTime//self.timeInterval)))
		
		self.remainingCycles = self.totalLoops - self.currentLoop
		if self.currentLoop == 0:
			self.remainingWaitTime = self.initialWait - min(self.elapsedTime,self.initialWait)
			self.remainingTime = self.remainingCycles*self.loopTime + self.remainingWaitTime
		else:
			self.remainingTime = self.remainingCycles*self.loopTime + self.remainingCycleTime
		self.remainingHours = self.remainingTime//3600
		self.remainingMinutes = (self.remainingTime - self.remainingHours*3600)//60
		self.remainingSeconds = self.remainingTime - self.remainingHours*3600 - self.remainingMinutes*60

		self.loopProgressBar.setValue(self.elapsedCycleIterations)
		self.totalProgressBar.setValue(n)

		if (self.m%(1000//self.timeInterval) == 0) or n == self.totalIterations:

			self.totalTime = self.elapsedTime + self.remainingTime
			self.totalHours = self.totalTime//3600
			self.totalMinutes = (self.totalTime - 3600*self.totalHours)//60
			self.totalSeconds = self.totalTime - 3600*self.totalHours - 60*self.totalMinutes

			self.currentLoopLineEdit.setText(str(self.currentLoop))
			self.elapsedCycleTimeLineEdit.setText(f'{self.elapsedCycleHours:02}:{self.elapsedCycleMinutes:02}:{self.elapsedCycleSeconds:02}')
			self.remainingCycleTimeLineEdit.setText(f'{self.remainingCycleHours:02}:{self.remainingCycleMinutes:02}:{self.remainingCycleSeconds:02}')
			self.elapsedTimeLineEdit.setText(f'{self.elapsedHours:02}:{self.elapsedMinutes:02}:{self.elapsedSeconds:02}')
			self.remainingTimeLineEdit.setText(f'{self.remainingHours:02}:{self.remainingMinutes:02}:{self.remainingSeconds:02}')
			self.totalTimeLineEdit.setText(f'{self.totalHours:02}:{self.totalMinutes:02}:{self.totalSeconds:02}')

			if not self.myIvtAutoscale:
				self.Ivtaxis = self.Ivtaxes.axis()
			self.Ivtaxes.clear()
			self.Ivtaxes.set_title('I v t')
			self.Ivtaxes.set_xlabel('Time (seconds)')
			self.Ivtaxes.set_ylabel('Current (A)')
			self.Ivtaxes.axhline(0,c='k')
			self.Ivtaxes.axvline(0,c='k')
			self.Ivtaxes.plot(self.activeTimeList, self.activeCurrentList, linewidth=4)
			self.Ivtaxes.relim()
			self.Ivtaxes.autoscale(True)
			if not self.myIvtAutoscale:
				self.Ivtaxes.axis(self.Ivtaxis)
			self.Ivtcanvas.draw()

			if not self.myQvtAutoscale:
				self.Qvtaxis = self.Qvtaxes.axis()
			self.Qvtaxes.clear()
			self.Qvtaxes.set_title('Q v t')
			self.Qvtaxes.set_xlabel('Time (seconds)')
			self.Qvtaxes.set_ylabel('Charge (C)')
			self.Qvtaxes.axhline(0,c='k')
			self.Qvtaxes.axvline(0,c='k')
			self.Qvtaxes.plot(self.activeTimeList, self.activeChargeList, linewidth=4)
			self.Qvtaxes.relim()
			self.Qvtaxes.autoscale(True)
			if not self.myQvtAutoscale:
				self.Qvtaxes.axis(self.Qvtaxis)
			self.Qvtcanvas.draw()

			if not self.myQvtCycleAutoscale:
				self.QvtCycleaxis = self.QvtCycleaxes.axis()
			self.QvtCycleaxes.clear()
			self.QvtCycleaxes.set_title('Q v t (Current Cycle)')
			self.QvtCycleaxes.set_xlabel('Time (seconds)')
			self.QvtCycleaxes.set_ylabel('Charge (C)')
			self.QvtCycleaxes.axhline(0,c='k')
			self.QvtCycleaxes.axvline(0,c='k')
			self.QvtCycleaxes.plot(self.activeTimeList[-1-(self.m-self.startCycleIndex):]-self.activeTimeList[self.startCycleIndex], self.activeChargeCycleList[-1-(self.m-self.startCycleIndex):], linewidth=4)
			self.QvtCycleaxes.relim()
			self.QvtCycleaxes.autoscale(True)
			if not self.myQvtCycleAutoscale:
				self.QvtCycleaxes.axis(self.QvtCycleaxis)
			self.QvtCyclecanvas.draw()

		self.cycleProfileaxes.clear()
		self.cycleProfileaxes.set_title('Cycle Profile')
		self.cycleProfileaxes.set_xlabel('Time (seconds)')
		self.cycleProfileaxes.set_ylabel('Voltage (V)')
		self.cycleProfileaxes.axhline(0, c='k')
		self.cycleProfileaxes.axvline(0, c='k')
		self.cycleProfileaxes.plot([self.x0, 0, 0, self.x1, self.x1, self.x2, self.x2, self.x3, self.x3, self.x4],[0, 0, self.y0, self.y0, 0, 0 ,self.y1, self.y1, 0, 0], c='r', linewidth = 4)
		self.cycleProfileaxes.axvline(self.elapsedCycleIterations*self.timeInterval/1000, c='g')
		self.cycleProfileaxes.relim()
		self.cycleProfileaxes.set_ylim(-1.5,1.5)
		self.cycleProfilecanvas.draw()

		if self.m == 0:
			headerBool = True
		else:
			headerBool = False
		self.dataToSave = pd.DataFrame({'Time':self.activeTimeList[-1], 'Voltage (V)':self.activeVoltageList[-1], 'Current (A)':self.activeCurrentList[-1], 'Charge (C)':self.activeChargeList[-1], 'Cycle Number':self.currentLoop, 'Charge (C) (Current Cycle)':self.activeChargeCycleList[-1]}, index = pd.Index([self.m]))
		self.dataToSave.to_csv(self.saveLocationLineEdit.text(), mode='a', header=headerBool, sep = '\t')
		self.m += 1

	def closeEvent(self,event):
		mkf.shutdownKeithley(self.keithley)
		app.exit()


if __name__ == '__main__':
	app = QtWidgets.QApplication(sys.argv)
	app.aboutToQuit.connect(app.deleteLater)
	window = Window()
	sys.exit(app.exec_())