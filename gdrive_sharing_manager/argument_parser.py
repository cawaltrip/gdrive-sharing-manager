from argparse import ArgumentParser
from abc import ABC, abstractmethod
from typing import List, Dict
from pathlib import Path
from googleapiclient.errors import HttpError
import logging
import json


class ArgParser(ABC):

    # When changing SCOPES, the token needs to be recreated.
    _SCOPES = ['https://www.googleapis.com/auth/drive']

    _token = None
    _creds = None

    _folder_mimetype = "application/vnd.google-apps.folder"

    _service = None
    logger = logging.getLogger("gdrive-share.common")

    @staticmethod
    def _get_folder_by_id(folder_id: str):
        result = None
        try:
            result = ArgParser._service.files().get(fileId=folder_id).execute()
        except HttpError:
            pass
        return result

    @staticmethod
    def _get_children_by_query(query: str) -> List:
        result = []
        page_token = None
        while True:
            try:
                param = {}
                if page_token:
                    param['pageToken'] = page_token
                files = ArgParser._service.files().list(q=query, spaces='drive', **param).execute()
                result.extend(files['files'])
                page_token = files.get('nextPageToken')
                if not page_token:
                    break
            except HttpError as e:
                print(f"The following error occurred: {e}")

        return result

    @staticmethod
    def _get_children_folders_by_folder_id(folder_id: str) -> List:
        query = f"'{folder_id}' in parents and mimeType='{ArgParser._folder_mimetype}' and trashed=false"
        return ArgParser._get_children_by_query(query)

    @staticmethod
    def _get_children_files_by_folder_id(folder_id: str) -> List:
        query = f"'{folder_id}' in parents and not mimeType='{ArgParser._folder_mimetype}' and trashed=false"
        return ArgParser._get_children_by_query(query)

    @staticmethod
    def _get_files_folders_by_folder_id(folder_id: str) -> List:
        query = f"'{folder_id}' in parents and trashed=false"
        return ArgParser._get_children_by_query(query)

    @staticmethod
    def _get_parent_name(folder_id: str) -> str:
        parent = ArgParser._service.files().get(fileId=folder_id).execute()
        return parent['name']

    @staticmethod
    def _get_files_folders_dict(queue: List =[], include_files: bool = True) -> Dict:
        folder_list = {}
        while len(queue) > 0:
            current_folder = queue.pop()
            child_folders = ArgParser._get_children_folders_by_folder_id(current_folder['id'])
            if include_files:
                child_files = ArgParser._get_children_files_by_folder_id(current_folder['id'])

            test_files = ArgParser._get_files_folders_by_folder_id(current_folder['id'])

            parent_name = ArgParser._get_parent_name(current_folder['id'])
            folder_list['folder_name'] = current_folder['name']
            folder_list['folder_id'] = current_folder['id']
            folder_list['parent_name'] = parent_name
            if include_files:
                if len(child_files) > 0:
                    folder_list['child_files'] = child_files

            if len(child_folders) <= 0:
                return folder_list

            folder_list['child_folders'] = []
            for child in child_folders:
                queue.append(child)
                folder_list['child_folders'].append(ArgParser._get_files_folders_dict(queue))

        return folder_list

    @staticmethod
    def _create_folder(parent_id: str, folder_name: str) -> str:
        # Create a folder on Drive, returns the newly created folders ID
        file_metadata = {
            'name': folder_name,
            'mimeType': ArgParser._folder_mimetype,
            'parents': [parent_id]}
        new_folder = ArgParser._service.files().create(body=file_metadata, fields='id, parents').execute()
        ArgParser.logger.debug(f"New folder created.  ID: {new_folder.get('id')}.  Parents: {new_folder.get('parents')}")
        return new_folder.get('id')

    @staticmethod
    def _duplicate_folder_structure(parent_id: str, folders: List) -> None:
        if isinstance(folders, list):
            for f in folders:
                # Create the folder, and then if there are children, recurse.
                new_folder_id = ArgParser._create_folder(parent_id=parent_id, folder_name=f['folder_name'])
                if "child_folders" in f.keys():
                    ArgParser._duplicate_folder_structure(parent_id=new_folder_id, folders=f["child_folders"])

    @staticmethod
    def _get_folder_by_name_under_parent(parent_id: str, folder_name: str):
        match = None
        folders_to_search = ArgParser._get_children_folders_by_folder_id(folder_id=parent_id)
        matches = [f for f in folders_to_search if f['name'] == folder_name]
        if len(matches) > 0:
            # For now we'll always just take the first one if there are multiple name matches
            match = matches[0]
        return match

    @staticmethod
    def _copy_file(file, dest_id: str):
        new_file_body = {
            'name': file['name'],
            'parents': [dest_id]
        }
        ArgParser.logger.info(f"Copying {file['name']}")
        try:
            new_file = ArgParser._service.files().copy(fileId=file['id'], body=new_file_body).execute()
        except HttpError as e:
            ArgParser.logger.warning(f"Failed to copy {file['name']}.  Error: {e}")
        else:
            ArgParser.logger.debug(f"Copied file: {file['name']} (id: {new_file.get('id')}, parents: {new_file.get('parents')})")
        return new_file

    @staticmethod
    def _copy_all_files(orig: Dict, new_: Dict) -> None:
        ArgParser.logger.debug("Entering _copy_all_files")
        # parameters data structure:
        # dict {
        #       'folder_name'
        #       'folder_id'
        #       'parent_name'
        #       (Optional List) 'child_files'
        #       (Optional List) 'child_folders'
        # }
        next_orig_root = None

        def _copy_files_from_one_folder_to_another(files_to_copy: List, dest_folder: str) -> None:
            for f in files_to_copy:
                if f['mimeType'] != ArgParser._folder_mimetype:
                    ArgParser._copy_file(f, dest_folder)

        if "child_files" in new_.keys():
            try:
                ArgParser.logger.debug("Copying files from root directory.")
                _copy_files_from_one_folder_to_another(new_['child_files'], orig['folder_id'])
            except HttpError as e:
                print(f"Could not copy files from {new_['folder_name']}")
                print(f"HttpError: {e}")

        if "child_folders" in new_.keys():
            ArgParser.logger.debug("child_folders in new_.keys()")
            for f in new_['child_folders']:
                if not "child_files" in f.keys():
                    ArgParser.logger.debug("no child_files in f.keys() - continuing")
                    continue
                if "child_folders" in orig.keys():
                    ArgParser.logger.debug("child_folders in orig.keys()")
                    found = False
                    for ff in orig['child_folders']:
                        if f['folder_name'] == ff['folder_name']:
                            # We've found a matching folder.  Copy the items from new_ to orig.
                            ArgParser.logger.debug("found a matching folder")
                            found = True
                            try:
                                ArgParser.logger.debug("Getting ready to enter "
                                                       "_copy_files_from_one_folder_to_another()")
                                if "child_files" in f:
                                    _copy_files_from_one_folder_to_another(f['child_files'], ff['folder_id'])
                                else:
                                    ArgParser.logger.critical("How did we hit this part??")
                            except HttpError as e:
                                ArgParser.logger.error(f"Could not copy files from {f['folder_name']}")
                                ArgParser.logger.error(f"HttpError: {e}")
                            ArgParser.logger.debug("setting next_orig_root")
                            next_orig_root = ff
                            break  # This one is break because we're in nested for loop currently.
                    if not found:
                        # Then we have a new folder.  Create the new folder in orig with the name from new_
                        # and then copy the items from new_ to orig.  Make sure there's actually files in new_
                        try:
                            ArgParser.logger.debug("creating new folder in orig (from new_)")
                            new_folder_id = ArgParser._create_folder(orig['folder_id'], f['folder_name'])
                        except HttpError as e:
                            ArgParser.logger.error(f"Could not create new folder: {f['folder_name']}")
                            ArgParser.logger.error(f"HttpError: {e}")
                            continue  # not break?
                        try:
                            ArgParser.logger.debug("Getting ready to enter "
                                                   "_copy_files_from_one_folder_to_another()")
                            _copy_files_from_one_folder_to_another(f['child_files'], new_folder_id)
                        except HttpError as e:
                            ArgParser.logger.error(f"Could not copy files from {f['folder_name']}")
                            ArgParser.logger.error(f"HttpError: {e}")
                else:
                    # Then we also have a new folder.  Create the new folder in orig with the name from new_
                    # and then copy the items from new_ to orig.  Make sure there's actually files in new_
                    try:
                        new_folder_id = ArgParser._create_folder(orig['folder_id'], f['folder_name'])
                    except HttpError as e:
                        ArgParser.logger.error(f"Could not create new folder: {f['folder_name']}")
                        ArgParser.logger.error(f"HttpError: {e}")
                        continue  # not break?
                    try:
                        _copy_files_from_one_folder_to_another(f['child_files'], new_folder_id)
                    except HttpError as e:
                        ArgParser.logger.error(f"Could not copy files from {f['folder_name']}")
                        ArgParser.logger.error(f"HttpError: {e}")
                if "child_folders" in f.keys():
                    ArgParser.logger.info("Recursing on child_folders of f.keys()")
                    # Recurse
                    if next_orig_root is None:
                        ArgParser.logger.debug("Setting 'fake' next_orig_root")
                        # Create a fake dictionary to pass to the recursive call.
                        next_orig_root = {
                            "folder_name": f['folder_name'],
                            "folder_id": new_folder_id,
                        }
                    ArgParser._copy_all_files(next_orig_root, f)

    @staticmethod
    def _share_folder_with_user(file_id: str, user: str, email_message: str = None):
        user_permission = {
            'type': 'user',
            'role': 'writer',
            'emailAddress': f"{user}"
        }
        response = ArgParser._service.permissions().create(fileId=file_id,
                                                           body=user_permission,
                                                           fields='id').execute()
        return response.get('id')




    @staticmethod
    @abstractmethod
    def add_arguments(subparsers, parents: List = [], defaults=None) -> None:
        pass
