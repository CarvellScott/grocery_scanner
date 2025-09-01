#!/usr/bin/env python3
import argparse
import configparser
import enum
import importlib.resources
import io
import os
import pathlib
import re
import subprocess
import sys
import uuid

import bottle

import grocery_scanner.core
import grocery_scanner.models
import grocery_scanner.services


class _HTMLTemplateEnum(enum.Enum):
    HOME_PAGE = "static/home.html"
    ITEM_PAGE = "static/item.html"
    LOGWATCH_PAGE = "static/logwatch.html"
    CART_PAGE = "static/cart.html"
    STYLES_CSS = "static/styles.css"

    def __call__(self):
        data = None
        path = pathlib.Path(self.value)

        files = importlib.resources.files("grocery_scanner")
        path = files.joinpath(self.value)
        return path.read_bytes()


class BottleAdapter:
    def __init__(self, repo):
        self._repo = repo
        self._secret = str(uuid.uuid4())

    def individual_item(self, reference):
        # TODO: Replace this with something that doesn't require the user to
        # take action.
        item = self._repo.load(reference)
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
        repo = self._repo
        item_list = [repo[key] for key in repo.keys()]
        template = bottle.SimpleTemplate(_HTMLTemplateEnum.HOME_PAGE())
        return template.render(items=item_list)

    def nfc_csv(self):
        """
        Produce a .csv file of URLS compatible with NXP Tag Writer
        """

        urlparts = bottle.request.urlparts
        scheme = urlparts.scheme
        netloc = urlparts.netloc
        url_prefix = f"{scheme}://{netloc}/nfc/items"

        file_data = generate_nfc_csv_from_repo(self._repo, url_prefix)
        #bottle.response.content_type = 'text/plain; charset=UTF8'
        bottle.response.content_type = 'text/csv; charset=UTF8'
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
        return generate_markdown_item_list(self._repo)

    def logwatch(self):
        return bottle.SimpleTemplate(_HTMLTemplateEnum.LOGWATCH_PAGE()).render()

    def logstream(self):
        bottle.response.content_type = "text/event-stream"
        bottle.response.cache_control = "no-cache"
        command = ["top", "-b", "-n", "1", "-p", str(os.getpid())]
        data = subprocess.check_output(command, universal_newlines=True)

        raw_data = [f"data: {_}\n" for _ in data.splitlines()]
        data = "".join(raw_data)
        data += "\n"
        yield data

    def cart(self):
        repo = self._repo
        secret = self._secret
        cookie_cart = bottle.request.get_cookie("cart", secret=secret) or dict()
        cart = {repo.load(key): quantity for key, quantity in cookie_cart.items()}
        template = bottle.SimpleTemplate(_HTMLTemplateEnum.CART_PAGE())
        return template.render(cart=cart)

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
        app.route("/items/<reference>", ["GET"], self.individual_item)
        app.route("/grocery_list.md", ["GET"], self.markdown_grocery_list)
        app.route("/nfc.csv", ["GET"], self.nfc_csv)
        app.route("/nfc<redirect_url:path>", ["GET"], self.nfc_tag_redirect)
        app.route("/styles.css", ["GET"], self.style)
        app.route("/logwatch", ["GET"], self.logwatch)
        app.route("/logstream", ["GET"], self.logstream)
        app.route("/cart", ["GET"], self.cart)
        app.route("/config.ini", ["GET"], self.get_config)
        app.route("/grocery-scanner-server.pyz", ["GET"], self.get_executable)
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
        grocery_defs.read(args.grocery_definitions)

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
