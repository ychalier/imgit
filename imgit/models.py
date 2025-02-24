import dataclasses


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


class Index(dict[str, Image]):

    def add(self, image: Image):
        self[image.path] = image
        
    @classmethod
    def from_list(cls, images: list[Image]):
        index = cls()
        for image in images:
            index.add(image)
        return index