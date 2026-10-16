import time
from translator.worker import ProcessWorker


def hanging_service(connection, config):
    connection.send(None)
    connection.recv()
    time.sleep(60)


def test_exit_terminates_hung_inference_process_and_releases_queue():
    worker = ProcessWorker(hanging_service, None)
    deadline = time.monotonic() + 10
    while worker.busy and time.monotonic() < deadline:
        worker.poll()
        time.sleep(0.02)
    assert not worker.busy
    worker.submit((1, b"image"))
    worker.poll()
    assert worker.busy
    worker.submit((2, b"old"))
    worker.submit((3, b"latest"))
    assert worker.pending == (3, b"latest")
    started = time.monotonic()
    worker.close()
    assert time.monotonic() - started < 5
    assert not worker.alive
    assert worker.pending is None
