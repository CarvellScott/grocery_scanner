#!/usr/bin/env python3
import argparse
import configparser
import doctest
import csv
import enum
import io
import importlib.resources
import itertools
import json
import multiprocessing
import os
import pathlib
import re
import sys
import time
import uuid
import webbrowser

import bottle

import grocery_scanner.core
import grocery_scanner.models
import grocery_scanner.services


class _HTMLTemplateEnum(enum.Enum):
    HOME_PAGE = "grocery_scanner/data/home.html"
    ITEM_PAGE = "grocery_scanner/data/item.html"
    LOGWATCH_PAGE = "grocery_scanner/data/logwatch.html"
    CART_PAGE = "grocery_scanner/data/cart.html"
    STYLES_CSS = "grocery_scanner/data/styles.css"

    def __call__(self):
        data = None
        path = pathlib.Path(self.value)
        with importlib.resources.as_file(path) as f:
            data = f.open("rb").read()
        return data


class ServerProcess(multiprocessing.Process):
    def __init__(self, app, host, port):
        super().__init__()
        self._app = app
        self._host = host
        self._port = port

    def run(self):
        bottle.run(self._app, host=self._host, port=self._port)


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-c",
        "--config-file",
        type=pathlib.Path,
        required=not os.getenv("GROCERY_SCANNER_CONFIG"),
        default=os.getenv("GROCERY_SCANNER_CONFIG")
    )
    parser.add_argument(
        "-a",
        "--address",
        type=str,
        default="0.0.0.0"
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=8080
    )


    args = parser.parse_args()
    return args


class DB2WebAdapter:
    def __init__(self, db):
        self._db = db
        self._secret = str(uuid.uuid4())

    def individual_item(self, reference):
        item = self._db.load(reference)
        secret = self._secret
        cart = bottle.request.get_cookie("cart", secret=secret) or dict()
        action = bottle.request.params.get("action")
        match action:
            case "request":
                cart[item.reference] = 1
                bottle.response.set_cookie("cart", cart, path="/", secret=secret)
                print(cart, file=sys.stderr)
                return bottle.redirect("/cart")
            case "fulfill":
                return "pretend the item was fulfilled."


        template = bottle.SimpleTemplate(_HTMLTemplateEnum.ITEM_PAGE())
        return template.render(item=item)

    def home_page(self):
        db = self._db
        item_list = [db[key] for key in db.keys()]
        template = bottle.SimpleTemplate(_HTMLTemplateEnum.HOME_PAGE())
        return template.render(items=item_list)

    def nfc_csv(self):
        """
        Produce a .csv file of URLS compatible with NXP Tag Writer
        """
        db = self._db
        item_list = [db[key] for key in db.keys()]

        urlparts = bottle.request.urlparts
        scheme = urlparts.scheme
        netloc = urlparts.netloc
        nfc_item_list = []
        for item in item_list:
            url = f"{scheme}://{netloc}/nfc/items/{item.reference}"
            name = repr(item.name)
            nfc_item_list.append((name, url))

        #bottle.response.content_type = 'text/plain; charset=UTF8'
        bottle.response.content_type = 'text/csv; charset=UTF8'
        return grocery_scanner.services.nfc_file_from_repo(
            nfc_item_list
        )

    def nfc_tag_redirect(self, redirect_url):
        """
        Redirect to whatever url is supplied. Arbitrary redirects are
        technically a vulnerability, but given the self-hosted service, not
        really a threat.
        """
        return bottle.redirect(redirect_url)

    def style(self):
        bottle.response.content_type = 'text/css; charset=UTF8'
        path = pathlib.Path("grocery_scanner/data/styles.css")
        return _HTMLTemplateEnum.STYLES_CSS()

    def markdown_grocery_list(self):
        """
        Produce a markdown-formatted grocery list, ideal for importing into
        Obsidian
        """
        db = self._db
        item_list = [db[key] for key in db.keys()]
        bottle.response.content_type = 'text/plain; charset=UTF8'
        formatter = "- [ ] [{name}]({url})".format
        lines = []
        for item in item_list:
            lines.append(formatter(name=item.name, url=item.url))
        items_str = "\n".join(lines)
        return items_str

    def logwatch(self):
        return bottle.SimpleTemplate(_HTMLTemplateEnum.LOGWATCH_PAGE()).render()

    def logstream(self):
        db = self._db
        item_list = [db[key] for key in db.keys()]
        bottle.response.content_type = "text/event-stream"
        bottle.response.cache_control = "no-cache"
        # Placeholder data
        raw_data = [f"data: {item.name}\n" for item in item_list]
        data = "".join(raw_data)
        data += "\n"
        yield data

    def cart(self):
        db = self._db
        secret = self._secret
        cookie_cart = bottle.request.get_cookie("cart", secret=secret) or dict()
        cart = {db.load(key): quantity for key, quantity in cookie_cart.items()}
        template = bottle.SimpleTemplate(_HTMLTemplateEnum.CART_PAGE())
        return template.render(cart=cart)

    def get_config(self):
        db = self._db
        item_list = [db[key] for key in db.keys()]
        config = configparser.ConfigParser()
        strio = io.StringIO()
        for item in item_list:
            config.add_section(item.reference)
            config[item.reference] = vars(item)
        config.write(strio)
        bottle.response.content_type = 'text/plain; charset=UTF8'
        return strio.getvalue()

    def make_app(self):
        """
        Creates a bottle.Bottle instance, assigns routes to it and returns it.
        """
        # The goal is for the entire API to be accessible via NFC tags/QR codes.
        # Therefore, most resources need to be accessible with GET
        app = bottle.Bottle()
        app.route("/", ["GET"], self.home_page)
        app.route("/items/<reference>", ["GET"], self.individual_item)
        app.route("/grocery_list.md", ["GET"], self.markdown_grocery_list)
        app.route("/nfc.csv", ["GET"], self.nfc_csv)
        app.route("/nfc<redirect_url:path>", ["GET"], self.nfc_tag_redirect)
        app.route("/styles.css", ["GET"], self.style)
        app.route("/logwatch", ["GET"], self.logwatch)
        app.route("/logstream", ["GET"], self.logstream)
        app.route("/cart", ["GET"], self.cart)
        app.route("/config.ini", ["GET"], self.get_config)
        return app


def read_items_from_markdown_str(raw_str):
    """
    Reads grocery items from a markdown-formatted list. The format is similar
    to how you'd create a checkbox in Obsidian:
    >>> item_format = "- [ ] [Item Name](https://item.url)"
    >>> item = next(read_items_from_markdown_str(item_format))
    >>> assert item.name == "Item Name"
    """
    identity_regex = re.compile(r"- \[[ x]\] ?\[(.*)\]\((.*)\)")
    for i, line in enumerate(raw_str.splitlines()):
        regex_match = identity_regex.search(line)
        if not regex_match:
            continue
        if regex_match:
            name, url = regex_match.groups()
        referential_name = name.lower()
        reference = re.sub(r"[^a-zA-Z0-9]", "_", referential_name)
        item = grocery_scanner.models.GroceryItem(reference, name, url)
        yield item


def main():
    args = get_args()

    config = configparser.ConfigParser()
    config.read(args.config_file)
    grocery_list_path = config.get("DEFAULT", "grocery_list_path")

    # I want the grocery data to be readable from some simple format. Not sure
    # if markdown or .csv would be easiest. Should probably support both.
    cls = grocery_scanner.models.GroceryItem
    csv_db = grocery_scanner.core.CSVRepository(cls)

    with open(grocery_list_path, "r") as f:
        for item in read_items_from_markdown_str(f.read()):
            csv_db.save(item)

    api = DB2WebAdapter(csv_db)
    app = api.make_app()

    server_start_time = time.perf_counter()
    server_proc = ServerProcess(app, host=args.address, port=args.port)
    server_proc.start()
    print(f"Server started in {time.perf_counter() - server_start_time}")
    browser_start_time = time.perf_counter()
    webbrowser.open(f"http://{args.address}:{args.port}")
    print(f"Browser started in {time.perf_counter() - browser_start_time}")

    while True:
        pass
    server_proc.terminate()


if __name__ == "__main__":
    main()
