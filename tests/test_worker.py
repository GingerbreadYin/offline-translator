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


def progress_service(connection,event):
    connection.send(None)
    job=connection.recv()[0]
    connection.send((job,{'complete':False},''))
    event.wait(10)
    connection.send((job,{'complete':True},''))
    job=connection.recv()[0]
    connection.send((job,{'complete':True},''))
    time.sleep(5)


def test_partial_result_keeps_worker_busy_until_completion():
    import multiprocessing
    event=multiprocessing.get_context('spawn').Event()
    worker=ProcessWorker(progress_service,event)
    try:
        deadline=time.monotonic()+10
        while worker.busy and time.monotonic()<deadline: worker.poll();time.sleep(.01)
        worker.submit((1,));worker.poll()
        results=[]
        while not results and time.monotonic()<deadline: results.extend(worker.poll());time.sleep(.01)
        assert results[0][1]['complete'] is False
        assert worker.busy
        worker.submit((2,));worker.poll()
        assert worker.pending==(2,)
        event.set()
        completed=[]
        while len(completed)<2 and time.monotonic()<deadline:
            completed.extend(worker.poll());time.sleep(.01)
        assert [r[0] for r in completed]==[1,2]
    finally:
        event.set();worker.close()
