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


class Merge(ArgParser):
    """Class that copies all the files back into the main folder structure"""

    parser = None
    logger = logging.getLogger("ludo.merge")

    def __init__(self):
        super(Merge, Merge.__init__())

    @staticmethod
    def add_arguments(subparsers, parents: List = []) -> None:
        Merge.parser = subparsers.add_parser(
            'merge',
            help="Merge the new pictures into the main album.",
            parents=parents)
        Merge.parser.set_defaults(func=Merge.merge)

    def merge(self):
        # Need to set token/credential
        test_token_path = Path(self.creds).parent.joinpath("token.json")
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
            ArgParser._service = build('drive', 'v2', credentials=creds)
            Merge.logger.info(f"Connected to API")

            Merge.logger.debug(f"Retrieving main media folder")
            ludo_folder = Merge._get_folder_by_id(Merge._MEDIA_BASE_FOLDER_ID)
            Merge.logger.debug(f"Retrieving new uploads folder")
            ludo_uploads_folder = Merge._get_folder_by_id(Merge._UPLOADS_BASE_FOLDER_ID)
            Merge.logger.debug(f"Retrieving specific uploads folder")
            folder_to_parse = Merge._get_folder_by_name_under_parent(ludo_uploads_folder['id'], self.new_folder_name)

            queue = [{
                "id": folder_to_parse['id'],
                "title": folder_to_parse['title']
            }]

            Merge.logger.debug(f"Creating file & folder tree structure of new items to merge")
            uploaded_files = Merge._get_files_folders_dict(queue)
            queue = [{
                "id": ludo_folder['id'],
                "title": ludo_folder['title']
            }]
            Merge.logger.debug(f"Creating file & folder tree structure of main folder")
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