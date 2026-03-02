from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from pyqtgraph.Qt import QtCore, QtGui
import sys
import glob
import serial
from configparser import ConfigParser


class DialogComms(QDialog):
    """Qt5 based Dialog box to configure a connection
    A callback function to create the connection is required.

    Example:
        # Create Dialog and exec()
        # Note: retval returns either QDialog::rejected == 0; QDialog::accepted == 1
        self.dialog_comms = dialog_comms.DialogComms(self.hw.create_interface)
        retval = self.dialog_comms.exec_()

        # The hw interface can then be accessed by:
        self.dialog_comms.hw_interface

        # Connection String - if object creation successful
        print("Connection:  " + self.dialog_comms.connection_str())
    """

    def __init__(self, create_connection_callback):
        super(DialogComms, self).__init__()

        self.connect_callback = create_connection_callback

        # Store the current interface instance
        self._hw_interface = None
        self._connection_str = ''

        # Settings with defaults
        self._settings_zmq = dict(host="192.168.001.005", dataport=5001, commandport=5101, stateport=5201)
        self._settings_serial = dict(comport='', baudrate=1000000)

        # configparser filename
        self._config_filename = 'connect.ini'
        self._config = ConfigParser()
        self._config_manage()

        # Create dialog
        self.setWindowTitle("Communications")
        self.setWindowIcon(QIcon('../resources/UoM-icon.png'))
        self.setFixedSize(400, 400)

        layout = QVBoxLayout()
        layout.addWidget(self._serial_settings_groupbox())
        layout.addWidget(self._zmq_settings_groupbox())
        layout.addWidget(self._dialog_buttonbox())
        self.setLayout(layout)

        # Set focus to buttonbox
        self._connect_serial_btn.setFocus()

    @property
    def hw_interface(self):
        return self._hw_interface

    def connection_str(self):
        return self._connection_str

    @staticmethod
    def serial_port_list():
        """ Lists serial port names

            :raises EnvironmentError:
                On unsupported or unknown platforms
            :returns:
                A list of the serial ports available on the system
        """
        if sys.platform.startswith('win'):
            ports = ['COM%s' % (i + 1) for i in range(256)]
        elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
            # this excludes your current terminal "/dev/tty"
            ports = glob.glob('/dev/tty[A-Za-z]*')
        elif sys.platform.startswith('darwin'):
            ports = glob.glob('/dev/tty.*')
        else:
            raise EnvironmentError('Unsupported platform')

        result = []
        for port in ports:
            try:
                s = serial.Serial(port)
                s.close()
                result.append(port)
            except (OSError, serial.SerialException):
                pass
        return result

    def _config_update_file(self):
        if self._config.read(self._config_filename):
            self._config.set('serial_connection', 'comport', self._settings_serial['comport'])
            self._config.set('serial_connection', 'baudrate', str(self._settings_serial['baudrate']))

            self._config.set('zmq_connection', 'host', str(self._settings_zmq['host']))
            self._config.set('zmq_connection', 'dataport', str(self._settings_zmq['dataport']))
            self._config.set('zmq_connection', 'commandport', str(self._settings_zmq['commandport']))
            self._config.set('zmq_connection', 'stateport', str(self._settings_zmq['stateport']))

            with open(self._config_filename, 'w') as f:
                self._config.write(f)

    def _config_manage(self):
        if not self._config.read(self._config_filename):
            # Create a new .ini file with some default values

            self._config.add_section('serial_connection')
            self._config.set('serial_connection', 'comport', self._settings_serial['comport'])
            self._config.set('serial_connection', 'baudrate', str(self._settings_serial['baudrate']))

            self._config.add_section('zmq_connection')
            self._config.set('zmq_connection', 'host', self._settings_zmq['host'])
            self._config.set('zmq_connection', 'dataport', str(self._settings_zmq['dataport']))
            self._config.set('zmq_connection', 'commandport', str(self._settings_zmq['commandport']))
            self._config.set('zmq_connection', 'stateport', str(self._settings_zmq['stateport']))

            with open(self._config_filename, 'w') as f:
                self._config.write(f)

        else:
            self._settings_serial["comport"] = self._config.get('serial_connection', 'comport')
            self._settings_serial["baudrate"] = self._config.getint('serial_connection', 'baudrate')

            self._settings_zmq["host"] = self._config.get('zmq_connection', 'host')
            self._settings_zmq["dataport"] = self._config.getint('zmq_connection', 'dataport')
            self._settings_zmq["commandport"] = self._config.getint('zmq_connection', 'commandport')
            self._settings_zmq["stateport"] = self._config.getint('zmq_connection', 'stateport')

    def _serial_settings_groupbox(self):
        serial_groupbox = QGroupBox("Serial Settings")

        comport_label = QLabel("COM port")
        baud_label = QLabel("Baudrate")

        self._baud_box = QSpinBox()
        self._baud_box.setRange(1, 10000000)
        self._baud_box.setValue(self._settings_serial["baudrate"])
        self._baud_box.valueChanged.connect(self._update_serial_settings)

        self._com_port_select = QComboBox()

        # Get current valid serial ports
        serial_ports = self.serial_port_list()

        # Add items back
        for port in serial_ports:
            self._com_port_select.addItem("{}".format(port))

        # Check to see if the current comport from the settings matches an available port
        for com in serial_ports:
            if com == self._settings_serial['comport']:
                self._com_port_select.setCurrentText(com)

        self._com_port_select.currentIndexChanged.connect(self._update_serial_settings)

        comport_refresh_btn = QPushButton()
        comport_refresh_btn.setText("Refresh")
        comport_refresh_btn.setAutoDefault(False)
        comport_refresh_btn.setDefault(False)
        comport_refresh_btn.clicked.connect(self._refresh)

        layout = QGridLayout()
        layout.setColumnStretch(0, 4)
        layout.setColumnStretch(1, 4)
        layout.addWidget(comport_label, 0, 0)
        layout.addWidget(self._com_port_select, 0, 1)
        layout.addWidget(comport_refresh_btn, 0, 2)
        layout.addWidget(baud_label, 1, 0)
        layout.addWidget(self._baud_box, 1, 1)

        serial_groupbox.setLayout(layout)

        return serial_groupbox

    def _zmq_settings_groupbox(self):
        zmq_groupbox = QGroupBox("ZMQ Settings")

        label_ip = QLabel("IP")
        label_dataport = QLabel("Data port")
        label_commsport = QLabel("Command port")
        label_stateport = QLabel("State port")
        self._ip_text = QLineEdit()
        # ip_text.setInputMask("000.000.000.000;_")
        # self._ip_text.setInputMask("000.000.000.000;0")

        ip_range = "(?:[0-1]?[0-9]?[0-9]|2[0-4][0-9]|25[0-5])"  # Part of the regular expression
        # Regular expression
        regexp = QtCore.QRegExp("^" + ip_range + "\\." + ip_range + "\\." + ip_range + "\\." + ip_range + "$")

        # Set IP Validator
        # regexp = QtCore.QRegExp(
        #   '^(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)(\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)){0,3}$')
        validator = QtGui.QRegExpValidator(regexp)
        self._ip_text.setValidator(validator)
        self._ip_text.setText(self._settings_zmq["host"])
        self._ip_text.textChanged.connect(self._update_zmq_settings)

        self._box_dataport = QSpinBox()
        self._box_commsport = QSpinBox()
        self._box_stateport = QSpinBox()

        # Set the range of values
        self._box_dataport.setRange(1, 100000)
        self._box_commsport.setRange(1, 100000)
        self._box_stateport.setRange(1, 100000)

        self._box_dataport.setValue(self._settings_zmq["dataport"])
        self._box_commsport.setValue(self._settings_zmq["commandport"])
        self._box_stateport.setValue(self._settings_zmq["stateport"])

        self._box_dataport.valueChanged.connect(self._update_zmq_settings)
        self._box_commsport.valueChanged.connect(self._update_zmq_settings)
        self._box_stateport.valueChanged.connect(self._update_zmq_settings)

        layout = QGridLayout()
        layout.setColumnStretch(0, 4)
        layout.setColumnStretch(1, 4)

        layout.addWidget(label_ip, 0, 0)
        layout.addWidget(self._ip_text, 0, 1)

        layout.addWidget(label_dataport, 1, 0)
        layout.addWidget(self._box_dataport, 1, 1)
        layout.addWidget(label_commsport, 2, 0)
        layout.addWidget(self._box_commsport, 2, 1)
        layout.addWidget(label_stateport, 3, 0)
        layout.addWidget(self._box_stateport, 3, 1)
        zmq_groupbox.setLayout(layout)

        return zmq_groupbox

    def _dialog_buttonbox(self):
        button_box = QDialogButtonBox()
        self._connect_serial_btn = button_box.addButton("Connect Serial", QDialogButtonBox.ActionRole)

        self._connect_zmq_btn = button_box.addButton("Connect ZMQ", QDialogButtonBox.ActionRole)
        self._connect_zmq_btn.setAutoDefault(True)
        self._connect_zmq_btn.setDefault(False)

        cancel_btn = button_box.addButton(QDialogButtonBox.Cancel)
        cancel_btn.setAutoDefault(False)
        cancel_btn.setDefault(False)

        self._connect_serial_btn.setAutoDefault(True)
        self._connect_serial_btn.setDefault(True)


        # disconnect the clicked signal from the slots QDialogBox automatically sets
        self._connect_serial_btn.clicked.disconnect()
        self._connect_zmq_btn.clicked.disconnect()

        # Connect the new clicked signal to a slot
        self._connect_serial_btn.clicked.connect(self._connect_serial)
        self._connect_zmq_btn.clicked.connect(self._connect_zmq)

        # connect up our buttons
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        self._connect_serial_btn.setFocus()
        button_box.setFocus()

        return button_box

    def _connect_serial(self):
        self._config_update_file()

        self._hw_interface = self.connect_callback("serial",
                                                   comport=self._settings_serial["comport"],
                                                   baudrate=self._settings_serial["baudrate"])
        self._connection_str = f'Serial, {self._settings_serial["comport"]:s}, ' \
                               f'{self._settings_serial["baudrate"]:,} Baud'
        self.accept()

    def _connect_zmq(self):
        self._config_update_file()

        self._hw_interface = self.connect_callback("zmq",
                                                   host=self._settings_zmq['host'],
                                                   dataport=self._settings_zmq["dataport"],
                                                   commandport=self._settings_zmq["commandport"],
                                                   stateport=self._settings_zmq["stateport"])

        self._connection_str = f'ZMQ, Host: {self._settings_zmq["host"]:s}, ' \
                               f'Dataport: {self._settings_zmq["dataport"]:d}, ' \
                               f'Commandport: {self._settings_zmq["commandport"]:d}, ' \
                               f'Stateport: {self._settings_zmq["stateport"]:d}'
        self.accept()

    def _update_serial_settings(self):
        self._settings_serial["baudrate"] = self._baud_box.value()
        self._settings_serial["comport"] = self._com_port_select.currentText()
        self._connect_serial_btn.setFocus()
        #print(self._settings_serial)

    def _update_zmq_settings(self):
        self._settings_zmq["host"] = self._ip_text.text()
        self._settings_zmq["dataport"] = self._box_dataport.value()
        self._settings_zmq["commandport"] = self._box_commsport.value()
        self._settings_zmq["stateport"] = self._box_stateport.value()
        self._connect_zmq_btn.setFocus()
        # print(self._settings_zmq)

    def _refresh(self):
        # Get current valid serial ports
        serial_ports = self.serial_port_list()

        # clear() removes all items from a combobox
        self._com_port_select.clear()

        # Add items back
        for port in serial_ports:
            self._com_port_select.addItem("{}".format(port))

        self._connect_serial_btn.setFocus()


#
#
#

if __name__ == '__main__':

    def dummy_callback(connection, *argv, **kwargs):

        print("connection is {}".format(connection))

        for arg in argv:
            print(arg)

        for key, value in kwargs.items():
            print("%s:\t%s" % (key, value))


    app = QApplication(sys.argv)

    dialog = DialogComms(dummy_callback)
    dialog.exec_()

    # Quit the app
    app.quit()
