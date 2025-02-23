import dataclasses
import http.server
import json
import pathlib
import random
import webbrowser


@dataclasses.dataclass
class Credentials:
    name: str
    client_id: str
    client_secret: str
    callback: str

    @classmethod
    def from_json(cls, path: str | pathlib.Path):
        with open(path, "r", encoding="utf8") as file:
            data = json.load(file)
        return cls(**data)


@dataclasses.dataclass
class Token:
    access_token: str
    expires_in: str
    token_type: str
    refresh_token: str
    account_username: str
    account_id: str
    
    @classmethod
    def from_json(cls, path: str | pathlib.Path):
        with open(path, "r", encoding="utf8") as file:
            data = json.load(file)
        return cls(**data)
    
    def to_json(self, path: str | pathlib.Path):
        with open(path, "w", encoding="utf8") as file:
            json.dump(dataclasses.asdict(self), file, indent=4, default=str)


class AuthRequestHandler(http.server.BaseHTTPRequestHandler):
    
    HTML = b"""
    <!DOCTYPE html>
    <html>
    <head>
    <script type="text/javascript">
    const params = new URLSearchParams(window.location.hash.substring(1));
    fetch("/out?" + params.toString()).then(() => { window.close(); });
    </script>
    </head>
    </html>
    """

    @property
    def location(self):
        return self.path.split("?")[0]

    def do_GET(self):
        if self.location == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(self.HTML)
        elif self.location == "/out":
            args = map(lambda x: x.split("="), self.path.split("?")[1].split("&"))
            query = { k: v for k, v in args }
            self.server.token = Token(**query)
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"ok")
            print("Token retrieved, press Ctrl+C to close the server")
        elif self.location == "/favicon.ico":
            self.send_response(404)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"404 Not Found")
        else:
            raise RuntimeError(f"Invalid path {self.location}")
        
    def log_message(self, format, *args):
        pass


class AuthServer(http.server.HTTPServer):

    def __init__(self):
        http.server.HTTPServer.__init__(self, ("", 8000), AuthRequestHandler)
        self.token: Token | None = None


class Client:
    
    def __init__(self, credentials_path: str, token_path: str | None = None):
        self.credentials = Credentials.from_json(credentials_path)
        if token_path is None:
            self.token_path = pathlib.Path.home() / ".config" / "imgit" / "token.json"
        else:
            self.token_path = pathlib.Path(token_path)
        self._token: Token | None = None
    
    def retrieve_token(self):
        state = hash(random.random())
        auth_url = f"https://api.imgur.com/oauth2/authorize?client_id={self.credentials.client_id}&response_type=token&state={state}"
        print("Opening browser for authentication...")
        print("If the browser does not open, please open the following URL manually:")
        print(auth_url)
        webbrowser.open(auth_url)
        server = AuthServer()
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
        if server.token is None:
            raise RuntimeError("Token is None, an error must have occurred")
        self._token = server.token
        self.token_path.parent.mkdir(parents=True, exist_ok=True)
        self._token.to_json(self.token_path)
    
    @property
    def token(self) -> Token:
        if self._token is None:
            if self.token_path.exists():
                self._token = Token.from_json(self.token_path)
            else:
                self.retrieve_token()
        return self._token
