import http.server
import datetime
import os
import pathlib
import urllib.parse

import jinja2

from ..models import Album, Index


class GuiRequestHandler(http.server.BaseHTTPRequestHandler):
    
    server: "GuiServer"

    @property
    def location(self):
        return self.path.split("?")[0]
    
    def error(self, code: int, message: str):
        self.send_response(code)
        self.end_headers()
        self.wfile.write(message.encode("utf8"))

    def do_GET(self):
        if self.location == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            template = self.server.jinja.get_template("template.html")
            html = template.render()
            self.wfile.write(html.encode("utf8"))
        elif self.location.startswith("/media/"):
            path = self.server.root / urllib.parse.unquote(self.location[7:])
            if not path.exists():
                self.error(404, "Not Found")
                return                
            mime_type = "application/octet-stream"
            ext = path.suffix.lower()
            if ext in [".jpg", ".jpeg"]:
                mime_type = "image/jpeg"
            elif ext == ".png":
                mime_type = "image/png"
            elif ext == ".gif":
                mime_type = "image/gif"
            elif ext == ".mp4":
                mime_type = "video/mp4"                
            self.send_response(200)
            self.send_header("Content-type", mime_type)
            self.end_headers()
            with open(path, "rb") as file:
                self.wfile.write(file.read())
        elif self.location == "/favicon.ico":
            self.send_response(404)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"404 Not Found")
        else:
            raise RuntimeError(f"Invalid path {self.location}")
        
    def log_message(self, format, *args):
        pass


def filter_date(timestamp: int | float) -> str:
    dt = datetime.datetime.fromtimestamp(timestamp)
    return dt.strftime("%Y-%m-%d")


def filter_pathname(path: str) -> str:
    return pathlib.Path(path).name


def filter_datetime(timestamp: int | float) -> str:
    dt = datetime.datetime.fromtimestamp(timestamp)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def fitler_size(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    elif size < 1024 ** 2:
        return f"{size / 1024:.0f} KB"
    elif size < 1024 ** 3:
        return f"{size / 1024 ** 2:.1f} MB"
    return f"{size / 1024 ** 3:.1f} GB"


class GuiServer(http.server.HTTPServer):

    def __init__(self, host: str, root: pathlib.Path, album: Album, index: Index):
        address, port = host.split(":")
        http.server.HTTPServer.__init__(self, (address, int(port)), GuiRequestHandler)
        self.root = root
        self.album = album
        self.index = index
        self.jinja = jinja2.Environment(loader=jinja2.FileSystemLoader(os.path.dirname(__file__)))
        self.jinja.filters["date"] = filter_date
        self.jinja.filters["datetime"] = filter_datetime
        self.jinja.filters["pathname"] = filter_pathname
        self.jinja.filters["size"] = fitler_size
        self.jinja.globals.update({
            "album": self.album,
            "index": self.index
        })