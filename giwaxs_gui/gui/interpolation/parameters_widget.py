from PyQt5.QtWidgets import (QLabel, QComboBox, QHBoxLayout)
from PyQt5.QtCore import Qt

from ..basic_widgets import (BasicInputParametersWidget,
                             AbstractInputParametersWidget)
from .modes import INTERPOLATION_MODES
from ...config import read_config
from ..basic_widgets import InfoButton


def get_interpolation_parameters(get_default_parameters: bool = False):
    return read_config(InterpolateSetupWindow.NAME, get_default_parameters)


class InterpolateSetupWindow(BasicInputParametersWidget):
    P = BasicInputParametersWidget.InputParameters

    # TODO: add info to interpolation parameters

    PARAMETER_TYPES = (P('r_size', 'Radius axis size', int),
                       P('phi_size', 'Angle axis size', int),
                       P('mode', 'Interpolation algorithm', str))

    NAME = 'Interpolation parameters'

    def _get_layout(self,
                    input_parameter: BasicInputParametersWidget.InputParameters):
        if input_parameter.name == 'mode':
            return self._get_mode_layout(input_parameter)
        else:
            return super()._get_layout(input_parameter)

    def _get_mode_layout(self, input_parameter: BasicInputParametersWidget.InputParameters):

        current_value = self.default_dict.get(input_parameter.name, None)
        if current_value is None:
            current_value = INTERPOLATION_MODES[0].name
        label_widget = QLabel(input_parameter.label)
        input_widget = QComboBox()
        input_widget.setEditable(False)
        input_widget.addItems([m.name for m in INTERPOLATION_MODES])
        input_widget.setCurrentText(current_value)
        layout = QHBoxLayout()
        layout.addWidget(label_widget, Qt.AlignHCenter)
        layout.addWidget(input_widget, Qt.AlignHCenter)
        if input_parameter.info:
            info_button = InfoButton(input_parameter.info)
            layout.addWidget(info_button, Qt.AlignLeft)

        def get_input(*args):
            return input_widget.currentText()

        setattr(AbstractInputParametersWidget, input_parameter.name, property(get_input))
        return layout



