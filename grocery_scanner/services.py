#!/usr/bin/env python3
import doctest
import re


import grocery_scanner.models
import grocery_scanner.utils

def change_item_status(repo, item_id, action):
    item = repo[item_id]
    if action == "request":
        item.status = "requested"
    if action == "fulfill":
        item.status = "OK"
    repo.save(item)

def generate_nfc_csv_from_repo(repo, url_prefix):
    repo_items = [repo[key] for key in repo.keys()]
    nfc_item_list = []
    for item in repo_items:
        url = f"{url_prefix}/{item.reference}"
        name = item.name
        nfc_item_list.append((name, url))

    file_data = grocery_scanner.utils.make_nfc_csv_data(nfc_item_list)
    return file_data

def generate_markdown_item_list(repo):
    item_list = [repo[key] for key in repo.keys()]
    formatter = "- [ ] [{name}]({url})".format
    lines = []
    for item in item_list:
        lines.append(formatter(name=item.name, url=item.url))
    items_str = "\n".join(lines)
    return items_str

def define_item_type(repo, grocery_item):
    pass



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

def add_items_from_markdown(repo, raw_str):
    for item in read_items_from_markdown_str():
        repo.save(item)


def add_container(repo, item_container):
    pass


def main():
    pass

if __name__ == "__main__":
    doctest.testmod()
    main()

