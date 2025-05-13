from typing import List
import docker
import os
from vagents.utils import get_host_ip_addr, logger


class WorkerManager:
    def __init__(self):
        self._workers = {}

    async def start_worker(
        self,
        worker_id: str,
        worker_owner: str,
        worker_image: str,
        worker_args: List[str],
    ):
        ...


class DockerWorkerManager(WorkerManager):
    def __init__(self):
        super().__init__()
        self._docker = docker.from_env()

    async def start_worker(
        self,
        worker_id: str,
        worker_owner: str,
        worker_image: str,
        worker_command: List[str],
        host_port: int = None,
        bind_tmp: bool = False,
        envs: dict = None,
    ):
        if worker_id in self._workers:
            raise RuntimeError(f"Worker {worker_id} already exists")
        extra_hosts = {"host.docker.internal": get_host_ip_addr()}
        volumes = (
            {
                "/tmp": {
                    "bind": "/tmp",
                    "mode": "rw",
                },
                os.path.expanduser("~/.cache"): {
                    "bind": "/root/.cache",
                    "mode": "rw",
                },
            }
            if bind_tmp
            else {}
        )
        port_bindings = {8080: host_port} if host_port else None
        container = self._docker.containers.run(
            image=worker_image,
            command=worker_command,
            name=worker_id,
            detach=True,
            remove=True,
            extra_hosts=extra_hosts,
            ports=port_bindings,
            volumes=volumes,
            ipc_mode="host",
            environment=envs,
        )
        self._workers[worker_id] = {
            "container": container.id,
            "owner": worker_owner,
            "image": worker_image,
            "port": host_port,
            "command": worker_command,
        }

    async def stop_worker(self, worker_id: str):
        if worker_id not in self._workers:
            raise RuntimeError(f"Worker {worker_id} does not exist")
        container = self._workers[worker_id]["container"]
        self._docker.containers.get(container).stop()
        del self._workers[worker_id]
