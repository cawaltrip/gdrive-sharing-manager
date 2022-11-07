import argparse
import logging
import sys
from pathlib import Path
from gdrive_sharing_manager.create.create import Create
from gdrive_sharing_manager.merge.merge import Merge
from configparser import ConfigParser, ExtendedInterpolation


def parse_args():
    root = argparse.ArgumentParser()

    # Read in a configuration file and if so, convert it to a dictionary
    # for future use.
    config_parser = argparse.ArgumentParser(add_help=False)
    config_parser.add_argument('-c','--conf', help="Path to optional configuration file.")
    conf_args, remaining_argv = config_parser.parse_known_args()
    config = None
    if conf_args.conf is not None:
        conf_file = Path(conf_args.conf).expanduser()
        if conf_file.exists():
            conf = ConfigParser(interpolation=ExtendedInterpolation())
            try:
                conf.read(conf_file)
            except:
                pass
            else:
                # There were options in the config file, so create a dictionary of them.
                config = {s:dict(conf.items(s)) for s in conf.sections()}
    primary = argparse.ArgumentParser(add_help=False)
    primary.add_argument('-v', '--verbose', action="count", default=0,
                        help="Increase the verbosity level.  Can be used multiple times.")
    primary.add_argument('-q', '--quiet', action="count", default=0,
                        help="Decrease the verbosity level.  Can be used multiple times.")
    primary.add_argument('-l', '--log', help="Path to log file if desired.")
    primary.add_argument('-C', '--credentials', dest="creds",
                        help="Path to credentials.json"),
    primary.add_argument('-u', '--user', help="User to share folder/retrieve files from.")

    if config is not None and "Primary" in config.keys():
        primary.set_defaults(**config['Primary'])

    subparsers = root.add_subparsers()
    Create.add_arguments(subparsers, [primary], config)
    Merge.add_arguments(subparsers, [primary], config)

    # Check if anything at all has been passed in and display usage if not
    if len(sys.argv) <= 1:
        root.print_help(sys.stderr)
        sys.exit(1)

    args = root.parse_args(remaining_argv)

    # Configure logging
    logger = logging.getLogger('gdrive-share')
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

    if args.creds:
        args.creds = Path(args.creds).expanduser()
    else:
        logger.critical("Must specify credentials file.")
        sys.exit(1)

    return args, root


def main():
    # Entry point for entire program.
    args, parser = parse_args()

    if "func" not in args:
        parser.print_help(sys.stderr)
        sys.exit(1)
    args.func(args)


if __name__ == '__main__':
    main()