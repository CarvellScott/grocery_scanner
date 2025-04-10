#!/usr/bin/env python3
import csv
import io

def nfc_file_from_repo(item_list):
    # This function converts the list of items into a format that can be used
    # with NXP Tag Writer (Android app) to write NFC tags in bulk.
    entries = list()
    for item_name, item_url in item_list:
        entry = {}
        entry["Type"] = "Link"
        entry["Content"] = item_url
        entry["URI type"] = "URL"
        entry["Description"] = item_name
        entry["Interaction counter"] = "no"
        entry["UID mirror"] = "no"
        entry["Interaction counter mirror"] = "no"
        entries.append(entry)
    str_obj = io.StringIO()
    writer = csv.DictWriter(str_obj, tuple(entry.keys()))
    writer.writeheader()
    for entry in entries:
        writer.writerow(entry)
    return str_obj.getvalue()

def main():
    pass

if __name__ == "__main__":
    main()

