
from PyQt5.QtWidgets import *
from PyQt5 import QtCore
from PyQt5.QtCore import Qt


class TransmitTableView(object):
    def __init__(self, data: dict, max_number_of_frequencies:  int):

        self.tableview_widget = QTableView()
        self.tableview_widget.setAlternatingRowColors(True)

        self._max_number_of_frequencies = max_number_of_frequencies
   
        self.model = TransmitTableModel(data)
        self.tableview_widget.setModel(self.model)

    def update_view(self, harmonic_dict : dict):
        # TODO: this is closely coupled to the tx-config harmonic dict !
        for key in harmonic_dict:
            if key == "enable":
                col = 0
            elif key == "freq":
                col = 1
            elif key == 'magnitude':
                col = 2
            elif key == 'phase':
                col = 3
            elif key == 'scale':
                break
            else:
                col = 4

            for row in range(self._max_number_of_frequencies):
                m_idx = self.model.index(row, col)
                val = harmonic_dict[key][row]
                self.model.setData(m_idx, val)


class TransmitTableModel(QtCore.QAbstractTableModel):

    def __init__(self, data):
        super(TransmitTableModel, self).__init__()
        self._data = data

        self.keys = list(self._data.keys())
        #print(self.keys)

        self.horizontal_label = ["Enable", "Freq(int)", "Magnitude", "Phase(rads)"]

    # def data(self, index, role):

    #     if role == Qt.DisplayRole:
    #         if index.row == 1:
    #             return self._data[index.row()][index.column()]

    #         else:
    #             # See below for the nested-list data structure.
    #             # .row() indexes into the outer list,
    #             # .column() indexes into the sub-list
    #             return self._data[index.row()][index.column()]


    def data(self, index, role=Qt.DisplayRole):

        checkbox_col = self.horizontal_label.index("Enable")
        #print(checkbox_col)
        if not index.isValid():
            return None

        if index.column() == self.horizontal_label.index("Enable"):
            value = ''
        elif index.column() == self.horizontal_label.index("Freq(int)"):
            value = QtCore.QVariant("%d" % self._data["freq"][index.row()])
        elif index.column() == self.horizontal_label.index( "Magnitude"):
            value = QtCore.QVariant("%.3f" % self._data["magnitude"][index.row()])
        elif index.column() == self.horizontal_label.index("Phase(rads)"):
            value = QtCore.QVariant("%.3f" % self._data["phase"][index.row()])
        else:
            value = ''

        if role == QtCore.Qt.EditRole:
            return value
        elif role == QtCore.Qt.DisplayRole:
            return value
        elif role == QtCore.Qt.CheckStateRole:
            if index.column() == self.horizontal_label.index("Enable"):
                #if self.test[index.row()]:
                if self._data["enable"][index.row()]:
                    return QtCore.Qt.Checked
                else:
                    return QtCore.Qt.Unchecked
        elif role == Qt.TextAlignmentRole:
            return Qt.AlignCenter

        return QtCore.QVariant()

    def setData(self, index, value, role=Qt.EditRole):
        if not index.isValid():
            return False

        if role == Qt.CheckStateRole and index.column() == self.horizontal_label.index("Enable"):
            if value == Qt.Checked:
                self._data["enable"][index.row()] = True
            else:
                self._data["enable"][index.row()] = False
            #self.setHeaderIcon()

        elif role == Qt.EditRole and index.column() != self.horizontal_label.index("Enable"):
            row = index.row()
            col = index.column()

            #if value.isdigit():

            if index.column() == self.horizontal_label.index("Freq(int)"):
                self._data["freq"][index.row()] = int(value)

            elif index.column() == self.horizontal_label.index( "Magnitude"):
                self._data["magnitude"][index.row()] = float(value)

            elif index.column() ==  self.horizontal_label.index("Phase(rads)"):
                self._data["phase"][index.row()] = float(value)

        self.dataChanged.emit(index, index, [Qt.EditRole])
        return True



    # def toggleCheckState(self, index):
    #     if index == self.horizontal_label.index( alhtou"Enable"):
    #         # if numpy.all(self.test == False):
    #         #     self.test.fill(True)
    #         # else:
    #         #     self.test.fill(False)
            
    #         topLeft = self.index(0, 3)
    #         bottomRight = self.index(self.rowCount(), 3)
    #         self.dataChanged.emit(topLeft, bottomRight)
    #         #self.setHeaderIcon()

    def rowCount(self, index):
        # The length of the outer list.
        # return len(self._data)
        return len(self._data["freq"])

    def columnCount(self, index):
        # The following takes the first sub-list, and returns
        # the length (only works if all rows are an equal length)
        #return len(self._data[0])
        return len(self.keys) -1 # subtract 1 for the scale

    def headerData(self, section, orientation, role):
        row_label = list(range(0, 16))

        if role == QtCore.Qt.DisplayRole:

            if orientation == QtCore.Qt.Horizontal:
                return self.horizontal_label[section]
            if orientation == QtCore.Qt.Vertical:
                return row_label[section]


    def flags(self, index):
        if not index.isValid():
            return None

        if index.column() == self.horizontal_label.index("Enable"):
            return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsUserCheckable
        else:
            return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable

    # def headerData(self):
    #     self.setHeaderData(0 , Qt.Horizontal, tr("hello"))
