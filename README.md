# Google Drive Sharing Manager
A management tool to let others upload files without giving them editor access to the folder.

This originally started as a way for me to let other people share pictures and videos from concerts without giving them access to the folder that everyone had read access to, so that we didn't accidentally lose files.  However, I thought this might be of use to others as well, so I expanded its scope.

It works by parsing a folder structure at a given root node, and then recreates that folder structure in a new location and shares that with the person with media to upload.  After they've finished, it then copies each file into the main folder.

## Prerequisites
1. You must have [Google Cloud access credentials](https://developers.google.com/workspace/guides/create-credentials).  I by default store mine at `~/.gcloud/credentials.json` and that's where this program will search for them by default (unless specified at the command line).
2. This application uses [Poetry](https://python-poetry.org/docs/) in order to build.

## Setup
First clone this repository.
```bash
git clone https://github.com/cawaltrip/gdrive-sharing-manager.git
cd gdrive-sharing-manager
```

Then, install the project
```bash
poetry install
```

If you'd like to create a wheel and install it with `pip`, then run the following:
```bash
poetry build
pip install dist/gdrive-sharing-manager-*-py3-none-any.whl
```

## Usage
Create and share a folder with `alice@example.com`
```bash
grdive-share create --source-root "FOOBAR" --dest-root "BAZLOW" --user "alice@example.com"
```

Merge additions made by `alice@example.com` back into the main folder.
```bash
gdrive-share merge --source-root "FOOBAR" --dest-root "BAZLOW" --user "alice@example.com"
```

If using poetry, and not installing from pip, prepend all commands with `poetry run`.  E.g.,
```bash
poetry run gdrive-share create --source-root "FOOBAR" --dest-root "BAZLOW" --user "alice@example.com"
```

Specify a configuration file for some of the options
```bash
gdrive-share -c ~/.config/gdrive-sharing-manager/config create --user "alice@example.com"
```

## Configuration File
If a configuration file is used, it must be the first command line argument specified.  This program accepts uses the extended interpolation found in Python's `configparser` to do it's work, so variables can be used.
No `DEFAULTS` section is used.  Here is a template that can be used:

```ini
[Common]
# Contains variables to be used elsewhere
main_folder_id = 
main_folder_name =
uploads_folder_id =
uploads_folder_name =

[Primary]
creds = ~/.gcloud/credentials.json

[Create]
# source_root_id = ${Common:main_folder_id}
source_root = ${Common:main_folder_name}
# dest_root_id = ${Common:uploads_folder_id}
dest_root = ${Common:uploads_folder_name}

[Merge]
# Notice that the source and destinations are swapped for the
# Merge step (i.e., source is the uploads folder and dest is
# the main folder)!
source_root_id = ${Common:uploads_folder_id}
# source_root = ${Common:uploads_folder_name}
dest_root_id = ${Common:main_folder_id}
# dest_root = ${Common:main_folder_name}
```



## TODO
- [x] Remove references to previous program.
  - [x] Including hardcoded folder values.
- [x] Add configuration file parsing.
- [ ] Tests?  What are those??
- [x] Automatically share folder with user.
- [ ] Determine if files with same names are identical files and don't copy over if so.
- [x] Update to Google Drive API v3.
- [ ] Make logging consistent

