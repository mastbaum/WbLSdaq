#!/bin/env python3

import os
import sys
import time
import h5py

import numpy as np

from matplotlib.backends.qt_compat import QtCore, QtWidgets, QtGui, is_pyqt5

if is_pyqt5():
    from matplotlib.backends.backend_qt5agg import (
        FigureCanvas, NavigationToolbar2QT as NavigationToolbar)
else:
    from matplotlib.backends.backend_qt4agg import (
        FigureCanvas, NavigationToolbar2QT as NavigationToolbar)
        
class CustomNavToolbar(NavigationToolbar):
    NavigationToolbar.toolitems = (
        ('Signals','Choose signal traces to show', 'choose', 'choose'),
        ('Autoscale', 'Autoscale axes for each new event', 'autoscale','autoscale'),
        ('Home', 'Reset original view', 'home', 'home'),
        ('Back', 'Back to previous view', 'back', 'back'),
        ('Forward', 'Forward to next view', 'forward', 'forward'),
        (None, None, None, None),
        ('Pan', 'Pan axes with left mouse, zoom with right', 'move', 'pan'),
        ('Zoom', 'Zoom to rectangle', 'zoom_to_rect', 'zoom'),
        #('Subplots', 'Configure subplots', 'subplots', 'configure_subplots'),
        (None, None, None, None),
        ('Save', 'Save the figure', 'filesave', 'save_figure')
    )
    
    def __init__(self, *args, **kwargs):
        '''parent is expected to be a SignalView object'''
        super().__init__(*args, **kwargs)
        
    def choose(self):
        self.parent.select_signals()
        
    def autoscale(self):
        self.parent.fig_ax.set_autoscale_on(True)
        self.parent.plot_signals()
        
from matplotlib.figure import Figure

class SignalSelector(QtWidgets.QDialog):
    def __init__(self,fname,parent=None,selected=None,raw_adc=False):
        super().__init__(parent)
        
        self._layout = QtWidgets.QVBoxLayout(self)
        
        self.set_file(fname,selected)
        
        self.raw_checkbox = QtWidgets.QCheckBox('Plot ADC counts')
        self.raw_checkbox.setCheckState(QtCore.Qt.Checked if raw_adc else QtCore.Qt.Unchecked)
        self._layout.addWidget(self.raw_checkbox)
        
        buttons = QtWidgets.QDialogButtonBox( QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel, QtCore.Qt.Horizontal, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self._layout.addWidget(buttons)
        
    def get_raw_adc(self):
        return self.raw_checkbox.checkState() == QtCore.Qt.Checked
    
    def get_selected(self):
        selected = []
        root = self._tree.invisibleRootItem()
        it_stack = [((),root)]
        while len(it_stack) > 0:
            path,it = it_stack.pop()
            for i in range(it.childCount()):
                item = it.child(i)
                name = item.text(0)
                fullpath = path+(name,)
                if item.childCount() > 0 and item.checkState(0) != QtCore.Qt.Unchecked:
                    it_stack.append((fullpath,item))
                elif item.checkState(0) == QtCore.Qt.Checked:
                    selected.append(fullpath)
        return selected
    
    
    def add_element(self,*label,parent=None,is_leaf=False,checked=True):
        label = ' '.join(map(str,label))
        elem = QtWidgets.QTreeWidgetItem(parent)
        elem.setText(0, label)
        if is_leaf:
            elem.setFlags(elem.flags() | QtCore.Qt.ItemIsUserCheckable)
            elem.setCheckState(0, QtCore.Qt.Checked if checked else QtCore.Qt.Unchecked)
        else:
            elem.setFlags(elem.flags() | QtCore.Qt.ItemIsTristate | QtCore.Qt.ItemIsUserCheckable)
        return elem
    
    def set_file(self,path,previous_selection=None):
        self._tree = QtWidgets.QTreeWidget()
        self._tree.setHeaderLabel('Channels Shown')
        with h5py.File(path,'r') as hf:
            for dname in hf.keys():
                digitizer = hf[dname]
                dgelem = self.add_element(dname,parent=self._tree)
                for gcname in digitizer.keys():
                    grch = digitizer[gcname]
                    if 'gr' in gcname:
                        gelem = self.add_element(gcname,parent=dgelem)
                        for grdat in grch:
                            if 'ch' in grdat or 'tr' == grdat:
                                ch = grch[grdat]
                                if previous_selection:
                                    checked = (dname,gcname,grdat) in previous_selection
                                else:
                                    checked = True
                                self.add_element(grdat,parent=gelem,is_leaf=True,checked=checked)
                            else:
                                #self.add_element(grch[grdat])
                                pass
                    elif 'ch' in gcname:
                        if previous_selection:
                            checked = (dname,gcname) in previous_selection
                        else:
                            checked = True
                        self.add_element(gcname,parent=dgelem,is_leaf=True,checked=checked)
        self._layout.addWidget(self._tree)
        
class SignalView(QtWidgets.QWidget):
    def __init__(self,parent=None,figure=None):
        super().__init__(parent=parent)
        if figure is None:
            figure = Figure(tight_layout=True)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.figure = figure
        self.figure.tight_layout()
        self.fig_ax = self.figure.subplots()
        self.fig_canvas = FigureCanvas(self.figure)
        self.fig_toolbar = CustomNavToolbar(self.fig_canvas, self)
        
        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.addWidget(self.fig_toolbar)
        self.layout.addWidget(self.fig_canvas)
        self.toolbar_shown(False)
        
        self.fname = None
        self.idx = 0
        self.raw_adc = False
        #self.fig_canvas.installEventFilter(self)
        
        self.times,self.data,self.raw_data,self.selected = None,None,None,None
        
    #def eventFilter(self, obj, event):
    #    if event.type() == QtCore.QEvent.MouseButtonPress:
    #        if event.button() == QtCore.Qt.RightButton:
    #            self.select_signals()
    #    return QtCore.QObject.event(obj, event)
        
    def focusInEvent(self, *args, **kwargs):
        super().focusInEvent(*args, **kwargs)
        self.toolbar_shown(True)
        
    def focusOutEvent(self, *args, **kwargs):
        super().focusOutEvent(*args, **kwargs)
        self.toolbar_shown(False)
    
    def toolbar_shown(self,shown):
        if shown:
            self.fig_toolbar.show()
        else:
            self.fig_toolbar.hide()
            
    def _load_data(self):
        self.times = []
        self.data = []
        self.raw_data = []
        with h5py.File(self.fname,'r') as hf:
            for dgzt,*grch in self.selected:

                dgzt = hf[dgzt]
                channel = dgzt
                for part in grch:
                    channel = channel[part]
                    
                ns_per_sample = dgzt.attrs['ns_sample']
                if 'samples' in dgzt.attrs:
                    num_samples = dgzt.attrs['samples']
                else:
                    num_samples = channel.attrs['samples']
                time = np.arange(0,num_samples*ns_per_sample,ns_per_sample)
                self.times.append(time)
                
                bits = dgzt.attrs['bits'] #digitizer bit depth
                if bits == 12: #V1472
                    Vpp = 1.0
                    zero_is_zero = True
                elif bits == 14: #V1730
                    Vpp = 2.0
                    zero_is_zero = False
                else:
                    raise Exception('Not sure how to do offset correction!')
                offset = channel.attrs['offset'] #16bit DAC offset
                if not zero_is_zero: #the different models treat offset of 0 DAC differently
                    offset = 2**16 - offset
                offset = Vpp*(offset/2.0**16.0)  #now in Volts
                
                samples = channel['samples'][:] #raw ADC values
                self.raw_data.append(samples)
                samples = Vpp*(samples/2.0**bits)-offset #now in Volts
                self.data.append(samples)
        
    def select_signals(self):
        if self.fname is None:
            self.times,self.data,self.raw_data,self.selected = None,None,None,None
            return
        selector = SignalSelector(self.fname, parent=self, selected=self.selected, raw_adc=self.raw_adc)
        result = selector.exec_()
        self.selected = selector.get_selected()
        self.raw_adc = selector.get_raw_adc()
        self._load_data()
        self.plot_signals()
        
    def plot_signals(self):
        ax = self.fig_ax
        autoscale = ax.get_autoscale_on()
        if not autoscale:
            xlim = ax.get_xlim()
            ylim = ax.get_ylim()
        ax.clear()
        
        if self.selected and self.times and self.data:
        
            for t,v,n in zip(self.times,self.raw_data if self.raw_adc else self.data,self.selected):
                if self.idx < 0 or self.idx >= len(v):
                    continue
                label = os.path.join('/',*n)
                ax.plot(t,v[self.idx],linestyle='steps',label=label)
                        
        ax.set_xlabel('Sample (ns)')
        ax.set_ylabel('ADC Counts' if self.raw_adc else 'Voltage (V)')
        if not autoscale:
            ax.set_autoscale_on(False)
            ax.set_xlim(*xlim)
            ax.set_ylim(*ylim)
            
        ax.figure.canvas.draw()
        

class ApplicationWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.fname,self.idx = None,0
        
        self._main = QtWidgets.QWidget()
        self._main.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setCentralWidget(self._main)
        layout = QtWidgets.QVBoxLayout(self._main)
        
        button_layout = QtWidgets.QHBoxLayout()
        
        button = QtWidgets.QPushButton('Load Data')
        button_layout.addWidget(button)
        button.setToolTip('Load a WbLSdaq data file')
        button.clicked.connect(self.load_file)
        
        button = QtWidgets.QPushButton('Reshape')
        button_layout.addWidget(button)
        button.setToolTip('Change the plot grid shape')
        button.clicked.connect(self.reshape_prompt)
        
        layout.addLayout(button_layout)
        
        self.grid = QtWidgets.QGridLayout()
        self.views = []
        self.reshape(1,1)
        layout.addLayout(self.grid)
        
        nav_layout = QtWidgets.QHBoxLayout()
        
        button = QtWidgets.QPushButton('<<')
        nav_layout.addWidget(button)
        button.setToolTip('Previous Event')
        button.clicked.connect(self.backward)
        
        self.txtidx = QtWidgets.QLineEdit(self)
        self.txtidx.setFixedWidth(100)
        nav_layout.addWidget(self.txtidx)
        self.txtidx.returnPressed.connect(self.set_idx)
        
        button = QtWidgets.QPushButton('>>')
        nav_layout.addWidget(button)
        button.setToolTip('Next Event')
        button.clicked.connect(self.forward)
        
        layout.addLayout(nav_layout)
        
        self.txtidx.setText(str(self.idx))
        self.plot_selected()
    
    def _load_data(self):
        self.view.load_data(self.fname)
        
        
    @QtCore.pyqtSlot()
    def reshape_prompt(self):
        dialog = QtWidgets.QDialog()
        layout = QtWidgets.QFormLayout()
        layout.addRow(QtWidgets.QLabel("Choose Plot Grid Shape"))
        rowbox,colbox = QtWidgets.QLineEdit(str(self.rows)),QtWidgets.QLineEdit(str(self.cols))
        layout.addRow(QtWidgets.QLabel("Rows"),rowbox)
        layout.addRow(QtWidgets.QLabel("Cols"),colbox)
        buttons = QtWidgets.QDialogButtonBox( QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel, QtCore.Qt.Horizontal, dialog)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.setLayout(layout)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            try:
                r = int(rowbox.text())
                c = int(colbox.text())
                self.reshape(r,c)
            except:
                print('Invalid input to reshape dialog')
        
    def reshape(self,rows,cols):
        self.rows = rows
        self.cols = cols
        for i in reversed(range(self.grid.count())): 
            self.grid.itemAt(i).widget().setParent(None)
        for r in range(self.rows):
            for c in range(self.cols):
                i = c+self.cols*r
                if i < len(self.views):
                    view = self.views[i]
                else:
                    view = SignalView()
                    view.fname = self.fname
                    view.idx = self.idx
                    self.views.append(view)
                self.grid.addWidget(view,r,c)
        for widget in self.views[self.rows*self.cols:]:
            widget.deleteLater() #how necessary is this, i wonder
        self.views = self.views[:self.rows*self.cols]
    
    @QtCore.pyqtSlot()
    def backward(self):
        self.idx = self.idx - 1;
        self.txtidx.setText(str(self.idx))
        self.plot_selected()
    
    @QtCore.pyqtSlot()
    def forward(self):
        self.idx = self.idx + 1;
        self.txtidx.setText(str(self.idx))
        self.plot_selected()
        
    @QtCore.pyqtSlot()
    def set_idx(self):
        self.idx = int(self.txtidx.text())
        self.txtidx.setText(str(self.idx))
        self.plot_selected()
    
    @QtCore.pyqtSlot()
    def load_file(self):
        fname,_ = QtWidgets.QFileDialog.getOpenFileName(self, 'Open file', '.','WbLSdaq HDF5 Files (*.h5)')
        if fname:
            self.fname = fname
            for view in self.views:
                view.fname = self.fname
                view.select_signals()
        
    @QtCore.pyqtSlot()
    def plot_selected(self):
        for view in self.views:
            view.idx = self.idx
            view.plot_signals()


if __name__ == "__main__":
    qapp = QtWidgets.QApplication(sys.argv)
    app = ApplicationWindow()
    app.show()
    qapp.exec_()