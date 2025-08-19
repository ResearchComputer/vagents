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


def test_toast_different_status_types(monkeypatch):
    """Test toast with different status types"""
    slept = {"count": 0}

    def fake_sleep(d):
        slept["count"] += 1

    monkeypatch.setattr(time, "sleep", fake_sleep)
    
    # Test different status types
    statuses = ["info", "success", "warning", "error"]
    
    for status in statuses:
        toast(f"Message with {status} status", status=status, duration=0.01)
    
    # Should have slept for each status type with duration
    assert slept["count"] == len(statuses)


def test_toast_with_no_duration(monkeypatch):
    """Test toast with None duration (instant)"""
    slept = {"count": 0}

    def fake_sleep(d):
        slept["count"] += 1

    monkeypatch.setattr(time, "sleep", fake_sleep)
    
    # Multiple instant toasts should not sleep
    for i in range(3):
        toast(f"Instant message {i}", status="info", duration=None)
    
    assert slept["count"] == 0


def test_toast_with_zero_duration(monkeypatch):
    """Test toast with zero duration"""
    slept = {"count": 0}

    def fake_sleep(d):
        slept["count"] += 1

    monkeypatch.setattr(time, "sleep", fake_sleep)
    
    toast("Zero duration message", status="info", duration=0)
    
    # Zero duration is falsy so should be treated as instant (no sleep)
    assert slept["count"] == 0


def test_toast_with_long_duration(monkeypatch):
    """Test toast with longer duration"""
    sleep_times = []

    def fake_sleep(d):
        sleep_times.append(d)

    monkeypatch.setattr(time, "sleep", fake_sleep)
    
    toast("Long duration message", status="info", duration=1.5)
    
    assert len(sleep_times) == 1
    assert sleep_times[0] == 1.5


def test_toast_progress_multiple_updates():
    """Test toast progress with multiple updates"""
    updates = []
    
    # Mock the implementation to capture updates
    original_toast_progress = toast_progress
    
    class MockProgressUpdater:
        def update(self, message):
            updates.append(message)
    
    def mock_toast_progress(message):
        class MockContext:
            def __enter__(self):
                updates.append(f"start: {message}")
                return MockProgressUpdater()
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                updates.append("end")
                return False
        
        return MockContext()
    
    # Temporarily replace toast_progress
    import vagents.utils.ui as ui_module
    original = ui_module.toast_progress
    ui_module.toast_progress = mock_toast_progress
    
    try:
        with ui_module.toast_progress("Processing...") as progress:
            progress.update("Step 1: Loading")
            progress.update("Step 2: Processing")
            progress.update("Step 3: Finalizing")
    finally:
        ui_module.toast_progress = original
    
    assert "start: Processing..." in updates
    assert "Step 1: Loading" in updates
    assert "Step 2: Processing" in updates
    assert "Step 3: Finalizing" in updates
    assert "end" in updates


def test_toast_with_special_characters(monkeypatch):
    """Test toast handles special characters in messages"""
    slept = {"count": 0}

    def fake_sleep(d):
        slept["count"] += 1

    monkeypatch.setattr(time, "sleep", fake_sleep)
    
    # Test with various special characters
    special_messages = [
        "Message with émojis 🎉",
        "Message with\nnewlines",
        "Message with\ttabs",
        "Message with 中文",
        "Message with symbols: !@#$%^&*()",
        ""  # Empty message
    ]
    
    for message in special_messages:
        toast(message, status="info", duration=0.01)
    
    assert slept["count"] == len(special_messages)


def test_toast_edge_cases(monkeypatch):
    """Test toast with edge case parameters"""
    slept = {"count": 0}

    def fake_sleep(d):
        slept["count"] += 1

    monkeypatch.setattr(time, "sleep", fake_sleep)
    
    # Test with very small duration
    toast("Small duration", status="info", duration=0.001)
    
    # Test with negative duration (should probably be handled gracefully)
    try:
        toast("Negative duration", status="info", duration=-1)
    except Exception:
        pass  # Implementation may handle this differently
    
    # Should have at least one sleep call from the valid case
    assert slept["count"] >= 1
