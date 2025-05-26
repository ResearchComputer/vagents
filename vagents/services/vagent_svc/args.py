from dataclasses import dataclass


@dataclass
class ServerArgs:
    host: str = "0.0.0.0"
    port: int = 8080
    server_id: str = "default"
    debug: bool = False

    # feature flags
    enable_graph_optimization: bool = True
    scheduler_policy: str = "fcfs" # fcfs
    fallback_to_eager: bool = False
    
    def translate_auto(self) -> None:
        pass


global_args: ServerArgs = ServerArgs()
