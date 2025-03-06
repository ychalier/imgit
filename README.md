# imgit

Synchronize local folders with [Imgur](https://imgur.com/) albums.

## Getting Started

### Prerequisites

You'll need a working installation of [Python 3](https://www.python.org/).

### Installation

1. Download the [latest release](https://github.com/ychalier/imgit/releases)
2. Install it with `pip`:
   ```console
   pip install ~/Downloads/imgit-0.1.0.tar.gz
   ```

### Credentials

Create an Imgur app (follow [instructions here](https://apidocs.imgur.com/#authorization-and-oauth)) and create a `credentials.json` file with the following fields:

```json
{
   "name": "You App Name",
   "client_id": "Your Client ID",
   "client_secret": "Your Client Secret",
   "callback": "http://localhost:8000"
}
```

### Usage

Here is a basic usage scenario: create an empty folder `My Album` and place images in it (subfolders are supported). To automatically create an Imgur album called `My Album` and uploads images to it, execute the following commands:

```console
$ cd "My Album"
$ imgit init
$ imgit push
```

> [!NOTE]
> The first time using the program, you will be asked to authenticate to your Imgur account and grant access to the application.


Syntax uses keywords from the git program: you may `clone` an existing album, `fetch` online changes, `pull` the online images locally, `push` your changes online, an view the changes `status`. More actions and informations are available with the `-h, --help` flag.

> [!WARNING]
> Imgur limits to 50 uploads per hour ([source](https://help.imgur.com/hc/en-us/articles/26511665959579)).

## Contributing

Contributions are welcomed. Do not hesitate to submit a pull request with your changes! Submit bug reports and feature suggestions in the [issue tracker](https://github.com/ychalier/imgit/issues/new/choose).

## License

This project is licensed under the GPL-3.0 license.
