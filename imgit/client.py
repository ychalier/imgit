import dataclasses
import http.server
import pathlib
import random
import time
import webbrowser

import requests

from . import models
from . import utils


@dataclasses.dataclass
class Credentials:
    name: str
    client_id: str
    client_secret: str
    callback: str


@dataclasses.dataclass
class Token:
    access_token: str
    expires_in: str
    token_type: str
    refresh_token: str
    account_username: str
    account_id: str


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
    
    def __init__(self,
            credentials_path: str,
            token_path: str | None = None,
            delay: float = 1):
        self.credentials = utils.read_dataclass(Credentials, credentials_path)
        if token_path is None:
            self.token_path = pathlib.Path.home() / ".config" / "imgit" / "token.json"
        else:
            self.token_path = pathlib.Path(token_path)
        self.delay = delay
        self._last_request: int = 0
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
        utils.write_dataclass(self._token, self.token_path)
    
    @property
    def token(self) -> Token:
        if self._token is None:
            if self.token_path.exists():
                self._token = utils.read_dataclass(Token, self.token_path)
            else:
                self.retrieve_token()
        return self._token
    
    def request(self,
            method: str,
            url: str,
            data: dict | None = None,
            files: dict | None = None,
            json_data: dict | None = None) -> dict:
        headers = {"Authorization": f"Bearer {self.token.access_token}"}
        now = time.time()
        if now - self._last_request < self.delay:
            time.sleep(self.delay - (now - self._last_request))
        self._last_request = now
        if method.lower() == "get":
            response = requests.get(url, headers=headers)
        elif method.lower() == "post":
            response = requests.post(url, headers=headers, data=data, files=files, json=json_data)
        elif method.lower() == "delete":
            response = requests.delete(url, headers=headers)
        else:
            raise ValueError(f"Unknown method {method}")
        try:
            data = response.json()
        except Exception as err:
            raise RuntimeError(f"Wrong response (status code {response.status_code}) for {method} {url}") from err
        if "errors" in data:
            error = data["errors"][0]
            if error["code"] == 429:
                user_reset = float(response.headers.get("X-RateLimit-UserReset", 0))
                raise models.QuotaError(f"Reached API quota, try again in {utils.format_duration(user_reset)}")
            raise models.ImgurError(f"Error: {error['code']} {error['status']}: {error['detail']}")
        if not "success" in data or not data["success"] or "data" not in data:
            raise models.ImgurError(f"Error: Illegal response '{data}'")
        return data["data"]

    def download(self, url: str, path: str | pathlib.Path):
        now = time.time()
        if now - self._last_request < self.delay:
            time.sleep(self.delay - (now - self._last_request))
        self._last_request = now
        headers = {"User-Agent": "Mozilla/5.0 (Linux; Android 6.0; MYA-L22 Build/HUAWEIMYA-L22) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.84 Mobile Safari/537.36"}
        response = requests.get(url, headers=headers)
        if not response.status_code == 200:
            raise models.ImgurError(f"Error: Got status {response.status_code} when downloading file")
        with open(path, "wb") as file:
            file.write(response.content)
        
    def get_album(self, album_id: str) -> models.Album:
        data = self.request("get", f"https://api.imgur.com/3/album/{album_id}")
        return models.Album(
            id=data["id"],
            delete_hash=data["deletehash"],
            title=data["title"],
            description=data["description"],
            datetime=data["datetime"],
            link=data["link"]
        )
    
    def create_album(self, album_title: str) -> models.Album:
        data = self.request("post", "https://api.imgur.com/3/album", json_data={
            "title": album_title,
            "description": ""
        })
        album_id = data["id"]
        return self.get_album(album_id)

    def get_album_images(self, album_id: str) -> models.Index:
        data = self.request("get", f"https://api.imgur.com/3/album/{album_id}/images")
        index = models.Index()
        if data is None:
            return index
        for d in data:
            description = d["description"]
            if description is None or description.strip() == "":
                utils.printc(f"Warning: image at {d['link']} has no description, skipping", "yellow")
                continue
            index.add(models.Image(
                path=description,
                remote_id=d["id"],
                remote_datetime=d["datetime"],
                remote_size=d["size"],
                remote_delete_hash=d["deletehash"],
                remote_link=d["link"],
                local_size=None,
                local_ctime=None,
                local_mtime=None,
                local_md5=None
            ))
        return index
    
    def upload_image(self, album_id: str, image: models.Image, path: pathlib.Path) -> models.Image:
            with open(path, "rb") as file:
                d = self.request(
                    "post",
                    "https://api.imgur.com/3/upload",
                    data={
                        "type": "file",
                        "name": path.name,
                        "title": image.path,
                        "description": image.path,
                        "album": album_id
                    },
                    files={
                        "image": file
                    })
            return models.Image(
                path=image.path,
                remote_id=d["id"],
                remote_datetime=d["datetime"],
                remote_size=d["size"],
                remote_delete_hash=d["deletehash"],
                remote_link=d["link"],
                local_size=None,
                local_ctime=None,
                local_mtime=None,
                local_md5=None
            )
    
    def delete_image(self, image_id: str):
        self.request("delete", f"https://api.imgur.com/3/image/{image_id}")
        
    def update_image_information(self, image_id: str, title_and_description: str):
        self.request("post", f"https://api.imgur.com/3/image/{image_id}", json_data={
            "title": title_and_description,
            "description": title_and_description
        })