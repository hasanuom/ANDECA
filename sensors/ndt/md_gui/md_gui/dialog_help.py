
import subprocess

from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QVBoxLayout, QLabel
from PyQt5.QtGui import *
from PyQt5.QtCore import *




class DialogHelp(QDialog):

    def __init__(self, *args, **kwargs):
        super(DialogHelp, self).__init__(*args, **kwargs)

        self.setWindowTitle("about SEMIS Metal Detector")
        self.setWindowIcon(QIcon('../resources/UoM-icon.png'))
        self.setFixedSize(400,300)

        QBtn = QDialogButtonBox.Ok

        self.buttonBox = QDialogButtonBox(QBtn)

        # connect up our buttons
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        self.label = QLabel()
        #self.label.setGeometry(QtCore.QRect(80, 400, 371, 71))
        font = QFont()
        font.setPointSize(10)
        self.label.setFont(font)
        #self.label.setStyleSheet(_fromUtf8("color:rgb(255, 85, 127)"))
        self.label.setObjectName("label")
        self.label.setText(self.dialog_text())

        self.layout = QVBoxLayout()
        self.layout.addWidget(self.label)
        self.layout.setAlignment(self.label, Qt.AlignTop)
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)


    @staticmethod
    def git_version():

        git_version = subprocess.check_output(['git', 'describe', '--always', '--tags', '--dirty', '--abbrev=4']).strip()

        #print(self.git_version)
        return git_version.decode('utf-8')

    @staticmethod
    def dialog_text():
        dialog= 'University of Manchester\n' \
                'SEMIS III Project\n\n'\
                'Version:\t' + DialogHelp.git_version()
        return dialog

    def dialog_open(self):
        pass

    def dialog_close(self):
        pass




#print(DialogHelp.git_version())
#print(DialogHelp.dialog_text())
#dialog = DialogHelp()
#dialog.exec_()