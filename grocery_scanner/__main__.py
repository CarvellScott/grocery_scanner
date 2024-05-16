#!/usr/bin/env python3
import argparse
import configparser
import csv
import multiprocessing
import os
import pathlib
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
  max-width:650px;
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
    <link rel="stylesheet" href="styles.css">
</head>
<body>
    <div>
        If you are reading this, you're now able to access Carvell's
        random experiments by hostname instead of by ip address.
        And there are no cache issues.
    </div>
    <table>
        <tr>
            <th>Item</th>
            <th>Shop Online</th>
        </tr>
        % for item in items:
            <tr>
                <td>
                    <a href="/items/{{item.name}}">{{item.name}}</a>
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


def individual_item(item):
    action = bottle.request.params.get("action")
    return (
        f"Pretend that this is a page for {item}. And you're trying to {action}:"
        f"/items/<item>?action=request",
        f"/items/<item>?action=cancel",
        f"/items/<item>?action=fulfill",
    )


def style():
    bottle.response.content_type = 'text/css; charset=UTF8'
    return _CSS_TEXT


def home_page(item_list):
    template = bottle.SimpleTemplate(HOME_PAGE)
    return template.render(css_text=_CSS_TEXT, items=item_list)


def nfc_csv(item_list):
    urlparts = bottle.request.urlparts
    scheme = urlparts.scheme
    netloc = urlparts.netloc
    nfc_endpoint_prefix = f"{scheme}://{netloc}/items"

    bottle.response.content_type = 'text/plain; charset=UTF8'
    bottle.response.content_type = 'text/csv; charset=UTF8'
    return grocery_scanner.services.nfc_file_from_repo(nfc_endpoint_prefix,
                                                          item_list)


def nfc_tag_redirect(path):
    return bottle.redirect(path)


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config-file",
        type=pathlib.Path,
        required=not os.getenv("GROCERY_SCANNER_CONFIG"),
        default=os.getenv("GROCERY_SCANNER_CONFIG")
    )
    args = parser.parse_args()
    return args


def main():
    args = get_args()

    config = configparser.ConfigParser()
    config.read(args.config_file)
    db = grocery_scanner.core.ShelveRepository()
    csv_db = grocery_scanner.core.CSVRepository()
    for item_name, item_url in config["DEFAULT"].items():
        reference = item_name
        item = grocery_scanner.models.GroceryItem(reference, item_name, item_url)
        db.save(item)
        csv_db.save(item)

    csv_db.dump()
    item_list = [db[key] for key in db.keys()]
    app = bottle.Bottle()
    # The goal is for the entire API to be accessible via NFC tags/QR codes.
    app.route("/", ["GET"], lambda item_list=item_list: home_page(item_list))
    app.route("/items/<item>", ["GET"], individual_item)
    app.route("/nfc.csv", ["GET"], lambda item_list=item_list: nfc_csv(item_list))
    app.route("/nfc<path:path>", ["GET"], nfc_tag_redirect)
    app.route("/styles.css", ["GET"], style)

    server_start_time = time.perf_counter()
    server_proc = ServerProcess(app, host="0.0.0.0", port=8080)
    server_proc.start()
    print(f"Server started in {time.perf_counter() - server_start_time}")
    browser_start_time = time.perf_counter()
    webbrowser.open("http://localhost:8080")
    print(f"Browser started in {time.perf_counter() - browser_start_time}")

    while True:
        pass
    server_proc.terminate()

if __name__ == "__main__":
    main()

