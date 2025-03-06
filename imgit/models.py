import dataclasses
import os


IMGIT_FOLDER = ".imgit"
IGNORE_NAME = ".imgitignore"
NON_ANIMATED_IMAGES = [".jpg", ".jpeg", ".png", ".tiff"]
VIDEOS = [".mp4", ".mpeg", ".avi", ".webm"]
ANIMATED_IMAGES = VIDEOS + [".gif", ".apng"]
ACCEPTED_EXTENSIONS = NON_ANIMATED_IMAGES + ANIMATED_IMAGES
NON_ANIMATED_SIZE_LIMIT = 20 * 1024 * 1024 # bytes
ANIMATED_SIZE_LIMIT = 200 * 1024 * 1024 # bytes
VIDEO_DURATION_LIMIT = 60 # seconds


class ImgurError(Exception):
    pass


class QuotaError(ImgurError):
    pass


class ImgitError(Exception):
    pass


@dataclasses.dataclass
class Album:
    id: str
    delete_hash: str
    title: str
    description: str
    datetime: int
    link: str


@dataclasses.dataclass
class Image:
    path: str
    remote_id: str | None
    remote_datetime: int | None
    remote_size: int | None
    remote_delete_hash: str | None
    remote_link: str | None
    local_size: int | None
    local_ctime: float | None
    local_mtime: float | None
    local_md5: str | None
    
    @property
    def online(self) -> bool:
        return self.remote_id is not None
    
    @property
    def offline(self) -> bool:
        return self.local_size is not None
    
    @property
    def animated(self) -> bool:
        return os.path.splitext(self.path)[1].lower() in ANIMATED_IMAGES
    
    @property
    def video(self) -> bool:
        return os.path.splitext(self.path)[1].lower() in VIDEOS


class Index(dict[str, Image]):

    def add(self, image: Image):
        self[image.path] = image
        
    @classmethod
    def from_list(cls, images: list[Image]):
        index = cls()
        for image in images:
            index.add(image)
        return index