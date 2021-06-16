from typing import Iterable
from pyqtgraph import parametertree as pt
from qtpy.QtWidgets import QDialog, QHBoxLayout, QVBoxLayout, QDialogButtonBox, QPushButton
from qtpy.QtCore import Qt, QSettings
from xicam.core import msg


class ScalableGroup(pt.parameterTypes.GroupParameter):
    def __init__(self, **opts):
        opts['type'] = 'group'
        opts['addText'] = "Add"
        opts['addList'] = ['str', 'float', 'int']
        pt.parameterTypes.GroupParameter.__init__(self, **opts)

    def addNew(self, typ):
        val = {
            'str': '',
            'float': 0.0,
            'int': 0
        }[typ]
        self.addChild(
            dict(name="New Field %d" % (len(self.childs) + 1), type=typ, value=val, removable=True, renamable=True))


class MetadataDialog(QDialog):
    """Dialog for calibrating images.

    User can select from a list of catalogs (pulled from the active ensemble),
    preview, and calibrate the image data.
    """

    default_parameters_dict = [{'title': 'Sample Name',
                                'name': 'sample_name',
                                'type': 'str',
                                'renamable': False,
                                'removable': False,
                                }]

    _default_parameter_state = ScalableGroup(children=default_parameters_dict,
                                             name='blah',
                                             type='group').saveState()

    _qsettings_key = 'xicam.Acquire.metadata.v1'
    _parameter_state = QSettings().value(_qsettings_key, defaultValue=_default_parameter_state)
    parameter = ScalableGroup(name='blah')
    parameter.restoreState(_parameter_state)

    def __init__(self, reserved: Iterable[str] = None, parent=None, window_flags=Qt.WindowFlags()):
        super(MetadataDialog, self).__init__(parent, window_flags)

        self.reserved = set(reserved or [])

        self.parameter_tree = pt.ParameterTree(showHeader=False)
        self.parameter_tree.setParameters(self.parameter, showTop=False)

        calibrate_button = QPushButton("&Acquire")

        self.buttons = QDialogButtonBox(Qt.Horizontal)
        # Add calibration button that accepts the dialog (closes with 1 status)
        self.buttons.addButton(calibrate_button, QDialogButtonBox.AcceptRole)
        # Add a cancel button that will reject the dialog (closes with 0 status)
        self.buttons.addButton(QDialogButtonBox.Cancel)

        self.buttons.rejected.connect(self.reject)
        self.buttons.accepted.connect(self.accept)

        outer_layout = QVBoxLayout()
        outer_layout.addWidget(self.parameter_tree)
        outer_layout.addWidget(self.buttons)
        outer_layout.setSpacing(0)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(outer_layout)

    def get_metadata(self):
        return {key: value['value'] for key, value in self.parameter.saveState('user')['children'].items()}

    def accept(self):
        intersection = set(self.get_metadata().keys()).intersection(self.reserved)

        if intersection:
            msg.notifyMessage(f'The field name "{list(intersection)[0]}" is reserved and cannot be used.')
        else:
            super(MetadataDialog, self).accept()
            QSettings().setValue(self._qsettings_key, self.parameter.saveState())


#
# if not active_catalogs:
#     raise RuntimeError("There are no catalogs in the active ensemble "
#                        f'"{active_ensemble.data(Qt.DisplayRole)}". '
#                        "Unable to calibrate.")
#
# dialog = CalibrationDialog(active_catalogs)
# accepted = dialog.exec_()
#
# # Only calibrate if the dialog was accepted via the calibrate button
# if not accepted == QDialog.Accepted:
#     return
#
# catalog = dialog.get_catalog()

if __name__ == "__main__":
    from qtpy.QtWidgets import QApplication

    qapp = QApplication([])

    mdd = MetadataDialog()
    mdd.show()

    qapp.exec_()
