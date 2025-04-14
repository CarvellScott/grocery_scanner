#!/usr/bin/env python3
import argparse
import configparser
import csv
import itertools
import json
import multiprocessing
import os
import pathlib
import re
import sys
import time
import webbrowser
import xml.etree.ElementTree as ET

import bottle

import grocery_scanner.core
import grocery_scanner.models
import grocery_scanner.services

_CSS_TEXT = """
body {
  max-width:767px;
  margin:40px auto;
  padding:0 10px;
  font:18px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", sans-serif, "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol", "Noto Color Emoji";
  color:#444
}
h1,
h2,
h3 {
  line-height:1.2
}
@media (prefers-color-scheme: dark) {
  body {
    color:#c9d1d9;
    background:#0d1117
  }
  a:link {
    color:#58a6ff
  }
  a:visited {
    color:#8e96f0
  }
}
"""

HOME_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="/styles.css">
</head>
<body>
    <div>
        If you are reading this, you're now able to access Carvell's
        random experiments by hostname instead of by ip address.
        And there are no cache issues.
    </div>
    <table>
        <tr>
            <th></th>
            <th>Item</th>
            <th>Link</th>
        </tr>
        % for item in items:
            <tr>
                <td><input type="checkbox"></td>
                <td>
                    <a href="/items/{{item.reference}}">{{item.name}}</a>
                </td>
                <td>
                    <a href={{item.url}}>Shop Online</a>
                </td>
            </tr>
        % end
    </table>
</body>
</html>
"""


ITEM_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="/styles.css">
</head>
<body>
    <div>
        Pretend that this is a page for {{item.name}}.
    </div>
    <form action="/cart/{{item.reference}}">
        <input type="number" id="quantity" name="quantity">
        <input type="submit" value="Add to cart">
    </form>
    <ul>
        <li>
            <a href="/items/{{item.reference}}?action=request"> Request </a>
        </li>
        <li>
            <a href="/nfc/items/{{item.reference}}"> Test NFC Redirect </a>
        </li>
        <li>
            <a href="{{item.url}}"> Shop Online</a>
    </ul>
</body>
</html>
"""

LOGWATCH_PAGE = """
<!DOCTYPE html>
<html>
    <head>
        <script>
            var es = new EventSource("logstream");
            es.onmessage = function(e) {
                document.getElementById("log").innerHTML = e.data;
            }
        </script>
    </head>
    <body>
        <pre id="log">No events yet.</pre>
    </body>
</html>
"""

CART_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="/styles.css">
</head>
<body>
    <h1>Cart</h1>
    <table>
        <tr>
            <th>Item</th>
            <th>URL</th>
        </tr>
        % for item, quantity in cart.items():
            <tr>
                <td>
                    {{quantity}} x <a href="/items/{{item.reference}}">{{item.name}}</a>
                </td>
                <td>
                    <a href={{item.url}} target="_blank">Shop Online</a>
                </td>
            </tr>
        % end
    </table>
</body>
</html>
"""

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
    args = parser.parse_args()
    return args


class DB2WebAdapter:
    def __init__(self, db):
        self._db = db

    def individual_item(self, reference):
        item = self._db.load(reference)
        secret = "bwah"
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


        template = bottle.SimpleTemplate(ITEM_PAGE)
        return template.render(item=item)

    def home_page(self):
        db = self._db
        item_list = [db[key] for key in db.keys()]
        template = bottle.SimpleTemplate(HOME_PAGE)
        return template.render(items=item_list)

    def nfc_csv(self):
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
        #return f"Redirecting you to {redirect_url}"
        return bottle.redirect(redirect_url)

    def style(self):
        bottle.response.content_type = 'text/css; charset=UTF8'
        return _CSS_TEXT

    def markdown_grocery_list(self):
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
        return bottle.SimpleTemplate(LOGWATCH_PAGE).render()

    def logstream(self):
        db = self._db
        item_list = [db[key] for key in db.keys()]
        bottle.response.content_type = "text/event-stream"
        bottle.response.cache_control = "no-cache"
        raw_data = [f"data: {item.name}\n" for item in item_list]
        data = "".join(raw_data)
        data += "\n"
        yield data

    def cart(self):
        db = self._db

        secret = "bwah"
        cookie_cart = bottle.request.get_cookie("cart", secret=secret) or dict()
        cart = {db.load(key): quantity for key, quantity in cookie_cart.items()}
        template = bottle.SimpleTemplate(CART_PAGE)
        return template.render(cart=cart)

    def get_config(self):
        db = self._db
        item_list = [db[key] for key in db.keys()]
        config = configparser.ConfigParser()
        import io
        strio = io.StringIO()
        for item in item_list:
            config.add_section(item.reference)
            config[item.reference] = vars(item)
        config.write(strio)
        bottle.response.content_type = 'text/plain; charset=UTF8'
        return strio.getvalue()


def read_items_from_markdown(markdown_filename):
    identity_regex = re.compile(r"- \[[ x]\] ?\[(.*)\]\((.*)\)")
    with open(markdown_filename, "r") as f:
        raw_data = f.read()
        for i, line in enumerate(raw_data.splitlines()):
            regex_match = identity_regex.search(line)
            if not regex_match:
                continue
            if regex_match:
                name, url = regex_match.groups()
            reference = f"{i:03}"
            item = grocery_scanner.models.GroceryItem(reference, name, url)
            yield item


def main():
    args = get_args()

    config = configparser.ConfigParser()
    config.read(args.config_file)

    cls = grocery_scanner.models.GroceryItem
    csv_db = grocery_scanner.core.CSVRepository(cls, "data.csv")

    for item in read_items_from_markdown("grocery_list.md"):
        csv_db.save(item)

    app = bottle.Bottle()
    api = DB2WebAdapter(csv_db)
    # The goal is for the entire API to be accessible via NFC tags/QR codes.
    # Therefore, most resources need to be accessible with GET
    app.route("/", ["GET"], api.home_page)
    app.route("/items/<reference>", ["GET"], api.individual_item)
    app.route("/grocery_list.md", ["GET"], api.markdown_grocery_list)
    app.route("/nfc.csv", ["GET"], api.nfc_csv)
    app.route("/nfc<redirect_url:path>", ["GET"], api.nfc_tag_redirect)
    app.route("/styles.css", ["GET"], api.style)
    app.route("/logwatch", ["GET"], api.logwatch)
    app.route("/logstream", ["GET"], api.logstream)
    app.route("/cart", ["GET"], api.cart)
    app.route("/config.ini", ["GET"], api.get_config)

    server_start_time = time.perf_counter()
    server_proc = ServerProcess(app, host="0.0.0.0", port=8080)
    server_proc.start()
    print(f"Server started in {time.perf_counter() - server_start_time}")
    browser_start_time = time.perf_counter()
    #webbrowser.open("http://localhost:8080")
    print(f"Browser started in {time.perf_counter() - browser_start_time}")

    while True:
        pass
    server_proc.terminate()


if __name__ == "__main__":
    main()
