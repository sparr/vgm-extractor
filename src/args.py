import argparse

def parse():
    arg_parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    arg_parser.add_argument("-v", "--verbose", action="count", default=0)

    arg_parser.add_argument("games", metavar="game", nargs="*", help="games to extract")

    arg_parser.add_argument(
        "-o", "--outputpath", help="path to output folder", required=True
    )

    arg_parser.add_argument(
        "--steamlibrarypath",
        help="path to steam library folder which contains steamapps/",
        required=False,
    )

    arg_parser.add_argument(
        "-a",
        "--albumsuffix",
        help="appended to the game name in the Album metadata for each track",
        default=" [VGMX]",
    )

    # TODO priority order of formats
    arg_parser.add_argument(
        "--format", help="preferred file format/extension, or '*' for all", default="*"
    )

    arg_parser.add_argument(
        "--overwrite",
        help="overwrite existing files",
        default=False,
        action="store_const",
        const=True,
    )

    arg_parser.add_argument(
        "--rescan",
        help="extract music for target directories that already exist",
        default=False,
        action="store_const",
        const=True,
    )

    arg_parser.add_argument(
        "--minduration",
        help="minimum duration in seconds of files to keep",
        type=int,
        default=30,
    )

    args = arg_parser.parse_args()
    args.parser = arg_parser
    return args