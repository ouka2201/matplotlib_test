from contextlib import contextmanager
from dataclasses import dataclass
import tableauserverclient as TSC


@dataclass(frozen=True)
class TableauConfig:
    server_url: str
    username: str
    password: str
    site_name: str = ""
    api_version: str = "3.21"
    
class TableauClient:
    def __init__(self, config: TableauConfig):
        self._config = config
        self._server = TSC.Server(config.server_url)
        self._server.version = config.api_version
        self._auth = TSC.TableauAuth(
            config.username,
            config.password,
            config.site_name,
        )

    @contextmanager
    def signed_in(self):
        with self._server.auth.sign_in(self._auth):
            yield self._server
