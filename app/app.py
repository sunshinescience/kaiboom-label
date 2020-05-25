#!/usr/bin/env python3
import collections
import glob
import logging
from pathlib import Path
import sys

from PySide2 import QtCore, QtWidgets, QtGui

logger = logging.getLogger("app")
logging.basicConfig(level=logging.INFO)

KeypointPosition = collections.namedtuple("KeypointPosition", "x y")


class Labels:
    keypoints = {
        "clubhead": {"color": QtGui.QColor(255, 0, 0, 127), "short": "CH"}, 
        "shaftcenter": {"color": QtGui.QColor(0, 0, 255, 127), "short": "SC"}, 
    }
    names = list(keypoints.keys())

    def __init__(self):
        self.labels = {}
    
    def __len__(self):
        return len(self.labels)

    def items(self):
        return self.labels.items()
    
    def __setitem__(self, name, pos):
        logger.info(f"Label name={name} set to pos={pos}.")
        assert name in self.names, name
        self.labels[name] = pos
    
    def clear(self):
        self.labels.clear()
    
    def to_json(self):
        return {n: [p.x, p.y] for n, p in self.items()}


class LabeledImage(QtWidgets.QWidget):
    def __init__(self, img_path):
        super().__init__()
        self.pen = QtGui.QPen()
        self.pen.setWidth(3)
        self.r = 10
        self.new(img_path)
    
    def new(self, img_path):
        self.pixmap = QtGui.QPixmap(str(img_path))
        self.setGeometry(self.image_rect)
        self.labels = Labels()
        
    @property
    def image_rect(self):
        return self.pixmap.rect()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)        
        painter.drawPixmap(self.rect(), self.pixmap)
        
        for n, p in self.labels.items():
            self.pen.setColor(self.labels.keypoints[n]["color"])
            painter.setPen(self.pen)
            point = QtCore.QPoint(*p)
            painter.drawEllipse(point, self.r, self.r)
            painter.drawText(point, self.labels.keypoints[n]["short"])


class LabelWidget(QtWidgets.QWidget):
    def __init__(self, img_dir):
        super().__init__()

        # data
        self.labels = {}
        self.image_list = img_dir.glob("*.png")
        self.image_iter = iter(self.image_list)
        self.current_image_path = None

        # elements
        self.clear_button = QtWidgets.QPushButton("clear")
        self.next_button = QtWidgets.QPushButton("next")
        self.keypoint_buttons = [QtWidgets.QRadioButton(n) for n in Labels.names]
        self.image_widget = None
        self.next_image()

        # layout
        self.layout = QtWidgets.QVBoxLayout()
        self.layout.addWidget(self.image_widget)
        hbox = QtWidgets.QHBoxLayout()
        for b in self.keypoint_buttons:
            hbox.addWidget(b)
        hbox.addWidget(self.next_button)
        hbox.addWidget(self.clear_button)
        self.layout.addLayout(hbox)
        self.setLayout(self.layout)

        # interactions
        self.clear_button.clicked.connect(self.clear)
        self.next_button.clicked.connect(self.next_image)
        self.image_widget.mousePressEvent = self.image_click
    
    def select_next_kpt_button(self):
        inext = None
        for i, b in enumerate(self.keypoint_buttons):
            if b.isChecked():
                inext = i + 1
                if inext == len(self.keypoint_buttons):
                    inext = 0
        self.keypoint_buttons[inext].setChecked(True)

    def image_click(self, event):
        x = event.pos().x()
        y = event.pos().y()
        pos = KeypointPosition(x, y)    
        for b in self.keypoint_buttons:
            if b.isChecked():
                self.image_widget.labels[b.text()] = pos
        self.update_image_widget()
        self.select_next_kpt_button()
    
    def clear(self):
        self.image_widget.labels.clear()
        self.update_image_widget()
        self.keypoint_buttons[0].setChecked(True)
    
    def update_image_widget(self):
        self.image_widget.update()
        image_rect = self.image_widget.image_rect
        self_width_min = image_rect.width() + 45
        self_height_min = image_rect.height() + 45
        self_rect = self.rect()
        self_rect.setWidth(max(self_width_min, self_rect.width()))
        self_rect.setHeight(max(self_height_min, self_rect.height()))
        self.setGeometry(self_rect)

    def next_image(self):
        if self.current_image_path is not None:
            num_labels = len(self.image_widget.labels)
            if num_labels > 0:
                logger.info(f"Adding {num_labels} labels for {self.current_image_path} to cache.")
                self.labels[self.current_image_path] = self.image_widget.labels
        self.current_image_path = next(self.image_iter)
        if self.image_widget is None:
            self.image_widget = LabeledImage(self.current_image_path)
        else:
            self.image_widget.new(self.current_image_path)
        self.update_image_widget()
        self.keypoint_buttons[0].setChecked(True)


def main():
    app = QtWidgets.QApplication([])
    img_dir = Path("/home/kaiboom/Pictures/golf")
    widget = LabelWidget(img_dir)
    widget.resize(800, 600)
    widget.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
