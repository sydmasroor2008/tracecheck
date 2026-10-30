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


def test_review_state_lives_in_the_session_and_never_in_a_file(app, monkeypatch):
    mod, _ = app
    monkeypatch.setattr(mod.data, "write_json", lambda *a: pytest.fail("review state written to a file"))
    field = next(f for f in mod.load("clean")["fields"] if not f["approved"])
    start = sum(f["approved"] for f in mod.load("clean")["fields"])
    mod.approve("clean", field["key"], field["value"])
    mod.demo("clean")["notes"]["X:1"] = "note"
    mod.set_live_doc("clean", "GI-03.jpg", True)
    assert sum(f["approved"] for f in mod.load("clean")["fields"]) == start + 1
    assert mod.demo("trader")["approvals"] == {}
    mod.st.session_state.clear()      # what a reload or a new tab gives
    assert sum(f["approved"] for f in mod.load("clean")["fields"]) == start




def test_hidden_reset_clears_the_session_and_the_parameter(app, monkeypatch):
    mod, _ = app

    class Rerun(Exception):
        pass

    def rerun():
        raise Rerun
    monkeypatch.setattr(mod.st, "rerun", rerun, raising=False)
    mod.st.session_state.update({"page": "4 Calculate", "demo": {"clean": {"approvals": {"k": {}}}}})
    mod.st.query_params.update({"reset": "1", "scenario": "trader"})
    with pytest.raises(Rerun):
        mod.hidden_reset()
    assert mod.st.session_state == {}
    assert mod.st.query_params == {"scenario": "trader"}


def test_no_reset_buttons_in_the_top_bar(app):
    mod, st = app
    mod.top_bar()
    assert not any("Reset" in str(args) for _, args in st.calls)


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
