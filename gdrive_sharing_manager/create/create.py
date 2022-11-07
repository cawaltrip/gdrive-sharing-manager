from gdrive_sharing_manager.argument_parser import ArgParser
from typing import List, Dict
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import traceback
import sys
import logging
from pathlib import Path


class Create(ArgParser):
    """Class that creates a new empty folder structure to share."""

    parser = None
    logger = logging.getLogger("gdrive-share.create")

    def __init__(self):
        super(Create, Create.__init__())

    @staticmethod
    def add_arguments(subparsers, parents: List = [], defaults: Dict = None) -> None:
        Create.parser = subparsers.add_parser(
            'create',
            help="Create empty folder structure to share with Ludo fan.",
            parents=parents)
        source_group = Create.parser.add_mutually_exclusive_group(required=False)
        source_group.add_argument('--source-root', help="Name of source folder (will use first one found).  "
                                                        "This is where the repository of files is.")
        source_group.add_argument('--source-root-id', help="Specific ID of the source folder.")
        dest_group = Create.parser.add_mutually_exclusive_group(required=False)
        dest_group.add_argument('--dest-root', help="Name of destination folder (will use first one found).  "
                                                    "The new folder to share will be created here.")
        dest_group.add_argument('--dest-root-id', help="Specific ID of the destination folder.")

        # Make sure that create() is called when this function is used because
        # there are no subcommands.
        Create.parser.set_defaults(func=Create.create)

        if defaults is not None:
            if Create.__name__ in defaults.keys():
                Create.parser.set_defaults(**defaults[Create.__name__])

    def create(self):
        if not self.user:
            Create.logger.critical("Must specify user to create upload folder for!")
            sys.exit(1)

        # Need to set token/credential
        test_token_path = self.creds.parent.joinpath("token.json")
        if test_token_path.exists():
            Create._token = test_token_path

        creds = None
        if Create._token.exists():
            Create.logger.debug(f"Retrieving credentials from {Create._token.resolve()}")
            creds = Credentials.from_authorized_user_file(str(Create._token), Create._SCOPES)
        if not creds or not creds.valid:
            Create.logger.debug(f"Creds are invalid.")
            if creds and creds.expired and creds.refresh_token:
                Create.logger.debug(f"Refreshing expired credentials")
                creds.refresh(Request())
            else:
                if not Create._creds.exists():
                    try:
                        Create._creds = Path(self.creds).expanduser()
                    except:
                        Create.logger.critical("Could not find credential!")
                        sys.exit(1)
                    if not Create._creds.exists():
                        Create.logger.critical("Could not find credential!")
                        sys.exit(1)
                Create.logger.debug(f"Retrieving credentials from {Create._creds.resolve()}")
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(Create._creds), Create._SCOPES)
                creds = flow.run_local_server(port=0)

            # Save the creds for the next run.
            with open(Create._token, "w") as token:
                Create.logger.debug(f"Writing token to {Create._token.resolve()}")
                token.write(creds.to_json())

        try:
            Create.logger.debug(f"Connecting to API")
            ArgParser._service = build('drive', 'v3', credentials=creds)
            Create.logger.info(f"Connected to API")

            Create.logger.debug(f"Retrieving source (main media) folder")
            if not self.source_root_id:
                if not self.source_root:
                    Create.logger.critical("Must specify a source folder or source folder ID!")
                    sys.exit(1)
                # Get the root folder information
                Create.logger.debug(f"Getting folder by name: {self.source_root}")
                source_folder = ArgParser._get_folder_by_name_under_parent(parent_id='root',
                                                                           folder_name=self.source_root)
            else:
                Create.logger.debug(f"Getting folder by ID: {self.source_root_id}")
                source_folder = ArgParser._get_folder_by_id(self.source_root_id)

            Create.logger.info(f"Retrieved source folder.")
            Create.logger.debug(f"Source folder ID: {source_folder['id']}")

            Create.logger.debug("Retrieving destination (uploads) folder")
            if not self.dest_root_id:
                if not self.dest_root:
                    Create.logger.critical("Must specify a destination folder or destination folder ID!")
                    sys.exit(1)
                # Get the root folder information
                Create.logger.debug(f"Getting folder by name: {self.dest_root}")
                dest_folder = ArgParser._get_folder_by_name_under_parent(parent_id='root',
                                                                         folder_name=self.dest_root)
            else:
                Create.logger.debug(f"Getting folder by ID: {self.dest_root_id}")
                source_folder = ArgParser._get_folder_by_id(self.dest_root_id)

            Create.logger.info(f"Retrieved destination folder")
            Create.logger.debug(f"Destination folder ID: {dest_folder['id']}")

            Create.logger.debug("Retrieving folder structure")
            queue = [{
                "id": source_folder['id'],
                "name": source_folder['name']
            }]

            folder_structure = ArgParser._get_files_folders_dict(queue, include_files=False)

        except HttpError as e:
            Create.logger.critical(f"The following error occurred: {e}")
            traceback.print_exc()
            sys.exit(1)

        try:
            Create.logger.info(f"Creating new folder for {self.user}")
            new_upload_folder_id = Create._create_folder(dest_folder['id'], self.user)
            Create.logger.info(f"Creating folder structure under {self.user}")
            if "child_folders" in folder_structure.keys():
                Create._duplicate_folder_structure(new_upload_folder_id, folder_structure['child_folders'])
            else:
                Create.logger.debug("No folder structure to create.")
        except HttpError as e:
            Create.logger.critical(f"The following error occurred: {e}")
            traceback.print_exc()
            sys.exit(1)

        Create.logger.info("Folder structure completed.")

        # Time to share the folder.
        Create.logger.debug(f"Sharing folder with: {self.user}")
        try:
            perm_id = ArgParser._share_folder_with_user(file_id=new_upload_folder_id, user=self.user)
        except HttpError as e:
            Create.logger.critical(f"The following error occurred: {e}")
            traceback.print_exc()
            sys.exit(1)
        Create.logger.info(f"Shared folder with: {self.user}")