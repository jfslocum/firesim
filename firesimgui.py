import logging as log
import os.path

from PySide import QtCore, QtGui, QtDeclarative, QtDeclarative, QtOpenGL

from ui.canvaswidget import CanvasWidget
from ui.fixturewidget import FixtureWidget
from util.config import Config
from models.scene import Scene
from controllers.scenecontroller import SceneController
from controllers.netcontroller import NetController


class FireSimGUI(QtCore.QObject):

    def __init__(self, args=None):
        QtCore.QObject.__init__(self)

        self.app = QtGui.QApplication(["FireSim"])
        self.args = args
        self.config = Config("data/config.json")

        self._selected_fixture_strand = 0
        self._selected_fixture_address = 0
        self._selected_fixture_pixels = 0

        self.selected_fixture = None

        self.scene = Scene(os.path.join(self.config.get("scene_root"), self.args.scene) + ".json")
        self.scenecontroller = SceneController(app=self, scene=self.scene)

        QtDeclarative.qmlRegisterType(CanvasWidget, "FireSim", 1, 0, "SimCanvas")
        QtDeclarative.qmlRegisterType(FixtureWidget, "FireSim", 1, 0, "Fixture")

        self.view = QtDeclarative.QDeclarativeView()
        format = QtOpenGL.QGLFormat(QtOpenGL.QGL.DirectRendering)
        glwidget = QtOpenGL.QGLWidget(format)
        glwidget.setAutoFillBackground(False)
        self.view.setViewport(glwidget)
        self.view.setWindowTitle("FireSim")
        self.view.setResizeMode(QtDeclarative.QDeclarativeView.SizeRootObjectToView)

        self.view.closeEvent = self.on_close

        self.context = self.view.rootContext()
        self.context.setContextProperty('main', self)

        self.fixture_info_list = []
        self.context.setContextProperty('fixtureInfoModel', self.fixture_info_list)

        self.view.setSource(QtCore.QUrl('ui/qml/FireSimGUI.qml'))

        self.root = self.view.rootObject()
        self.item_frame = self.root.findChild(QtDeclarative.QDeclarativeItem)
        self.canvas = self.root.findChild(CanvasWidget)

        self.scenecontroller.set_canvas(self.canvas)

        cw, ch = self.scenecontroller.scene.extents()
        self.canvas.setWidth(cw)
        self.canvas.setHeight(ch)

        self.root.backdrop_showhide_callback.connect(self.on_btn_backdrop_showhide)
        self.root.labels_showhide_callback.connect(self.on_btn_labels_showhide)
        self.root.lock_callback.connect(self.on_btn_lock)
        self.root.show_center_callback.connect(self.on_btn_show_center)

        self.netcontroller = NetController(self)

        self.ups_timer = QtCore.QTimer()
        self.ups_timer.setInterval(1000)
        self.ups_timer.timeout.connect(self.update_ups)
        self.ups_timer.start()

        self.netcontroller.data_received.connect(self.on_network_event)

        self.view.setFixedSize(max(640, cw + 130), max(480, ch))

        log.info("FireSimGUI Ready.")
        self.view.show()
        #self.view.showFullScreen()
        #self.view.setGeometry(self.app.desktop().availableGeometry())


    def run(self):
        return self.app.exec_()

    def on_close(self, e):
        pass

    @QtCore.Slot()
    def update_ups(self):
        self.canvas.stat_ups = self.netcontroller.get_ups()

    @QtCore.Slot()
    def on_network_event(self):
        self.canvas.update()

    @QtCore.Slot(result=bool)
    def is_backdrop_enabled(self):
        return self.scenecontroller.scene.get("backdrop_enable", False)

    @QtCore.Slot(result=bool)
    def are_labels_enabled(self):
        return self.scenecontroller.scene.get("labels_enable", False)

    @QtCore.Slot(result=bool)
    def is_locked(self):
        return self.scenecontroller.scene.get("locked", False)

    @QtCore.Slot(result=bool)
    def is_center_shown(self):
        return self.scenecontroller.show_center

    @QtCore.Slot()
    def on_btn_add_fixture(self):
        self.scenecontroller.add_fixture()

    @QtCore.Slot()
    def on_btn_clear(self):
        self.scenecontroller.clear_fixtures()

    @QtCore.Slot()
    def on_btn_save(self):
        self.scenecontroller.save_scene()

    @QtCore.Slot(result=bool)
    def on_btn_backdrop_showhide(self, obj):
        enabled = self.scenecontroller.toggle_background_enable()
        if enabled:
            obj.setProperty("text", "Hide Backdrop")
        else:
            obj.setProperty("text", "Show Backdrop")
        return enabled

    @QtCore.Slot(result=bool)
    def on_btn_labels_showhide(self, obj):
        enabled = self.scenecontroller.toggle_labels_enable()
        if enabled:
            obj.setProperty("text", "Hide Labels")
        else:
            obj.setProperty("text", "Show Labels")
        return enabled

    @QtCore.Slot(result=bool)
    def on_btn_lock(self, obj):
        locked = self.scenecontroller.toggle_locked()
        if locked:
            obj.setProperty("text", "Unlock Scene")
        else:
            obj.setProperty("text", "Lock Scene")
        return locked

    @QtCore.Slot(result=bool)
    def on_btn_show_center(self, obj):
        show_center = self.scenecontroller.toggle_show_center()
        if show_center:
            obj.setProperty("text", "Hide Center")
        else:
            obj.setProperty("text", "Show Center")
        return show_center

    def widget_selected(self, selected, fixture, multi):
        self.selected_fixture = None

        if multi:
            pass
        else:
            if selected:
                self.selected_fixture_strand = fixture.strand()
                self.selected_fixture_address = fixture.address()
                self.selected_fixture_pixels = fixture.pixels()
            else:
                self.selected_fixture_strand = 0
                self.selected_fixture_address = 0
                self.selected_fixture_pixels = 0

        if selected:
            self.selected_fixture = fixture
            self.update_selected_fixture_properties()

    def update_selected_fixture_properties(self):
        if self.selected_fixture is not None:
            self.selected_fixture.set_strand(int(self.selected_fixture_strand))
            self.selected_fixture.set_address(int(self.selected_fixture_address))
            self.selected_fixture.set_pixels(int(self.selected_fixture_pixels))
            self.selected_fixture.get_widget().update()
            self.scenecontroller.update_scene()
            self.scenecontroller.create_pixel_array()

    def _get_selected_fixture_strand(self):
        return self._selected_fixture_strand

    def _set_selected_fixture_strand(self, strand):
        if self._selected_fixture_strand == strand:
            return
        self._selected_fixture_strand = strand
        self.update_selected_fixture_properties()
        self.on_selected_fixture_strand.emit()

    def _get_selected_fixture_address(self):
        return self._selected_fixture_address

    def _set_selected_fixture_address(self, address):
        if self._selected_fixture_address == address:
            return
        self._selected_fixture_address = address
        self.update_selected_fixture_properties()
        self.on_selected_fixture_address.emit()

    def _get_selected_fixture_pixels(self):
        return self._selected_fixture_pixels

    def _set_selected_fixture_pixels(self, pixels):
        if self._selected_fixture_pixels == pixels:
            return
        self._selected_fixture_pixels = pixels
        self.update_selected_fixture_properties()
        self.on_selected_fixture_pixels.emit()

    on_selected_fixture_strand = QtCore.Signal()
    on_selected_fixture_address = QtCore.Signal()
    on_selected_fixture_pixels = QtCore.Signal()

    selected_fixture_strand = QtCore.Property(int, _get_selected_fixture_strand, _set_selected_fixture_strand, notify=on_selected_fixture_strand)
    selected_fixture_address = QtCore.Property(int, _get_selected_fixture_address, _set_selected_fixture_address, notify=on_selected_fixture_address)
    selected_fixture_pixels = QtCore.Property(int, _get_selected_fixture_pixels, _set_selected_fixture_pixels, notify=on_selected_fixture_pixels)

