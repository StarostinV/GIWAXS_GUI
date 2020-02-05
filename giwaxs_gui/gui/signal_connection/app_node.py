from numpy import ndarray

from .signal_container import SignalContainer
from .signal_connectors import SignalConnector

__all__ = ['AppNode']


class AppNode(object):
    @property
    def image(self):
        return self.signal_connector.image

    def __init__(self, signal_connector: SignalConnector):
        self.signal_connector = signal_connector

    def get_lower_connector(self, name: str = None):
        return self.signal_connector.get_lower_connector(name)

    def set_beam_center(self, beam_center: tuple):
        self.image.set_beam_center(beam_center)
        self.signal_connector.emit_upward(SignalContainer().geometry_changed(0))

    def set_image(self, image: ndarray):
        self.image.set_image(image)
        sc = SignalContainer(app_node=self)
        sc.image_changed(0)
        sc.geometry_changed(0)

    def add_transformation(self, name: str):
        self.image.add_transformation(name)
        sc = SignalContainer()
        sc.transformation_added(0)
        sc.geometry_changed(0)
        self.signal_connector.emit_upward(sc)

    def set_image_limits(self, limits=None):
        if self.image.intensity_limits != limits:
            self.image.set_image_limits(limits)
            SignalContainer().intensity_limits_changed(0).send(self)
