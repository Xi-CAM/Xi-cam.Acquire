from PyQt5 import QtWidgets, uic, QtGui
import sys
import os


from bluesky_widgets.qt.figures import QtFigure
from bluesky_widgets.models.plot_builders import Lines
from bluesky_widgets.models.auto_plot_builders import AutoLines

current_dir = os.path.dirname(os.path.abspath(__file__))
Form, Base = uic.loadUiType(os.path.join(current_dir, "../ui/scan_display.ui"))


class ScanDisplay(Form, Base):
    def __init__(self):
        super(Base, self).__init__() # Call the inherited classes __init__ method
        self.setupUi(self)

        self.MotorSelector1.addItem("Pinhole X")
        self.MotorSelector1.addItem("Pinhole Y")
        self.MotorSelector1.addItem("Pinhole Z")
        ###Set initial scan range values
        self.StartInput1.setText('0')
        self.StopInput1.setText('10')
        self.StepsInput1.setText('11')

        self.DetectorSelector1.addItem("Diode")

        self.model = Lines(x='motor', ys=['det'], max_runs=3)
        self.view = QtFigure(self.model.figure)

        self.dataVizWidget.setLayout(QtWidgets.QVBoxLayout())
        self.dataVizWidget.layout().addWidget(self.view)


if __name__ == '__main__':
    import sys
    app = QtWidgets.QApplication(sys.argv)
    w = ScanDisplay()
    w.show()
    sys.exit(app.exec_())

