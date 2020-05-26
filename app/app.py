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


class LabeledPerson:
    keypoints = {
        "clubhead": {"color": QtGui.QColor(255, 0, 0, 127), "short": "CH"}, 
        "shaftcenter": {"color": QtGui.QColor(0, 0, 255, 127), "short": "SC"}, 
        "ball": {"color": QtGui.QColor(255, 255, 255, 127), "short": "B"}, 
        "nose": {"color": QtGui.QColor(255, 128, 0, 127), "short": "N"}, 
        "left_shoulder": {"color": QtGui.QColor(255, 255, 0, 127), "short": "LS"}, 
        "right_shoulder": {"color": QtGui.QColor(255, 255, 0, 127), "short": "RS"}, 
        "left_elbow": {"color": QtGui.QColor(0, 255, 255, 127), "short": "LE"}, 
        "right_elbow": {"color": QtGui.QColor(0, 255, 255, 127), "short": "RE"}, 
        "left_wrist": {"color": QtGui.QColor(255, 0, 255, 127), "short": "LW"}, 
        "right_wrist": {"color": QtGui.QColor(255, 0, 255, 127), "short": "RW"}, 
        "left_hip": {"color": QtGui.QColor(128, 128, 128, 127), "short": "LH"}, 
        "right_hip": {"color": QtGui.QColor(128, 128, 128, 127), "short": "RH"}, 
        "left_knee": {"color": QtGui.QColor(0, 0, 0, 127), "short": "LK"}, 
        "right_knee": {"color": QtGui.QColor(0, 0, 0, 127), "short": "RK"}, 
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


class Persons:
    def __init__(self, labels=None):
        self.labels = labels
        if self.labels is None:
            self.labels = []
        self.active_person_idx = None
        if len(self) > 0:
            self.active_person_idx = 0
    
    def __len__(self):
        return len(self.labels)        

    def __iter__(self):
        return iter(self.labels)
    
    def __getitem__(self, idx):
        return self.labels[idx]

    @property
    def active_person(self):
        if self.active_person_idx is None:
            return None
        return self.labels[self.active_person_idx]
    
    def new(self):
        self.labels.append(LabeledPerson())
        self.active_person_idx = len(self) - 1


class LabeledImage(QtWidgets.QWidget):
    def __init__(self, img_path, persons=None):
        super().__init__()
        self.pen = QtGui.QPen()
        self.pen.setWidth(3)
        self.r = 10
        self.new(img_path, persons)
    
    def new(self, img_path, persons=None):
        self.pixmap = QtGui.QPixmap(str(img_path))
        self.setGeometry(self.image_rect)
        self.persons = persons
        if self.persons is None:
            self.persons = Persons()
        
    @property
    def image_rect(self):
        return self.pixmap.rect()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)        
        painter.drawPixmap(self.rect(), self.pixmap)
        
        for i, person in enumerate(self.persons):
            for n, p in person.items():
                self.pen.setColor(person.keypoints[n]["color"])
                painter.setPen(self.pen)
                point = QtCore.QPoint(*p)
                painter.drawEllipse(point, self.r, self.r)
                point.setX(point.x() + self.r)
                point.setY(point.y() + self.r // 2)
                painter.drawText(point, person.keypoints[n]["short"] + f"-{i}")


class LabelWidget(QtWidgets.QWidget):
    def __init__(self, img_dir):
        super().__init__()

        # data
        self.labels = {}
        self.image_fpaths = list(img_dir.glob("*.png"))
        self.current_image_idx = None
        self.current_image_fpath = None

        # elements
        self.clear_button = QtWidgets.QPushButton("clear")
        self.next_button = QtWidgets.QPushButton("next")
        self.back_button = QtWidgets.QPushButton("back")
        self.keypoint_buttons = [QtWidgets.QRadioButton(n) for n in LabeledPerson.names]
        self.person_selector = QtWidgets.QComboBox()
        self.image_widget = None
        self.next_image()

        # layout
        self.layout = QtWidgets.QVBoxLayout()
        self.layout.addWidget(self.image_widget)
        hbox = QtWidgets.QHBoxLayout()
        for b in self.keypoint_buttons:
            hbox.addWidget(b)
        hbox.addWidget(self.person_selector)
        hbox.addWidget(self.back_button)
        hbox.addWidget(self.next_button)
        hbox.addWidget(self.clear_button)
        self.layout.addLayout(hbox)
        self.setLayout(self.layout)

        # interactions
        self.clear_button.clicked.connect(self.clear)
        self.next_button.clicked.connect(self.next_image)
        self.back_button.clicked.connect(self.last_image)
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
                self.image_widget.persons.active_person[b.text()] = pos
        self.update_image_widget()
        self.select_next_kpt_button()
    
    def clear(self):
        self.image_widget.persons.active_person.clear()
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

    def jump_image(self, jump):
        if self.current_image_fpath is not None:
            labeled_persons = [p for p in self.image_widget.persons if len(p) > 0]
            num_labeled_persons = len(labeled_persons)
            if num_labeled_persons > 0:
                logger.info(f"Adding {num_labeled_persons} labeled persons for {self.current_image_fpath} to cache.")
                self.labels[self.current_image_fpath] = Persons(labeled_persons)
        if self.current_image_idx is None:
            self.current_image_idx = 0
        else:
            self.current_image_idx += jump
        self.current_image_fpath = self.image_fpaths[self.current_image_idx]
        persons = self.labels.get(self.current_image_fpath)
        if self.image_widget is None:
            self.image_widget = LabeledImage(self.current_image_fpath, persons=persons)
        else:
            self.image_widget.new(self.current_image_fpath, persons=persons)
        if len(self.image_widget.persons) < 1:
            self.image_widget.persons.new()
        self.person_selector.clear()
        self.person_selector.addItems([str(i) for i in range(len(self.image_widget.persons))])
        self.update_image_widget()
        self.keypoint_buttons[0].setChecked(True)
    
    def next_image(self):
        self.jump_image(1)
    
    def last_image(self):
        if self.current_image_idx < 1 or self.current_image_idx is None:
            logger.warning(f"current_image_idx={self.current_image_idx}, nothing to go back to")
            return
        self.jump_image(-1)


def main():
    app = QtWidgets.QApplication([])
    img_dir = Path("/home/kaiboom/Pictures/golf")
    widget = LabelWidget(img_dir)
    widget.resize(800, 600)
    widget.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
