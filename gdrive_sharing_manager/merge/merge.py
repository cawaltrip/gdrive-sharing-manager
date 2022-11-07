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


class Merge(ArgParser):
    """Class that copies all the files back into the main folder structure"""

    parser = None
    logger = logging.getLogger("gdrive-share.merge")

    def __init__(self):
        super(Merge, Merge.__init__())

    @staticmethod
    def add_arguments(subparsers, parents: List = [], defaults=None) -> None:
        Merge.parser = subparsers.add_parser(
            'merge',
            help="Merge the new pictures into the main album.",
            parents=parents)
        source_group = Merge.parser.add_mutually_exclusive_group(required=False)
        source_group.add_argument('--source-root', help="Name of source folder (will use first one found).  "
                                                        "This is the folder where the user's files are found")
        source_group.add_argument('--source-root-id', help="Specific ID of the source folder.")
        dest_group = Merge.parser.add_mutually_exclusive_group(required=False)
        dest_group.add_argument('--dest-root', help="Name of destination folder (will use first one found).  "
                                                    "This is where to copy the files to.  This is most "
                                                    "likely the source folder from the `create` step.")
        dest_group.add_argument('--dest-root-id', help="Specific ID of the destination folder.")
        Merge.parser.set_defaults(func=Merge.merge)

        # Make sure that merge() is called when this function is used because
        # there are no subcommands.
        Merge.parser.set_defaults(func=Merge.merge)

        if defaults is not None:
            if Merge.__name__ in defaults.keys():
                Merge.parser.set_defaults(**defaults[Merge.__name__])

    def merge(self):
        if not self.user:
            Merge.logger.critical("Muse specify user to retrieve media from!")

        # Need to set token/credential
        test_token_path = self.creds.parent.joinpath("token.json")
        if test_token_path.exists():
            Merge._token = test_token_path

        creds = None
        if Merge._token.exists():
            Merge.logger.debug(f"Retrieving credentials from {Merge._token.resolve()}")
            creds = Credentials.from_authorized_user_file(str(Merge._token), Merge._SCOPES)
        if not creds or not creds.valid:
            Merge.logger.debug(f"Creds are invalid.")
            if creds and creds.expired and creds.refresh_token:
                Merge.logger.debug(f"Refreshing expired credentials")
                creds.refresh(Request())
            else:
                if not Merge._creds.exists():
                    try:
                        Merge._creds = Path(self.creds).expanduser()
                    except:
                        Merge.logger.critical("Could not find credential!")
                        sys.exit(1)
                    if not Merge._creds.exists():
                        Merge.logger.critical("Could not find credential!")
                        sys.exit(1)
                Merge.logger.debug(f"Retrieving credentials from {Merge._creds.resolve()}")
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(Merge._creds), Merge._SCOPES)
                creds = flow.run_local_server(port=0)

            # Save the creds for the next run.
            with open(Merge._token, "w") as token:
                Merge.logger.debug(f"Writing token to {Merge._token.resolve()}")
                token.write(creds.to_json())
        try:
            Merge.logger.debug(f"Connecting to API")
            ArgParser._service = build('drive', 'v3', credentials=creds)
            Merge.logger.info(f"Connected to API")

            Merge.logger.debug(f"Retrieving source (uploads) folder")
            if not self.source_root_id:
                if not self.source_root:
                    Merge.logger.critical("Must specify a source folder or source folder ID!")
                    sys.exit(1)
                # Get the root folder information
                Merge.logger.debug(f"Getting folder by name: {self.source_root}")
                source_folder = ArgParser._get_folder_by_name_under_parent(parent_id='root',
                                                                           folder_name=self.source_root)
            else:
                Merge.logger.debug(f"Getting folder by ID: {self.source_root_id}")
                source_folder = ArgParser._get_folder_by_id(self.source_root_id)

            Merge.logger.info(f"Retrieved source folder.")
            Merge.logger.debug(f"Source folder ID: {source_folder['id']}")

            Merge.logger.debug("Retrieving destination (main media) folder")
            if not self.dest_root_id:
                if not self.dest_root:
                    Merge.logger.critical("Must specify a destination folder or destination folder ID!")
                    sys.exit(1)
                # Get the root folder information
                Merge.logger.debug(f"Getting folder by name: {self.dest_root}")
                dest_folder = ArgParser._get_folder_by_name_under_parent(parent_id='root',
                                                                         folder_name=self.dest_root)
            else:
                Merge.logger.debug(f"Getting folder by ID: {self.dest_root_id}")
                dest_folder = ArgParser._get_folder_by_id(self.dest_root_id)

            Merge.logger.info(f"Retrieved destination folder")
            Merge.logger.debug(f"Destination folder ID: {dest_folder['id']}")

            Merge.logger.debug(f"Retrieving specific uploads folder")
            folder_to_parse = Merge._get_folder_by_name_under_parent(source_folder['id'], self.user)

            Merge.logger.debug(f"Creating folder & files structure of new items to merge")
            queue = [{
                "id": folder_to_parse['id'],
                "name": folder_to_parse['name']
            }]
            uploaded_files = Merge._get_files_folders_dict(queue)

            Merge.logger.debug(f"Creating folder & files structure of destination folder")
            queue = [{
                "id": dest_folder['id'],
                "name": dest_folder['name']
            }]
            original_files = Merge._get_files_folders_dict(queue)

            Merge.logger.info(f"Merging in new media!")
            ArgParser._copy_all_files(original_files, uploaded_files)

        except HttpError as e:
            Merge.logger.critical(f"The following error occurred: {e}")
            traceback.print_exc()
            sys.exit(1)
        except KeyError as e:
            Merge.logger.critical(f"The following error occurred: {e}")
            traceback.print_exc()
            sys.exit(1)
        else:
            Merge.logger.info(f"Successfully copied all files over!")