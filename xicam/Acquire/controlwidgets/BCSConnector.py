from qtpy.QtWidgets import *


class BCSConnector(QStackedWidget):
    def __init__(self):
        super(BCSConnector, self).__init__()
        self.addWidget(Connector())
        self.addWidget(Connecting())
        self.addWidget(Connected())
        self.addWidget(ConnectionLost())
        self.setCurrentIndex(0)

    def connect(self):
        pass


class Connector(QWidget):
    def __init__(self):
        super(Connector, self).__init__()
        layout = QFormLayout()
        layout.addRow("Address:", QLineEdit())
        layout.addRow("Port:", QLineEdit())
        layout.addRow('', QPushButton('Connect'))

        self.setLayout(layout)


class Connecting(QWidget):
    def __init__(self):
        super(Connecting, self).__init__()
        vbox = QVBoxLayout()
        vbox.addWidget(QLabel('Connecting...'))


class Connected(QWidget):
    def __init__(self):
        super(Connected, self).__init__()
        vbox = QVBoxLayout()
        vbox.addWidget(QLabel('Connected!'))


class ConnectionLost(QWidget):
    def __init__(self):
        super(ConnectionLost, self).__init__()
        vbox = QVBoxLayout()
        vbox.addWidget(QLabel('Connection Lost.\nReconnecting...'))
