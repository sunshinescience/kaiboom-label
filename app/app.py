#!/usr/bin/env python3
import collections
import glob
from pathlib import Path
import sys

from PySide2 import QtCore, QtWidgets, QtGui


ClickCoords = collections.namedtuple("ClickCoords", "x_widget y_widget x_image y_image")


class MyWidget(QtWidgets.QWidget):
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
        self.image_widget = QtWidgets.QLabel(self)
        self.next_image()        

        # layout
        self.layout = QtWidgets.QVBoxLayout()
        self.layout.addWidget(self.image_widget)
        hbox = QtWidgets.QHBoxLayout()
        hbox.addWidget(self.shaft_button)
        hbox.addWidget(self.head_button)
        hbox.addWidget(self.next_button)
        self.layout.addLayout(hbox)
        self.setLayout(self.layout)

        # interactions
        self.next_button.clicked.connect(self.next_image)
        self.image_widget.mousePressEvent = self.image_click
    
    def image_click(self, event):
        x = event.pos().x()
        y = event.pos().y()
        # assumption (empiric): image placed at center vertically and left horizontally
        y_img_start = self.image_widget.height() // 2 - self.pixmap.height() // 2
        x_img_start = 0
        x_img = x - x_img_start
        y_img = y - y_img_start
        self.apply_click(ClickCoords(x, y, x_img, y_img))
    
    def apply_click(self, click_coords):
        print(click_coords)
        if self.shaft_button.isChecked():
            print(f"shaft: {click_coords}")
        elif self.head_button.isChecked():
            print(f"head: {click_coords}")
        else:
            raise NotImplementedError("New keypoint type button?")

    def next_image(self):
        self.pixmap = QtGui.QPixmap(str(next(self.image_iter)))
        self.image_widget.setPixmap(self.pixmap)
        self.shaft_button.setChecked(True)



def main():
    app = QtWidgets.QApplication([])

    img_dir = Path("/home/kaiboom/Pictures/golf")
    widget = MyWidget(img_dir)
    widget.resize(800, 600)
    widget.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
