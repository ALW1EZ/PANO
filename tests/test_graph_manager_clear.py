import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch


class Location:
    pass


class Event:
    pass


def _module(name, **attributes):
    module = ModuleType(name)
    module.__dict__.update(attributes)
    return module


def _load_graph_manager():
    packages = {
        name: _module(name, __path__=[])
        for name in ("ui", "ui.managers", "ui.components", "ui.dialogs")
    }
    qt_core = _module(
        "PySide6.QtCore",
        QObject=object,
        QPointF=object,
        Qt=SimpleNamespace(PenStyle=lambda value: value),
        QTimer=object,
        Signal=lambda *args: object(),
    )
    qt_gui = _module("PySide6.QtGui", QColor=object)
    stubs = {
        **packages,
        "PySide6": _module("PySide6", __path__=[]),
        "PySide6.QtCore": qt_core,
        "PySide6.QtGui": qt_gui,
        "entities": _module("entities", __path__=[], Entity=object),
        "entities.event": _module("entities.event", Event=Event),
        "entities.location": _module("entities.location", Location=Location),
        "ui.components.node_visual": _module(
            "ui.components.node_visual", NodeVisual=type("NodeVisual", (), {}),
            NodeVisualState=object,
        ),
        "ui.components.edge_visual": _module(
            "ui.components.edge_visual", EdgeVisual=type("EdgeVisual", (), {})
        ),
        "ui.components.group_visual": _module(
            "ui.components.group_visual", GroupVisual=type("GroupVisual", (), {})
        ),
        "ui.dialogs.timeline_editor": _module(
            "ui.dialogs.timeline_editor", TimelineEvent=object
        ),
        "ui.managers.map_manager": _module(
            "ui.managers.map_manager", MapManager=type("MapManager", (), {})
        ),
        "ui.managers.group_manager": _module(
            "ui.managers.group_manager", GroupManager=type("GroupManager", (), {})
        ),
    }
    path = Path(__file__).resolve().parents[1] / "ui" / "managers" / "graph_manager.py"
    spec = importlib.util.spec_from_file_location("ui.managers.graph_manager", path)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, stubs):
        spec.loader.exec_module(module)
    return module.GraphManager


class FakeTimeline:
    def __init__(self, events):
        self.events = list(events)

    def delete_event(self, event):
        self.events.remove(event)


class FakeSignal:
    def __init__(self):
        self.emitted = False

    def emit(self):
        self.emitted = True


def test_clear_removes_location_markers_and_entity_timeline_events_only():
    auto_event = SimpleNamespace(source_entity_id="event-1")
    manual_event = SimpleNamespace(name="manual")
    timeline = FakeTimeline([auto_event, manual_event])
    removed_locations = []
    removed_items = []
    location = Location()
    event = Event()
    graph_manager = SimpleNamespace(
        edges={},
        nodes={"location-1": SimpleNamespace(node=location), "event-1": SimpleNamespace(node=event)},
        groups={},
        group_manager=SimpleNamespace(groups={}),
        map_manager=SimpleNamespace(remove_location=removed_locations.append),
        view=SimpleNamespace(
            scene=SimpleNamespace(removeItem=removed_items.append),
            window=lambda: SimpleNamespace(
                timeline_manager=SimpleNamespace(
                    get_events=lambda: timeline.events,
                    timeline_widget=timeline,
                )
            ),
        ),
        nodes_changed=FakeSignal(),
    )

    _load_graph_manager().clear(graph_manager)

    assert removed_locations == ["location-1"]
    assert timeline.events == [manual_event]
    assert len(removed_items) == 2
    assert graph_manager.nodes == {}
    assert graph_manager.nodes_changed.emitted
