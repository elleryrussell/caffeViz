# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'displaycontrolwidget.ui'
#
# Created: Fri Jul 31 20:18:43 2015
#      by: PyQt4 UI code generator 4.10.4
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class Ui_displayControlWidget(object):
    def setupUi(self, displayControlWidget):
        displayControlWidget.setObjectName(_fromUtf8("displayControlWidget"))
        displayControlWidget.resize(290, 56)
        self.formLayout = QtGui.QFormLayout(displayControlWidget)
        self.formLayout.setObjectName(_fromUtf8("formLayout"))
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.previousBtn = QtGui.QPushButton(displayControlWidget)
        self.previousBtn.setObjectName(_fromUtf8("previousBtn"))
        self.horizontalLayout.addWidget(self.previousBtn)
        self.updateBtn = QtGui.QPushButton(displayControlWidget)
        self.updateBtn.setObjectName(_fromUtf8("updateBtn"))
        self.horizontalLayout.addWidget(self.updateBtn)
        self.nextBtn = QtGui.QPushButton(displayControlWidget)
        self.nextBtn.setObjectName(_fromUtf8("nextBtn"))
        self.horizontalLayout.addWidget(self.nextBtn)
        self.formLayout.setLayout(0, QtGui.QFormLayout.LabelRole, self.horizontalLayout)

        self.retranslateUi(displayControlWidget)
        QtCore.QMetaObject.connectSlotsByName(displayControlWidget)

    def retranslateUi(self, displayControlWidget):
        displayControlWidget.setWindowTitle(_translate("displayControlWidget", "Form", None))
        self.previousBtn.setText(_translate("displayControlWidget", "Previous", None))
        self.updateBtn.setText(_translate("displayControlWidget", "Update", None))
        self.nextBtn.setText(_translate("displayControlWidget", "Next", None))

