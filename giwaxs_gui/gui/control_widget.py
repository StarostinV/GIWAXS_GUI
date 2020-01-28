import logging

from PyQt5.QtWidgets import (QWidget, QHBoxLayout,
                             QTreeView, QLabel)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QStandardItem, QStandardItemModel

from .basic_widgets import (RoundedPushButton,
                            DeleteButton)
from .roi.roi_widgets import RingParametersWidget, RingSegmentParametersWidget
from .roi.roi_containers import BasicROIContainer
from .signal_connection import (SignalConnector,
                                SignalContainer)
from ..utils import Icon, RoiParameters

logger = logging.getLogger(__name__)


class ControlWidget(BasicROIContainer, QTreeView):
    _DEFAULT_RING_PARAMETERS = dict(radius=10, width=1,
                                    angle=180, angle_std=360,
                                    type=RoiParameters.roi_types.ring)
    _DEFAULT_ARC_PARAMETERS = dict(radius=10, width=1,
                                   angle=180, angle_std=180,
                                   type=RoiParameters.roi_types.segment)

    _RADIUS_RANGE = (0, 2000)
    _WIDTH_RANGE = (0, 1000)

    def __init__(self, signal_connector: SignalConnector, parent=None):
        BasicROIContainer.__init__(self, signal_connector)
        QTreeView.__init__(self, parent)
        self._model = QStandardItemModel()
        self._model.setHorizontalHeaderLabels([''])
        self._model.setRowCount(0)
        self.setModel(self._model)
        self.selectionModel().currentChanged.connect(self.on_clicked)

        # self.clicked.connect(self.on_clicked)
        self.__init_ui__()
        self.show()

    def __init_ui__(self):
        self.add_ring_button = RoundedPushButton(
            text='Add', icon=Icon('add'), radius=30)
        self.add_ring_button.clicked.connect(self.emit_create_ring)
        self.delete_all_rings_button = DeleteButton(text='Delete all rings?')
        self.delete_all_rings_button.clicked.connect(self.emit_delete_all_rings)

        self.add_arc_button = RoundedPushButton(
            text='Add', icon=Icon('add'), radius=30)
        self.add_arc_button.clicked.connect(self.emit_create_arc)
        self.delete_all_arcs_button = DeleteButton(text='Delete all segments?')
        self.delete_all_arcs_button.clicked.connect(self.emit_delete_all_arcs)

        self.ring_item = QStandardItem()
        ring_layout = self._get_header_layout(self.ring_item, 'Rings')
        ring_layout.addWidget(self.add_ring_button, alignment=Qt.AlignRight)
        ring_layout.addWidget(self.delete_all_rings_button, alignment=Qt.AlignRight)

        self.arc_item = QStandardItem()
        arc_layout = self._get_header_layout(self.arc_item, 'Ring Segments')
        arc_layout.addWidget(self.add_arc_button, alignment=Qt.AlignRight)
        arc_layout.addWidget(self.delete_all_arcs_button, alignment=Qt.AlignRight)

        self.setGeometry(500, 500, 500, 500)
        self.setColumnWidth(0, 250)
        self.header().resizeSection(0, 100)

    def _get_header_layout(self, item: QStandardItem, label: str):
        header_widget = QWidget(self)
        layout = QHBoxLayout()
        header_widget.setLayout(layout)
        label_widget = QLabel(label)
        layout.addWidget(label_widget, alignment=Qt.AlignLeft)
        layout.addStretch(1)
        self._model.appendRow(item)
        self.setIndexWidget(item.index(), header_widget)
        return layout

    def on_clicked(self, index):
        item = self._model.itemFromIndex(index)
        key = item.data()
        if key is not None:
            selected_roi = self.roi_dict[key]
            selected_roi.send_active()

    def emit_create_ring(self, *args):
        params = RoiParameters(**self._DEFAULT_RING_PARAMETERS,
                               name=f'ring {self.ring_item.rowCount()}')
        self.__class__.emit_create_segment(self, params)

    def emit_create_arc(self, *args):
        params = RoiParameters(**self._DEFAULT_ARC_PARAMETERS,
                               name=f'ring segment {self.arc_item.rowCount()}')
        self.__class__.emit_create_segment(self, params)

    def emit_delete_all_of_type(self, roi_type: int):
        sc = SignalContainer()
        for roi in self.roi_dict.values():
            if roi.parameters.type == roi_type:
                sc.segment_deleted(roi)
        self.signal_connector.emit_upward(sc)

    def emit_delete_all_rings(self):
        return self.emit_delete_all_of_type(RoiParameters.roi_types.ring)

    def emit_delete_all_arcs(self):
        return self.emit_delete_all_of_type(RoiParameters.roi_types.segment)

    def _get_roi(self, params: RoiParameters):
        new_ring_item = QStandardItem()
        new_ring_item.setData(params.key)

        if params.type == RoiParameters.roi_types.ring:
            new_roi = RingParametersWidget(
                new_ring_item, self, params, self._RADIUS_RANGE, self._WIDTH_RANGE)
            self.ring_item.appendRow(new_ring_item)
        elif params.type == RoiParameters.roi_types.segment:
            new_roi = RingSegmentParametersWidget(
                new_ring_item, self, params, self._RADIUS_RANGE, self._WIDTH_RANGE)
            self.arc_item.appendRow(new_ring_item)
        self._model.layoutChanged.emit()
        return new_roi

    def _add_item(self, roi: RingParametersWidget):
        self.setIndexWidget(roi.item.index(), roi)
        self.setExpanded(roi.item.parent().index(), True)
        roi.deleteClicked.connect(self.emit_delete_segment)

    def _remove_item(self, roi: RingParametersWidget):
        ring_item = roi.item
        roi.item.parent().removeRow(ring_item.row())
        self._model.layoutChanged.emit()

    def on_type_changed(self, value: RoiParameters):
        self.delete_roi(self.roi_dict[value.key])
        self.add_roi(value)
