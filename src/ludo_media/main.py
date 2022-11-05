import argparse
import logging
import sys
from pathlib import Path
from ludo_media.create.create import Create
from ludo_media.merge.merge import Merge


def parse_args():
    root = argparse.ArgumentParser()
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument('-v', '--verbose', action="count", default=0,
                        help="Increase the verbosity level.  Can be used multiple times.")
    common.add_argument('-q', '--quiet', action="count", default=0,
                        help="Decrease the verbosity level.  Can be used multiple times.")
    common.add_argument('-l', '--log', help="Path to log file if desired.")
    common.add_argument('-n', '--folder-name',
                        dest="new_folder_name", metavar="FOLDER_NAME",
                        help="Folder name to create/merge from", required=True)
    common.add_argument('-c', '--credential', dest="creds", help="Path to credential.json")

    subparsers = root.add_subparsers()
    Create.add_arguments(subparsers, [common])
    Merge.add_arguments(subparsers, [common])

    # Check if anything at all has been passed in and display usage if not
    if len(sys.argv) <= 1:
        root.print_help(sys.stderr)
        sys.exit(1)

    args = root.parse_args()

    # Configure logging
    logger = logging.getLogger('ludo')
    logger.setLevel(logging.DEBUG)

    # Console output:
    verbosity = logging.WARN - ((args.verbose - args.quiet) * 10)
    if verbosity < 0:
        verbosity = 0

    console_handler = logging.StreamHandler()
    console_handler.setLevel(verbosity)
    # console_handler.setFormatter(logging.Formatter('[%(levelname)s](%(name)s): %(message)s'))
    console_handler.setFormatter(logging.Formatter('[%(levelname)s](%(name)s:%(funcName)s:%(lineno)d): %(message)s'))
    logger.addHandler(console_handler)

    if args.log is not None:
        # Setup the log file handler.
        # This handler is nice if we want to have a log directory that rotates.
        # log_file_handler = logging.handlers.TimedRotatingFileHandler('logs/args.log', when='M', interval=2)
        log_file = Path(args.log).expanduser()
        log_file_handler = logging.FileHandler(filename=log_file, mode='w')
        log_file_handler.setFormatter(
            logging.Formatter('%(asctime)s [%(levelname)s](%(name)s:%(funcName)s:%(lineno)d): %(message)s'))
        log_file_handler.setLevel(logging.DEBUG)
        logger.addHandler(log_file_handler)



    return root.parse_args(), root


def main():
    args, parser = parse_args()

    if "func" not in args:
        parser.print_help(sys.stderr)
        sys.exit(1)
    args.func(args)


if __name__ == '__main__':
    main()