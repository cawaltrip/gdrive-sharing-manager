from ludo_media.argument_parser import ArgParser
from typing import List
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
    logger = logging.getLogger("ludo.create")

    def __init__(self):
        super(Create, Create.__init__())

    @staticmethod
    def add_arguments(subparsers, parents: List = []) -> None:
        Create.parser = subparsers.add_parser(
            'create',
            help="Create empty folder structure to share with Ludo fan.",
            parents=parents)
        Create.parser.set_defaults(func=Create.create)

    def create(self):
        creds = None
        if Create._token.exists():
            Create.logger.debug(f"Retrieving credentials from {Create._token.resolve()}")
            creds = Credentials.from_authorized_user_file(Create._token, Create._SCOPES)
        if not creds or not creds.valid:
            Create.logger.debug(f"Creds are invalid.")
            if creds and creds.expired and creds.refresh_token:
                Create.logger.debug(f"Refreshing expired credentials")
                creds.refresh(Request())
            else:
                if not Create._creds.exists():
                    try:
                        Create._creds = Path(self.creds)
                    except:
                        Create.logger.critical("Could not find credential!")
                        sys.exit(1)
                    if not Create._creds.exists():
                        Create.logger.critical("Could not find credential!")
                        sys.exit(1)
                Create.logger.debug(f"Retrieving credentials from {Create._creds.resolve()}")
                flow = InstalledAppFlow.from_client_secrets_file(
                    Create._creds, Create._SCOPES)
                creds = flow.run_local_server(port=0)

            # Save the creds for the next run.
            with open(Create._token, "w") as token:
                Create.logger.debug(f"Writing token to {Create._token.resolve()}")
                token.write(creds.to_json())

        try:
            Create.logger.debug(f"Connecting to API")
            ArgParser._service = build('drive', 'v2', credentials=creds)
            Create.logger.info(f"Connected to API")
            # Get the root folder information
            # about = ArgParser._service.about().get().execute()
            # root_folder = ArgParser._service.files().get(fileId=about['rootFolderId']).execute()
            # root_children = Create._get_children_folders_by_folder_id(root_folder['id'])

            Create.logger.debug(f"Retrieving main media folder")
            ludo_folder = Create._get_folder_by_id(Create._MEDIA_BASE_FOLDER_ID)
            Create.logger.debug(f"Retrieving new uploads folder")
            ludo_uploads_folder = Create._get_folder_by_id(Create._UPLOADS_BASE_FOLDER_ID)

            queue = [{
                "id": ludo_folder['id'],
                "title": ludo_folder['title']
            }]

            Create.logger.debug(f"Creating folder tree structure of main media folder")
            ludo_folder_children = ArgParser._get_files_folders_dict(queue, include_files=False)

        except HttpError as e:
            Create.logger.critical(f"The following error occurred: {e}")
            traceback.print_exc()
            sys.exit(1)
        try:
            Create.logger.info(f"Creating new folder for {self.new_folder_name}")
            new_upload_folder_id = Create._create_folder(ludo_uploads_folder['id'], self.new_folder_name)
            Create.logger.info(f"Creating folder tree structure under {self.new_folder_name}")
            Create._duplicate_folder_structure(new_upload_folder_id, ludo_folder_children['child_folders'])
        except HttpError as e:
            Create.logger.critical(f"The following error occurred: {e}")
            traceback.print_exc()
            sys.exit(1)
