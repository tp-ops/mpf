"""BCP module."""
import asyncio
from functools import partial
from typing import List

from mpf.core.events import QueuedEvent
from mpf.core.mpf_controller import MpfController

from mpf.core.bcp.bcp_server import BcpServer
from mpf.core.utility_functions import Util

from mpf.core.bcp.bcp_interface import BcpInterface
from mpf.core.bcp.bcp_transport import BcpTransportManager

MYPY = False
if MYPY:   # pragma: no cover
    from mpf.core.machine import MachineController  # pylint: disable-msg=cyclic-import,unused-import


class Bcp(MpfController):

    """BCP Module."""

    config_name = "bcp"

    __slots__ = ["interface", "transport", "servers", "enabled"]

    def __init__(self, machine: "MachineController") -> None:
        """initialize BCP module."""
        super().__init__(machine)
        self.interface = BcpInterface(machine)
        self.transport = BcpTransportManager(machine)
        self.servers = []       # type: List[BcpServer]

        if self.machine.options['bcp']:
            self.enabled = True
            self.machine.events.add_handler('init_phase_2',
                                            self._setup_bcp_connections)
        else:
            self.enabled = False

        self.machine.events.add_handler('init_phase_4',
                                        self._setup_bcp_servers)

        self.machine.events.add_handler('shutdown',
                                        self._stop_servers)

    def send(self, bcp_command, **kwargs):
        """Emulate legacy send.

        Args:
        ----
            bcp_command: Commmand to send
        """
        self.transport.send_to_all_clients(bcp_command, **kwargs)

    def _setup_bcp_connections(self, queue: QueuedEvent, **kwargs):
        """Connect to BCP servers from MPF config."""
        del kwargs
        if 'connections' not in self.machine.config['bcp'] or not self.machine.config['bcp']['connections'] or self.machine.config['bcp']['connections'] == 'None':
            return

        client_connect_futures = []
        for name, settings in self.machine.config['bcp']['connections'].items():
            self.machine.events.post('bcp_connection_attempt',
                                     name=name,
                                     host=settings['host'],
                                     port=settings['port'])
            '''event: bcp_connection_attempt
            desc: MPF is attempting to make a BCP connection.
            args:
            name: The name of the connection.
            host: The host name MPF is attempting to connect to.
            port: The TCP port MPF is attempting to connect to'''

            client = Util.string_to_class(settings['type'])(self.machine, name, self.machine.bcp)
            client.exit_on_close = settings['exit_on_close']
            connect_future = asyncio.ensure_future(client.connect(settings))
            connect_future.add_done_callback(partial(self.transport.register_transport, client))
            client_connect_futures.append(connect_future)

        # block init until all clients are connected
        if client_connect_futures:
            queue.wait()
            future = asyncio.ensure_future(asyncio.wait(iter(client_connect_futures)))
            future.add_done_callback(lambda x: queue.clear())
            future.add_done_callback(self._bcp_clients_connected)

    def _bcp_clients_connected(self, *args):
        del args
        self.machine.events.post('bcp_clients_connected')
        '''event: bcp_clients_connected
        desc: All BCP outgoing BCP connections have been made.'''

    def _setup_bcp_servers(self, queue: QueuedEvent, **kwargs):
        """Start BCP servers to allow other clients to connect."""
        del kwargs
        if 'servers' not in self.machine.config['bcp'] or not self.machine.config['bcp']['servers']:
            return

        servers_start_futures = []
        for settings in self.machine.config['bcp']['servers'].values():
            server = BcpServer(self.machine, settings['ip'], settings['port'], settings['type'])
            server_future = asyncio.ensure_future(server.start())
            server_future.add_done_callback(lambda x, s=server: self.servers.append(s))     # type: ignore
            servers_start_futures.append(server_future)

        # block init until all servers were started
        if servers_start_futures:
            queue.wait()
            future = asyncio.ensure_future(asyncio.wait(iter(servers_start_futures)))
            future.add_done_callback(lambda x: queue.clear())

    def _stop_servers(self, **kwargs):
        """Stop BCP servers."""
        del kwargs
        for server in self.servers:
            server.stop()
