#!/usr/bin/env python3
import argparse
import configparser
import datetime
import enum
import importlib.resources
import io
import os
import pathlib
import re
import subprocess
import sys
import uuid
import warnings

try:
    import bottle
except ModuleNotFoundError:
    warnings.warn("bottle.py module not found.")

import grocery_scanner.core
import grocery_scanner.models
import grocery_scanner.services

_ASSETS = importlib.resources.files("grocery_scanner")


class _HTMLTemplateEnum(enum.Enum):
    HOME_PAGE = "static/home.html"
    ITEM_PAGE = "static/item.html"
    LOGWATCH_PAGE = "static/logwatch.html"
    STYLES_CSS = "static/styles.css"

    def __new__(cls, value):
        obj = object.__new__(cls)
        obj._value_ = _ASSETS.joinpath(value).read_bytes()
        return obj

    def __call__(self):
        return self.value


class BottleAdapter:
    def __init__(self, repo):
        self._repo = repo
        self._start_time = datetime.datetime.now()
        self._secret = str(uuid.uuid4())

    def mark_item_requested(self, reference):
        grocery_scanner.services.mark_item_requested(self._repo, reference)
        return bottle.redirect("/")

    def home_page(self):
        repo = self._repo
        item_list = [repo[key] for key in repo.keys()]
        item_dct_list = []
        for item in item_list:
            entry = [
                item.reference,
                item.name,
                item.url,
                item.status
            ]
            item_dct_list.append(entry)

        template = bottle.SimpleTemplate(_HTMLTemplateEnum.HOME_PAGE())
        return template.render(items=item_dct_list)

    def nfc_csv(self):
        """
        Produce a .csv file of URLS compatible with NXP Tag Writer
        """
        urlparts = bottle.request.urlparts
        scheme = urlparts.scheme
        netloc = urlparts.netloc
        url_prefix = f"{scheme}://{netloc}/nfc/items"

        file_data = grocery_scanner.services.generate_nfc_csv_from_repo(self._repo, url_prefix)
        # Would use text/csv for MIME type, but browsers insist on turning it
        # into an automatic download, even with Content-Disposition = inline
        bottle.response.content_type = 'text/plain; charset=UTF8'
        return file_data

    def nfc_tag_redirect(self, redirect_url):
        """
        Redirect to whatever url is supplied. Arbitrary redirects are
        technically a vulnerability, but given the self-hosted service, not
        really a threat.
        """
        return bottle.redirect(redirect_url)

    def style(self):
        bottle.response.content_type = 'text/css; charset=UTF8'
        return _HTMLTemplateEnum.STYLES_CSS()

    def markdown_grocery_list(self):
        """
        Produce a markdown-formatted grocery list, ideal for importing into
        Obsidian
        """
        bottle.response.content_type = 'text/plain; charset=UTF8'
        return grocery_scanner.services.generate_markdown_item_list(self._repo)

    def logwatch(self):
        return bottle.SimpleTemplate(_HTMLTemplateEnum.LOGWATCH_PAGE()).render()

    def logstream(self):
        command = ["top", "-b", "-n", "1", "-p", str(os.getpid())]
        data = subprocess.check_output(command, universal_newlines=True)

        bottle.response.content_type = "text/event-stream"
        bottle.response.cache_control = "no-cache"
        raw_data = ["retry: 1000\n"] + [f"data: {_}\n" for _ in data.splitlines()]
        data = "".join(raw_data)
        data += "\n"
        yield data

    def get_config(self):
        repo = self._repo
        item_list = [repo[key] for key in repo.keys()]
        config = configparser.ConfigParser()
        strio = io.StringIO()
        for item in item_list:
            config.add_section(item.reference)
            config[item.reference] = vars(item)
        config.write(strio)
        bottle.response.content_type = 'text/plain; charset=UTF8'
        return strio.getvalue()

    def get_executable(self):
        path = pathlib.Path(sys.argv[0]).absolute()
        bottle.response.content_type = 'application/zip'
        with open(path, "rb") as f:
            return f.read()

    def make_app(self):
        """
        Creates a bottle.Bottle instance, assigns routes to it and returns it.
        """
        # The goal is for the entire API to be accessible via NFC tags/QR codes.
        # Therefore, most resources need to be accessible with GET
        app = bottle.Bottle()
        app.route("/", ["GET"], self.home_page)
        app.route("/items/<reference>", ["GET"], self.mark_item_requested)
        app.route("/grocery_list.md", ["GET"], self.markdown_grocery_list)
        app.route("/nfc.csv", ["GET"], self.nfc_csv)
        app.route("/nfc<redirect_url:path>", ["GET"], self.nfc_tag_redirect)
        app.route("/styles.css", ["GET"], self.style)
        app.route("/logwatch", ["GET"], self.logwatch)
        app.route("/logstream", ["GET"], self.logstream)
        app.route("/config.ini", ["GET"], self.get_config)
        app.route("/download_server", ["GET"], self.get_executable)
        return app


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "grocery_definitions",
        type=pathlib.Path,
        help="A .md or .ini file containing grocery definitions."
    )
    parser.add_argument(
        "-a",
        "--address",
        type=str,
        default=os.getenv("GROCERY_SCANNER_ADDRESS") or "0.0.0.0"
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=os.getenv("GROCERY_SCANNER_PORT") or 8080
    )

    args = parser.parse_args()
    return args


def main():
    args = get_args()
    cls = grocery_scanner.models.GroceryItem
    item_repo = grocery_scanner.core.CSVRepository(cls)

    # I want the grocery data to be readable from some simple format.
    # I want it to be borderline trivial to write but still extendable later.
    # Since configparser's format supports comments I opted for that.
    # May revisit supporting markdown in the future or .csv
    if args.grocery_definitions.suffix == ".ini":
        grocery_defs = configparser.ConfigParser()
        with open(args.grocery_definitions, "r") as f:
            grocery_defs.read_string(f.read())

        for section in grocery_defs.sections():
            raw_item = dict(grocery_defs.items(section))
            item = grocery_scanner.models.GroceryItem(**raw_item)
            item_repo.save(item)

    if args.grocery_definitions.suffix == ".md":
        with open(args.grocery_definitions, "r") as f:
            grocery_scanner.services.add_items_from_markdown(item_repo, f.read())

    api = BottleAdapter(item_repo)
    app = api.make_app()
    bottle.run(app, host=args.address, port=args.port)


if __name__ == "__main__":
    main()
