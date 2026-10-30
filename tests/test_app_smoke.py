"""Import app.py with a stub streamlit module and call every page for every folder."""

import importlib
import sys
import types

import pytest


class Stub:
    """Accepts any streamlit call and returns a harmless value."""

    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        def call(*args, **kwargs):
            self.calls.append((name, args))
            if name in ("columns", "tabs"):
                n = args[0] if isinstance(args[0], int) else len(args[0])
                return [Stub() for _ in range(n)]
            if name in ("selectbox", "radio"):
                return list(args[1])[kwargs.get("index", 0)]
            if name in ("button", "checkbox", "download_button"):
                return False
            if name in ("text_input", "number_input"):
                return kwargs.get("value", "" if name == "text_input" else None)
            if name == "rerun":
                raise AssertionError("rerun should not happen without a click")
            return Stub()
        return call

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@pytest.fixture
def app(monkeypatch):
    st = Stub()
    module = types.ModuleType("streamlit")
    module.__getattr__ = st.__getattr__
    module.session_state = {}
    module.query_params = {}
    module.sidebar = Stub()
    monkeypatch.setitem(sys.modules, "streamlit", module)
    sys.modules.pop("app", None)
    mod = importlib.import_module("app")
    yield mod, st
    sys.modules.pop("app", None)


@pytest.mark.parametrize("folder", ["clean", "problem", "trader"])
def test_every_page_renders(app, folder):
    mod, st = app
    for name, page in mod.RENDER.items():
        page(folder)
    shown = " ".join(str(a) for _, args in st.calls for a in args)
    assert "Precursor status" in shown


@pytest.mark.parametrize("folder", ["clean", "problem", "trader"])
def test_every_page_ends_with_its_button(app, folder):
    mod, st = app
    for name, page in mod.RENDER.items():
        st.calls.clear()
        page(folder)
        labels = [args[0] for call, args in st.calls if call == "button" and args[0] != "Yes, reset"]
        assert labels[-1].endswith("→"), name


def test_reset_demo_clears_this_scenario_only(app, monkeypatch):
    mod, _ = app
    cleared = []
    monkeypatch.setattr(mod.data, "reset_approvals", lambda f: cleared.append(("approvals", f)))
    monkeypatch.setattr(mod.data, "reset_flag_notes", lambda f: cleared.append(("notes", f)))
    state = mod.st.session_state
    state.update({"defaults": {"clean": {"A0": 1.0}, "trader": {"A0": 2.0}}, "default-clean-A0": 1.0,
                  "default-trader-A0": 2.0, "note-clean-X": "n", "edit-clean-Y": "1"})
    mod.reset_demo("clean")
    assert cleared == [("approvals", "clean"), ("notes", "clean")]
    assert state["defaults"] == {"clean": {}, "trader": {"A0": 2.0}}
    assert set(state) == {"defaults", "default-trader-A0"}


def test_going_to_a_page_asks_to_scroll_up(app):
    mod, st = app
    mod.go("2 Trace")
    mod.scroll_up()
    assert any(name == "html" and "scrollTo" in str(args) for name, args in st.calls)
    st.calls.clear()
    mod.scroll_up()
    assert not any(name == "html" for name, _ in st.calls)


def test_main_shows_banner(app):
    mod, st = app
    mod.main()
    assert any(mod.BANNER in str(a) for name, args in st.calls if name == "html" for a in args)
    assert "SYNTHETIC" in mod.BANNER
