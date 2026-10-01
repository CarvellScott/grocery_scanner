#!/usr/bin/env python3
import argparse
import configparser
import datetime
import enum
import importlib.resources
import io
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import uuid
import warnings
import zipfile
import zipapp

try:
    import bottle
except ModuleNotFoundError:
    warnings.warn("bottle.py module not found.")

import grocery_scanner.repositories
import grocery_scanner.models
import grocery_scanner.services

_ASSETS = importlib.resources.files("grocery_scanner")


class _HTMLTemplateEnum(enum.Enum):
    HOME_PAGE = "static/home.html"
    ITEM_PAGE = "static/item.html"
    LOGWATCH_PAGE = "static/logwatch.html"
    STATIC_REDIRECTOR = "static/static_redirector.html"
    STYLES_CSS = "static/styles.css"

    def __new__(cls, value):
        obj = object.__new__(cls)
        obj._value_ = _ASSETS.joinpath(value).read_bytes()
        return obj

    def __call__(self):
        return self.value


class BottleAdapter:
    def __init__(self, repo, config_filepath=None):
        self._repo = repo
        self._start_time = datetime.datetime.now()
        self._secret = str(uuid.uuid4())

        # I'd prefer to supply the config from outside of the constructor, but
        # bottle needs to read the filepath, a dict, or a module.
        self._config = None
        self._config_filepath = config_filepath
        if self._config_filepath and self._config_filepath.exists():
            config = configparser.ConfigParser()
            config.read(self._config_filepath)
            self._config = config

        self._app = None


    def change_item_status(self, reference):
        action = bottle.request.params.get("action")
        grocery_scanner.services.change_item_status(self._repo, reference, action)
        return bottle.redirect("/")

    def home_page(self):
        template = bottle.SimpleTemplate(_HTMLTemplateEnum.HOME_PAGE())
        return template.render()

    def nfc_csv(self):
        """
        Produces a .csv file of URLS compatible with NXP Tag Writer
        The url_prefix here should be the absolute url to whatever hosts the
        STATIC_REDIRECTOR page.
        """
        url_prefix = bottle.request.params.get("url_prefix")
        if url_prefix:
            if "%s" not in url_prefix:
                return bottle.abort(400, "The 'url_prefix' parameter must be an absolute url with a %s as a placeholder")

        if not url_prefix:
            urlparts = bottle.request.urlparts
            scheme = urlparts.scheme
            netloc = urlparts.netloc
            url_prefix = f"{scheme}://{netloc}/nfc/items/%s"
        formatter = url_prefix.replace("%s", "{}").format

        file_data = grocery_scanner.services.generate_nfc_csv_from_repo(self._repo, formatter)
        # Would use text/csv for MIME type, but browsers insist on turning it
        # into an automatic download, even with Content-Disposition = inline
        bottle.response.content_type = 'text/plain; charset=UTF8'
        return file_data

    def static_redirector(self):
        """
        This page is intended to be downloadable such that you can upload it to
        a static webhosting service.
        """
        repo = self._repo
        item_dct_list = []
        item_dct = {_.reference: _.url for _ in repo.iter_items()}
        item_json = json.dumps(item_dct, indent=2)
        for item in repo.iter_items():
            shop_url = item.url
            entry = (item.reference, item.name, shop_url)
            item_dct_list.append(entry)
        template = bottle.SimpleTemplate(_HTMLTemplateEnum.STATIC_REDIRECTOR())
        return template.render(item_json=item_json, items=item_dct_list)

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


    def make_app(self):
        """
        Creates a bottle.Bottle instance, assigns routes to it and returns it.
        """
        # The goal is for the entire API to be accessible via NFC tags/QR codes.
        # Therefore, most resources need to be accessible with GET
        app = bottle.Bottle()
        app.route("/", ["GET"], self.home_page)
        app.route("/items/<reference>", ["GET"], self.change_item_status)
        app.route("/grocery_list.md", ["GET"], self.markdown_grocery_list)
        app.route("/nfc.csv", ["GET"], self.nfc_csv)
        app.route("/styles.css", ["GET"], self.style)
        app.route("/logwatch", ["GET"], self.logwatch)
        app.route("/logstream", ["GET"], self.logstream)
        app.route("/static_redirector", ["GET"], self.static_redirector)
        app.config.load_config(self._config_filepath)
        return app


    def __call__(self):
        app = self.make_app()
        self._app = app
        bottle.run(self._app, debug=True, reloader=True)


def get_args():
    default_config_path = pathlib.Path("./config.ini")
    parser = argparse.ArgumentParser()
    extra_help = "Defaults to %(default)s"
    parser.add_argument(
        "-c",
        "--config-filepath",
        type=pathlib.Path,
        default=(default_config_path if default_config_path.exists() else None),
        required=not default_config_path.exists(),
        help=(
            "A .ini file containing configuration. " +
            (extra_help if default_config_path.exists() else "")
        )
    )

    parser.add_argument(
        "grocery_definitions",
        type=pathlib.Path,
        help="A .md or .ini file containing grocery definitions."
    )

    args = parser.parse_args()
    return args


def main():
    args = get_args()
    cls = grocery_scanner.models.GroceryItem
    item_repo = grocery_scanner.repositories.CSVRepository(cls)
    runtime_path = pathlib.Path(sys.argv[0]).absolute()

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
            item_repo.read_from_markdown_file_handler(f)

    api = BottleAdapter(item_repo, args.config_filepath)
    api()


if __name__ == "__main__":
    main()
