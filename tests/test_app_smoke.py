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


def test_main_shows_banner(app):
    mod, st = app
    mod.main()
    assert ("warning", (mod.BANNER,)) in st.calls
    assert "SYNTHETIC" in mod.BANNER
