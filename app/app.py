#!/usr/bin/env python3
import collections
import glob
from pathlib import Path
import sys

from PySide2 import QtCore, QtWidgets, QtGui


class LabeledImage(QtWidgets.QWidget):
    def __init__(self, img_path):
        super().__init__()
        self.image(img_path)
    
    def image(self, img_path):
        self.pixmap = QtGui.QPixmap(str(img_path))
        self.setGeometry(self.pixmap.rect())

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)        
        painter.drawPixmap(self.rect(), self.pixmap)
        #pen = QPen(Qt.red, 3)
        #painter.setPen(pen)
        #painter.drawLine(10, 10, self.rect().width() -10 , 10)


class LabelWidget(QtWidgets.QWidget):
    def __init__(self, img_dir):
        super().__init__()

        # data
        self.image_list = img_dir.glob("*.png")
        self.image_iter = iter(self.image_list)

        # elements
        self.next_button = QtWidgets.QPushButton("next")
        self.shaft_button = QtWidgets.QRadioButton("shaft")  # center of shaft
        self.head_button = QtWidgets.QRadioButton("head")   # club head
        self.shaft_button.setChecked(True)
        self.image_widget = LabeledImage(next(self.image_iter))

        # layout
        self.layout = QtWidgets.QVBoxLayout()
        self.layout.addWidget(self.image_widget)
        hbox = QtWidgets.QHBoxLayout()
        hbox.addWidget(self.shaft_button)
        hbox.addWidget(self.head_button)
        hbox.addWidget(self.next_button)
        self.layout.addLayout(hbox)
        self.setLayout(self.layout)
        self.adjust_size()

        # interactions
        self.next_button.clicked.connect(self.next_image)
        self.image_widget.mousePressEvent = self.image_click
    
    def image_click(self, event):
        x = event.pos().x()
        y = event.pos().y()
        self.apply_click(x, y)
    
    def apply_click(self, x, y):
        xy = (x, y)
        if self.shaft_button.isChecked():
            print(f"shaft: {xy}")
        elif self.head_button.isChecked():
            print(f"head: {xy}")
        else:
            raise NotImplementedError("New keypoint type button?")
    
    def adjust_size(self):
        self.image_widget.update()
        image_rect = self.image_widget.rect()
        self_width_min = image_rect.width() * 1.1
        self_height_min = image_rect.height() * 1.1
        self_rect = self.rect()
        self_rect.setWidth(max(self_width_min, self_rect.width()))
        self_rect.setHeight(max(self_height_min, self_rect.height()))
        self.setGeometry(self_rect)

    def next_image(self):
        self.image_widget.image(next(self.image_iter))
        self.adjust_size()
        self.shaft_button.setChecked(True)


def main():
    app = QtWidgets.QApplication([])

    img_dir = Path("/home/kaiboom/Pictures/golf")
    widget = LabelWidget(img_dir)
    widget.resize(800, 600)
    widget.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
