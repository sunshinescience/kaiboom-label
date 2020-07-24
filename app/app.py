#!/usr/bin/env python3
import collections
import datetime
import glob
import json
import logging
from pathlib import Path
import shutil
import sys
from typing import List
import os
import pprint

import numpy as np
from PySide2 import QtCore, QtWidgets, QtGui
import fire

kpt_alpha = 200
logger = logging.getLogger("app")
logging.basicConfig(level=logging.INFO)


KeypointPosition = collections.namedtuple("KeypointPosition", "x y")


class LabeledPerson:
    keypoint_names = [
        "nose",
        "left_shoulder",
        "right_shoulder",
        "left_elbow",
        "right_elbow",
        "left_wrist",
        "right_wrist",
        "left_hip",
        "right_hip",
        "left_knee",
        "right_knee",
        "clubhead",
        "shaftcenter",
        "ball"
    ]  # in order
    keypoints = {
        "clubhead": {"color": QtGui.QColor(255, 0, 0, kpt_alpha), "short": "CH"}, 
        "shaftcenter": {"color": QtGui.QColor(0, 0, 255, kpt_alpha), "short": "SC"}, 
        "ball": {"color": QtGui.QColor(255, 255, 255, kpt_alpha), "short": "B"}, 
        "nose": {"color": QtGui.QColor(255, 128, 0, kpt_alpha), "short": "N"}, 
        "left_shoulder": {"color": QtGui.QColor(255, 255, 0, kpt_alpha), "short": "LS"}, 
        "right_shoulder": {"color": QtGui.QColor(255, 255, 0, kpt_alpha), "short": "RS"}, 
        "left_elbow": {"color": QtGui.QColor(0, 255, 255, kpt_alpha), "short": "LE"}, 
        "right_elbow": {"color": QtGui.QColor(0, 255, 255, kpt_alpha), "short": "RE"}, 
        "left_wrist": {"color": QtGui.QColor(255, 0, 255, kpt_alpha), "short": "LW"}, 
        "right_wrist": {"color": QtGui.QColor(255, 0, 255, kpt_alpha), "short": "RW"}, 
        "left_hip": {"color": QtGui.QColor(128, 128, 128, kpt_alpha), "short": "LH"}, 
        "right_hip": {"color": QtGui.QColor(128, 128, 128, kpt_alpha), "short": "RH"}, 
        "left_knee": {"color": QtGui.QColor(0, 0, 0, kpt_alpha), "short": "LK"}, 
        "right_knee": {"color": QtGui.QColor(0, 0, 0, kpt_alpha), "short": "RK"}, 
    }
    names = list(keypoints.keys())
    assert len(names) == len(keypoint_names), f"{len(names)} vs {len(keypoints)}"

    def __init__(self, labels=None):
        self.labels = labels or {}
    
    def __len__(self):
        return len(self.labels)

    def items(self):
        return self.labels.items()
    
    def __setitem__(self, name: str, pos: KeypointPosition):
        logger.debug(f"Label name={name} set to pos={pos}.")
        assert name in self.names, name
        self.labels[name] = pos
    
    def clear(self):
        self.labels.clear()
    
    def remove(self, name: str):
        del self.labels[name]
    
    def to_json(self):
        return {n: [p.x, p.y] for n, p in self.items()}
    
    def to_arrays(self):
        """COCO style."""
        num_kpts = len(self.keypoint_names)
        v = np.zeros((num_kpts,), dtype=np.uint32)
        xy = np.zeros((num_kpts * 2,), dtype=np.uint32)
        for i, name in enumerate(self.keypoint_names):
            pos = self.labels.get(name)
            if pos is not None:
                v[i] = 2
                xy[i*2] = pos.x
                xy[i*2 + 1] = pos.y
        return v, xy
    
    @classmethod
    def from_json(cls, data):
        labels = {}
        for n, p in data.items():
            assert n in cls.keypoints.keys()
            labels[n] = KeypointPosition(*p)
        return cls(labels)


class Persons:
    def __init__(self, persons: List[LabeledPerson]=None):
        self.persons = persons
        if self.persons is None:
            self.persons = []
        self.active_person_idx = None
        if len(self) > 0:
            self.active_person_idx = 0
    
    def __len__(self):
        return len(self.persons)        

    def __iter__(self):
        return iter(self.persons)
    
    def __getitem__(self, idx):
        return self.persons[idx]
    
    def to_json(self):
        return [l.to_json() for l in self.persons]
    
    @classmethod
    def from_json(cls, data):
        persons = [LabeledPerson.from_json(d) for d in data]
        return cls(persons)

    @property
    def active_person(self):
        if self.active_person_idx is None:
            return None
        return self.persons[self.active_person_idx]
    
    def new(self) -> int:
        self.persons.append(LabeledPerson())
        self.active_person_idx = len(self) - 1
        return self.active_person_idx
    
    def delete(self, idx):
        del self.persons[idx]
        self.active_person_idx = 0
        if len(self) < 1:
            self.active_person_idx = None

class Dataset:
    def __init__(self, data=None):
        self.data = data or {}
    
    def __setitem__(self, img_fpath: str, persons: Persons):
        self.data[img_fpath] = persons
    
    def __len__(self):
        return len(self.data)
    
    def __contains__(self, fname):
        return fname in self.data
    
    def get(self, img_fpath: str):
        return self.data.get(img_fpath)
    
    def remove(self, img_fpath: str):
        del self.data[img_fpath]

    def to_json(self):
        return {i: p.to_json() for i, p in self.data.items()}
    
    @classmethod
    def from_json(cls, data):
        data = {i: Persons.from_json(p) for i, p in data.items()}
        return cls(data)


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
    def __init__(self, data_dir):
        super().__init__()

        # data
        self.data_dir = Path(data_dir)
        self.dataset_fpath = data_dir / "dataset.json"
        self.stache_dir = data_dir / "stached"
        self.stache_dir.mkdir(exist_ok=True)
        try:
            self.dataset = Dataset.from_json(json.load(self.dataset_fpath.open()))
            logger.info(f"Loaded dataset from {self.dataset_fpath} with {len(self.dataset)} labeled images at {datetime.datetime.now()}.")
        except FileNotFoundError:
            logger.info("Created new dataset.")
            self.dataset = Dataset()
        self.image_fpaths = []
        for e in ("*.png", "*.bmp", "*.JPG", "*.jpg"):
            self.image_fpaths.extend(self.data_dir.glob(e))
        self.image_fpaths = sorted(list(self.image_fpaths), key=lambda p: p.name)
        self.current_image_idx = None
        self.current_image_fpath = None

        # elements
        self.add_person_button = QtWidgets.QPushButton("+")
        self.delete_person_button = QtWidgets.QPushButton("-")
        self.pop_button = QtWidgets.QPushButton("pop")
        self.save_button = QtWidgets.QPushButton("save")
        self.clear_button = QtWidgets.QPushButton("clear")
        self.stache_button = QtWidgets.QPushButton("stache")
        self.next_button = QtWidgets.QPushButton("next")
        self.nextunlabeled_button = QtWidgets.QPushButton("next unlabeled")
        self.back_button = QtWidgets.QPushButton("back")
        self.json_button = QtWidgets.QPushButton("json")
        self.keypoint_buttons = [QtWidgets.QRadioButton(n) for n in LabeledPerson.names]
        self.person_selector = QtWidgets.QComboBox()
        self.image_selector = QtWidgets.QComboBox()
        self.image_selector.addItems([p.name for p in self.image_fpaths])
        self.image_widget = None
        self.next_image()

        # layout
        self.layout = QtWidgets.QVBoxLayout()
        self.layout.addWidget(self.image_widget)
        hbox = QtWidgets.QHBoxLayout()
        for b in self.keypoint_buttons:
            hbox.addWidget(b)
        hbox.addWidget(self.pop_button)
        hbox.addWidget(self.person_selector)
        hbox.addWidget(self.add_person_button)
        hbox.addWidget(self.delete_person_button)
        hbox.addWidget(self.back_button)
        hbox.addWidget(self.next_button)
        hbox.addWidget(self.save_button)
        self.layout.addLayout(hbox)
        aux_hbox = QtWidgets.QHBoxLayout()
        aux_hbox.addWidget(self.image_selector)
        aux_hbox.addWidget(self.nextunlabeled_button)
        aux_hbox.addWidget(self.json_button)
        aux_hbox.addWidget(self.stache_button)
        self.layout.addLayout(aux_hbox)
        self.setLayout(self.layout)

        # interactions
        self.add_person_button.clicked.connect(self.add_person)
        self.delete_person_button.clicked.connect(self.delete_person)
        self.clear_button.clicked.connect(self.clear)
        self.pop_button.clicked.connect(self.pop)
        self.next_button.clicked.connect(self.next_image)
        self.nextunlabeled_button.clicked.connect(self.nextunlabeled_image)
        self.back_button.clicked.connect(self.last_image)
        self.save_button.clicked.connect(self.save_dataset)
        self.json_button.clicked.connect(self.print_json)
        self.stache_button.clicked.connect(self.stache_img)
        self.image_selector.currentIndexChanged.connect(self.goto_image)
        self.image_widget.mousePressEvent = self.image_click
    
    def save_dataset(self):
        self.cache_current_labels()
        json.dump(self.dataset.to_json(), self.dataset_fpath.open("w"))
        logger.info(f"Saved dataset to {self.dataset_fpath} with {len(self.dataset)} labeled images at {datetime.datetime.now()}.")
    
    def select_next_kpt_button(self, i=None):
        if i is not None:
            inext = i
        else:
            inext = None
            for i, b in enumerate(self.keypoint_buttons):
                if b.isChecked():
                    inext = i + 1
                    if inext == len(self.keypoint_buttons):
                        inext = 0
        self.keypoint_buttons[inext].setChecked(True)

    def image_click(self, event):
        if self.image_widget.persons.active_person_idx is None:
            logger.error(f"No person selected.")
            return
        x = event.pos().x()
        y = event.pos().y()
        # TODO if outside of img dim return
        pos = KeypointPosition(x, y)    
        for b in self.keypoint_buttons:
            if b.isChecked():
                self.image_widget.persons.active_person[b.text()] = pos
        self.update_image_widget()
        self.select_next_kpt_button()
    
    def stache_img(self, event):
        logger.info(f"Staching image {self.current_image_fpath.name}")
        trgPath = self.stache_dir / self.current_image_fpath.name
        shutil.move(self.current_image_fpath, trgPath)
        del self.image_fpaths[self.current_image_idx]
        try:
            self.dataset.remove(self.current_image_fpath.name)
        except KeyError:
            logger.debug("No labels for stached image.")
        self.goto_image()
    
    def add_person(self, event):
        idx = self.image_widget.persons.new()
        self.refresh_person_selector()
        self.person_selector.setCurrentIndex(idx)
        self.select_next_kpt_button(0)
    
    def delete_person(self, event):
        idx = self.person_selector.currentIndex()
        logger.info(f"Deleting person {idx}")
        self.image_widget.persons.delete(idx)
        self.person_selector.setCurrentIndex(0)
        self.update_image_widget()
        self.refresh_person_selector()
    
    def clear(self):
        self.image_widget.persons.active_person.clear()
        self.update_image_widget()
        self.keypoint_buttons[0].setChecked(True)
    
    def pop(self, event):
        iprev = None
        for i, b in enumerate(self.keypoint_buttons):
            if b.isChecked():
                iprev = max(0, i - 1)
        try:
            self.image_widget.persons.active_person.remove(self.keypoint_buttons[iprev].text())
        except KeyError as e:
            logger.warning(f"Can't remove {e}")
        self.keypoint_buttons[iprev].setChecked(True)
        self.update_image_widget()
    
    def update_image_widget(self):
        self.image_widget.update()
        return  # resizing this way makes it jump to 0,0, leave it to manual
        image_rect = self.image_widget.image_rect
        self_width_min = image_rect.width() + 45
        self_height_min = image_rect.height() + 45
        self_rect = self.rect()
        self_rect.setWidth(max(self_width_min, self_rect.width()))
        self_rect.setHeight(max(self_height_min, self_rect.height()))
        self.setGeometry(self_rect)
    
    def refresh_person_selector(self):
        self.person_selector.clear()
        self.person_selector.addItems([str(i) for i in range(len(self.image_widget.persons))])
    
    def cache_current_labels(self):
        if self.current_image_fpath is not None:
            labeled_persons = [p for p in self.image_widget.persons if len(p) > 0]
            num_labeled_persons = len(labeled_persons)
            if num_labeled_persons > 0:
                image_fname = self.current_image_fpath.name
                logger.debug(f"Adding {num_labeled_persons} labeled persons for {image_fname} to cache.")
                self.dataset[image_fname] = Persons(labeled_persons)
    
    def goto_image(self, image_idx=None):
        if image_idx is None:
            image_idx = self.current_image_idx
        self.cache_current_labels()
        self.current_image_idx = image_idx
        self.current_image_fpath = self.image_fpaths[self.current_image_idx]
        persons = self.dataset.get(self.current_image_fpath.name)
        if self.image_widget is None:
            self.image_widget = LabeledImage(self.current_image_fpath, persons=persons)
        else:
            self.image_widget.new(self.current_image_fpath, persons=persons)
        if len(self.image_widget.persons) < 1:
            self.image_widget.persons.new()
        self.refresh_person_selector()
        self.update_image_widget()
        self.keypoint_buttons[0].setChecked(True)

    def jump_image(self, jump):        
        if self.current_image_idx is None:
            new_image_idx = 0
        else:
            new_image_idx = self.current_image_idx + jump
        self.goto_image(new_image_idx)        
    
    def next_image(self):
        self.jump_image(1)
    
    def last_image(self):
        if self.current_image_idx < 1 or self.current_image_idx is None:
            logger.warning(f"current_image_idx={self.current_image_idx}, nothing to go back to")
            return
        self.jump_image(-1)
    
    def nextunlabeled_image(self):
        for i in range(self.current_image_idx + 1, len(self.image_fpaths)):
            if self.image_fpaths[i].name not in self.dataset:
                self.goto_image(i)
                return
        logger.warning(f"Reached end of images, no more unlabeled ones.")
    
    def print_json(self, event):
        idx = self.person_selector.currentIndex()
        v, xy = self.image_widget.persons[idx].to_arrays()
        data = {
            "imageAssetPath": self.current_image_fpath.name,
            "annotation": {
                "v": v.tolist(),
                "xy": xy.tolist()
            }
        }
        pprint.PrettyPrinter(indent=2, width=180).pprint(data)


def main(cwd):
    app = QtWidgets.QApplication([])
    img_dir = Path(cwd)
    widget = LabelWidget(img_dir)
    widget.resize(800, 600)
    widget.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    fire.Fire(main)
