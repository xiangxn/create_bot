import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "grpc"))
import argparse
import json
from create_account import metadata
from create_account.server import Server


def main(argv):
    """Program entry point.

    :param argv: command-line arguments
    :type argv: :class:`list`
    """
    author_strings = []
    for name, email in zip(metadata.authors, metadata.emails):
        author_strings.append('Author: {0} <{1}>'.format(name, email))

    epilog = '''
{project} {version}

{authors}
URL: <{url}>
'''.format(project=metadata.project, version=metadata.version, authors='\n'.join(author_strings), url=metadata.url)

    arg_parser = argparse.ArgumentParser(prog=argv[0], formatter_class=argparse.RawDescriptionHelpFormatter, description=metadata.description, epilog=epilog)
    arg_parser.add_argument('--config', type=argparse.FileType('r'), help='config file for console')
    arg_parser.add_argument('-V', '--version', action='version', version='{0} {1}'.format(metadata.project, metadata.version))
    arg_parser.add_argument('-D', '--debug', action='store_true', help='debug mode')
    arg_parser.add_argument('-G', '--generate', action='store_true', help='generate address')
    arg_parser.add_argument('-C', '--clean', action='store_true', help='clean address in database')
    arg_parser.add_argument('-E', '--export', help='Export data to file')
    arg_parser.add_argument('-T', '--transfer', action='store_true', help='Distribute tokens')
    arg_parser.add_argument('-S', '--staking', action='store_true', help='staking tokens')

    args = arg_parser.parse_args(args=argv[1:])
    config_info = procConfig(args.config)
    server = Server(config_info, args.debug)
    if args.generate:
        server.generate_address()
    elif args.clean:
        server.drop_data()
    elif args.export:
        server.export_data(args.export)
    elif args.transfer:
        server.run_transfer()
    elif args.staking:
        server.run_staking()
    else:
        server.run()
    return 0


def procConfig(cf):
    config_info = {}
    if not cf:
        cf = open("./config.json", "r")
    config_info = json.load(cf)
    return config_info


def entry_point():
    """Zero-argument entry point for use with setuptools/distribute."""
    raise SystemExit(main(sys.argv))


if __name__ == '__main__':
    entry_point()