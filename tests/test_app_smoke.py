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
        labels = [args[0] for call, args in st.calls if call == "button"]
        assert labels[-1].endswith("→"), name


def fake_saved_state(mod, monkeypatch):
    cleared = []
    for name in ("reset_approvals", "reset_flag_notes", "reset_live_choices"):
        monkeypatch.setattr(mod.data, name, lambda f, name=name: cleared.append((name, f)))
    mod.st.session_state.update({
        "defaults": {"clean": {"A0": 1.0}, "trader": {"A0": 2.0}}, "default-clean-A0": 1.0, "default-trader-A0": 2.0,
        "note-clean-X": "n", "edit-clean-Y": "1", "doc-clean": "PI-A1.pdf", "ai_message": "m",
        "page": "4 Calculate", "scenario": "trader"})
    return cleared


def test_reset_demo_clears_this_scenario_only(app, monkeypatch):
    mod, _ = app
    cleared = fake_saved_state(mod, monkeypatch)
    mod.reset_demo("clean")
    state = mod.st.session_state
    assert {f for _, f in cleared} == {"clean"} and len(cleared) == 3
    assert state["defaults"] == {"clean": {}, "trader": {"A0": 2.0}}
    assert "default-trader-A0" in state
    assert not {"default-clean-A0", "note-clean-X", "edit-clean-Y", "doc-clean", "ai_message"} & set(state)
    assert state["page"] == "Overview" and state["scenario"] == "trader"


def test_reset_all_clears_every_scenario(app, monkeypatch):
    mod, _ = app
    cleared = fake_saved_state(mod, monkeypatch)
    mod.reset_all()
    state = mod.st.session_state
    assert {f for _, f in cleared} == set(mod.data.FOLDERS) and len(cleared) == 9
    assert state["defaults"] == {"clean": {}, "problem": {}, "trader": {}}
    assert "default-trader-A0" not in state
    assert state["page"] == "Overview" and state["scenario"] == "clean"


def test_reset_menu_is_on_every_screen(app):
    mod, st = app
    for page in mod.PAGES:
        mod.st.session_state["page"] = page
        for folder in mod.data.FOLDERS:
            mod.st.session_state["scenario"] = folder
            st.calls.clear()
            mod.top_bar()
            assert ("popover", ("Reset demo",)) in st.calls


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
