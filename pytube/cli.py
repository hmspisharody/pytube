# -*- coding: utf-8 -*-
"""A simple command line application to download youtube videos."""

import argparse
import datetime as dt
import gzip
import json
import logging
import os
import sys
from io import BufferedWriter
from typing import Tuple, Any

from pytube import __version__
from pytube import YouTube


logger = logging.getLogger(__name__)


def main():
    """Command line application to download youtube videos."""
    # noinspection PyTypeChecker
    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument("url", help="The YouTube /watch url", nargs="?")
    parser.add_argument(
        "--version", action="version", version="%(prog)s " + __version__,
    )
    parser.add_argument(
        "--itag", type=int, help="The itag for the desired stream",
    )
    parser.add_argument(
        "-l",
        "--list",
        action="store_true",
        help=(
            "The list option causes pytube cli to return a list of streams "
            "available to download"
        ),
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        dest="verbosity",
        help="Verbosity level",
    )
    parser.add_argument(
        "--build-playback-report",
        action="store_true",
        help="Save the html and js to disk",
    )

    args = parser.parse_args()
    logging.getLogger().setLevel(max(3 - args.verbosity, 0) * 10)

    if not args.url:
        parser.print_help()
        sys.exit(1)

    if args.list:
        display_streams(args.url)

    elif args.build_playback_report:
        build_playback_report(args.url)

    elif args.itag:
        download(args.url, args.itag)


def build_playback_report(url: str) -> None:
    """Serialize the request data to json for offline debugging.

    :param str url:
        A valid YouTube watch URL.
    """
    yt = YouTube(url)
    ts = int(dt.datetime.utcnow().timestamp())
    fp = os.path.join(
        os.getcwd(), "yt-video-{yt.video_id}-{ts}.json.gz".format(yt=yt, ts=ts),
    )

    js = yt.js
    watch_html = yt.watch_html
    vid_info = yt.vid_info

    with gzip.open(fp, "wb") as fh:
        fh.write(
            json.dumps(
                {
                    "url": url,
                    "js": js,
                    "watch_html": watch_html,
                    "video_info": vid_info,
                }
            ).encode("utf8"),
        )


def get_terminal_size() -> Tuple[int, int]:
    """Return the terminal size in rows and columns."""
    rows, columns = os.popen("stty size", "r").read().split()
    return int(rows), int(columns)


def display_progress_bar(
    bytes_received: int, filesize: int, ch: str = "█", scale: float = 0.55
) -> None:
    """Display a simple, pretty progress bar.

    Example:
    ~~~~~~~~
    PSY - GANGNAM STYLE(강남스타일) MV.mp4
    ↳ |███████████████████████████████████████| 100.0%

    :param int bytes_received:
        The delta between the total file size (bytes) and bytes already
        written to disk.
    :param int filesize:
        File size of the media stream in bytes.
    :param str ch:
        Character to use for presenting progress segment.
    :param float scale:
        Scale multiplier to reduce progress bar size.

    """
    _, columns = get_terminal_size()
    max_width = int(columns * scale)

    filled = int(round(max_width * bytes_received / float(filesize)))
    remaining = max_width - filled
    bar = ch * filled + " " * remaining
    percent = round(100.0 * bytes_received / float(filesize), 1)
    text = " ↳ |{bar}| {percent}%\r".format(bar=bar, percent=percent)
    sys.stdout.write(text)
    sys.stdout.flush()


def on_progress(
    stream: Any, chunk: Any, file_handler: BufferedWriter, bytes_remaining: int
) -> None:
    filesize = stream.filesize
    bytes_received = filesize - bytes_remaining
    display_progress_bar(bytes_received, filesize)


def download(url: str, itag: str) -> None:
    """Start downloading a YouTube video.

    :param str url:
        A valid YouTube watch URL.
    :param str itag:
        YouTube format identifier code.

    """
    # TODO(nficano): allow download target to be specified
    # TODO(nficano): allow dash itags to be selected
    yt = YouTube(url, on_progress_callback=on_progress)
    stream = yt.streams.get_by_itag(int(itag))
    if stream is None:
        print("Could not find a stream with itag: " + itag)
        sys.exit()
    print("\n{fn} | {fs} bytes".format(fn=stream.default_filename, fs=stream.filesize,))
    try:
        stream.download()
        sys.stdout.write("\n")
    except KeyboardInterrupt:
        sys.exit()


def display_streams(url: str) -> None:
    """Probe YouTube video and lists its available formats.

    :param str url:
        A valid YouTube watch URL.

    """
    yt = YouTube(url)
    for stream in yt.streams.all():
        print(stream)


if __name__ == "__main__":
    main()
