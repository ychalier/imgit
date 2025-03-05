import pathlib
import webbrowser

from ..actions import load_album, load_index
from .server import GuiServer


def runserver(host: str = "127.0.0.1:8000", root: pathlib.Path = pathlib.Path(".")):
    album = load_album(root)
    index = load_index(root)
    server = GuiServer(host, root.absolute(), album, index)
    print(f"Listening to http://{host}, press ^C to stop")
    webbrowser.open(f"http://{host}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
