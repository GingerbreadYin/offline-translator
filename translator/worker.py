"""A warm, terminable inference process with one replaceable pending request."""
import multiprocessing


def inference_loop(connection, resources):
    from PIL import Image
    from .services import Pipeline
    pipeline = Pipeline(resources)
    connection.send(None)
    while True:
        try:
            job, size, pixels = connection.recv()
        except EOFError:
            return
        image = Image.frombytes("RGB", size, pixels)
        del pixels
        try:
            connection.send((job, pipeline.run(image), ""))
        except Exception as exc:
            connection.send((job, None, str(exc)))
        finally:
            image.close()


class ProcessWorker:
    def __init__(self, target=inference_loop, config=None):
        context = multiprocessing.get_context("spawn")
        self.connection, child = context.Pipe()
        self.process = context.Process(target=target, args=(child, config), daemon=True)
        self.busy = True
        self.pending = None
        self.closed = False
        self.process.start()
        child.close()

    @property
    def alive(self):
        return not self.closed and self.process.is_alive()

    def submit(self, request):
        if self.closed:
            raise RuntimeError("Inference worker is closed")
        self.pending = request

    def cancel_pending(self):
        self.pending = None

    def poll(self):
        results = []
        if self.closed:
            return results
        while self.connection.poll():
            try:
                result = self.connection.recv()
            except (EOFError, OSError):
                raise RuntimeError("离线引擎意外退出，请重启软件")
            self.busy = False
            if result is not None:
                results.append(result)
        if not self.process.is_alive():
            raise RuntimeError("离线引擎意外退出，请重启软件")
        if not self.busy and self.pending is not None:
            request, self.pending = self.pending, None
            self.connection.send(request)
            self.busy = True
        return results

    def close(self):
        if self.closed:
            return
        self.pending = None
        self.process.terminate()
        self.process.join(timeout=2)
        if self.process.is_alive():
            self.process.kill()
            self.process.join(timeout=2)
        self.connection.close()
        self.process.close()
        self.closed = True
