import time

from vagents.utils.ui import toast, toast_progress


def test_toast_instant_and_timed(monkeypatch):
    # Instant toast should not sleep
    slept = {"count": 0}

    def fake_sleep(d):
        slept["count"] += 1

    monkeypatch.setattr(time, "sleep", fake_sleep)
    toast("hello", status="info", duration=None)
    # With duration, our fake sleep should be called once
    toast("hello", status="success", duration=0.01)
    assert slept["count"] == 1


def test_toast_progress_context():
    # Ensure context manager yields an updater and allows updates
    with toast_progress("Working...") as progress:
        progress.update("step 1")
        progress.update("step 2")
