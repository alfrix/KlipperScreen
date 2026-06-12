import http.client
import json as json_module
import logging
import os
import re
import socket

import requests


class KlippyRest:
    def __init__(self, ip, port=7125, api_key=False, path="", ssl=None):
        self.ip = ip
        self.port = port
        self.path = f"/{path}" if path else ""
        self.ssl = ssl
        self.api_key = api_key
        self.ssl = int(self.port) in {443, 7130} if ssl is None else bool(ssl)
        self.status = ""
        self.uds_path = self._resolve_uds_path(ip)
        self._use_unix_socket = False
        self._uds_sock_path = None
        self.session = requests.Session()
        if self.uds_path:
            self._init_unix_socket(self.uds_path)

    @staticmethod
    def _resolve_uds_path(host):
        """Detect if host is a Unix socket path or resolve to default socket."""
        default_socket = os.path.expanduser("~/printer_data/comms/moonraker.sock")
        if not host or not host.strip():
            return default_socket
        host = host.strip()
        if host.startswith("/"):
            return host
        if host in ("127.0.0.1", "localhost", "::1"):
            return default_socket
        return None

    def _init_unix_socket(self, socket_path):
        """Try to initialize Unix socket connection."""
        if not os.path.exists(socket_path):
            logging.warning("Unix socket %s not found, using TCP for REST", socket_path)
            return
        if self._try_unix_socket(socket_path):
            return
        if self._try_manual_unix_socket(socket_path):
            return
        logging.warning("Unix socket init failed for %s, using TCP for REST", socket_path)

    def _try_unix_socket(self, socket_path):
        """Try to mount a requests-unixsocket adapter on the given path."""
        # Try requests-unixsocket2 first (the '2' variant)
        try:
            import requests_unixsocket.mod_requests as mod_requests

            adapter = mod_requests.UnixSocketAdapter(socket_path)
            self.session.mount("unix://", adapter)
            self._use_unix_socket = True
            self._uds_sock_path = socket_path
            logging.debug(f"Using Unix socket for REST: {socket_path}")
            return True
        except ImportError:
            pass
        # Fall back to original requests-unixsocket
        try:
            import requests_unixsocket

            adapter = requests_unixsocket.UnixSocketAdapter(socket_path)
            self.session.mount("unix://", adapter)
            self._use_unix_socket = True
            self._uds_sock_path = socket_path
            logging.debug(f"Using Unix socket for REST: {socket_path}")
            return True
        except ImportError:
            pass
        except AttributeError:
            pass
        return False

    def _try_manual_unix_socket(self, socket_path):
        """Use http.client directly over a Unix socket as a universal fallback."""
        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.connect(socket_path)
            self._uds_sock = sock
            self._uds_sock_path = socket_path
            self._use_unix_socket = True
            logging.debug(f"Using manual Unix socket for REST: {socket_path}")
            return True
        except (FileNotFoundError, ConnectionRefusedError, PermissionError) as e:
            logging.debug(f"Manual Unix socket failed for {socket_path}: {e}")
            return False

    @property
    def endpoint(self):
        if self._use_unix_socket and self._uds_sock_path:
            return f"unix://{self._uds_sock_path}"
        return f"{'https' if self.ssl else 'http'}://{self.ip}:{self.port}{self.path}"

    @staticmethod
    def process_response(response):
        return response["result"] if response and "result" in response else response

    def get_thumbnail_stream(self, thumbnail):
        return self.send_request(f"server/files/gcodes/{thumbnail}", json=False)

    def _do_request(
        self, method, request_method, data=None, json=None, json_response=True, timeout=3
    ):
        url = f"{self.endpoint}/{method}"
        headers = {"x-api-key": self.api_key} if self.api_key else {}
        if hasattr(self, "_uds_sock"):
            try:
                return self._do_unix_request(
                    method, request_method, data, json, json_response, headers, timeout
                )
            except Exception as e:
                self.status = self.format_status(e)
                logging.error(self.status.replace("\n", ">>"))
                return False
        try:
            response = self.session.request(
                request_method.upper(), url, json=json, data=data, headers=headers, timeout=timeout
            )
            response.raise_for_status()
            self.status = ""
            return response.json() if json_response else response.content
        except Exception as e:
            self.status = self.format_status(e)
            logging.error(self.status.replace("\n", ">>"))
            return False

    def _do_unix_request(self, method, request_method, data, json, json_response, headers, timeout):
        """Send a request using http.client over a Unix socket."""
        path = f"/{method}" if not method.startswith("/") else method
        if json is not None:
            body = json_module.dumps(json).encode("utf-8")
        elif data is not None:
            if isinstance(data, dict):
                body = json_module.dumps(data).encode("utf-8")
            else:
                body = data
        else:
            body = b""

        http_conn = http.client.HTTPConnection(
            "localhost", timeout=timeout, unix_socket=self._uds_sock
        )
        http_conn.request(request_method.upper(), path, body=body, headers=headers)
        response = http_conn.getresponse()
        resp_body = response.read()
        http_conn.close()

        if response.status >= 400:
            raise requests.exceptions.HTTPError(f"HTTP {response.status}")
        self.status = ""
        if json_response:
            return json_module.loads(resp_body)
        return resp_body

    def post_request(self, method, data=None, json=None, json_response=True):
        return self._do_request(method, "post", data, json, json_response)

    def send_request(self, method, json=True, timeout=4):
        res = self._do_request(method, "get", json_response=json, timeout=timeout)
        return self.process_response(res) if json else res

    @staticmethod
    def format_status(status):
        try:
            rep = {
                "HTTPConnectionPool": "",
                "/server/info ": "",
                "Caused by ": "",
                "(": "",
                ")": "",
                ": ": "\n",
                "'": "",
                "`": "",
                '"': "",
            }
            rep = {re.escape(k): v for k, v in rep.items()}
            pattern = re.compile("|".join(rep.keys()))
            status = pattern.sub(lambda m: rep[re.escape(m.group(0))], f"{status}").split("\n")
            return "\n".join(_ for _ in status if "urllib3" not in _ and _ != "")
        except TypeError or KeyError:
            return status
