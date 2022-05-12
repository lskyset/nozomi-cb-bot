import csv
import os
import sqlite3
from itertools import zip_longest
from operator import itemgetter

from .. import config as cfg


def togspread(path, ws, gs_sheet):
    content = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            content.append(row)
    ws.clear()
    gs_sheet.values_update(
        ws.title, params={"valueInputOption": "USER_ENTERED"}, body={"values": content}
    )


def get_csv_table_data(table, c, r=False):
    row_name = [
        itemgetter(1)(col)
        for col in c.execute(f"PRAGMA table_info({table})").fetchall()
    ]
    data = None
    if r:
        data = [row_name] + list(
            reversed(c.execute(f"SELECT * from {table}").fetchall())
        )
    else:
        data = [row_name] + c.execute(f"SELECT * from {table}").fetchall()
    return data


def data_csv(name):
    conn = sqlite3.connect(f"{name}.db")
    c = conn.cursor()
    table_list = ["members_data"]
    path = f"{name}_data.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for table in table_list:
            writer.writerows(get_csv_table_data(table, c))
            writer.writerow("")
        writer.writerow(
            ["Last updated at", cfg.jst_time().strftime("%m/%d/%Y %H:%M:%S"), "JST"]
        )
    return path


def chat_log_csv(name):
    conn = sqlite3.connect(f"{name}.db")
    c = conn.cursor()
    path = name + "_chat_log.csv"
    chat_logs = get_csv_table_data("chat_log", c, r=True)
    damage_logs = get_csv_table_data("damage_log", c, r=True)
    data = []
    for a, b in list(zip_longest(chat_logs, damage_logs, fillvalue="")):
        data.append([*a, "", *b])
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(data)
    return path


def upload_db(drive, path):
    folderName = "cb-database"
    folders = drive.ListFile(
        {
            "q": f"title='{folderName}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        }
    ).GetList()
    for folder in folders:
        if folder["title"] == folderName:
            file_list = drive.ListFile(
                {"q": "'{}' in parents and trashed=false".format(folder["id"])}
            ).GetList()
            file = None
            for drive_file in file_list:
                if drive_file["title"] == path:
                    file = drive_file
                    break
            if not file:
                file = drive.CreateFile({"parents": [{"id": folder["id"]}]})
            file.SetContentFile(path)
            file.Upload()
            return True
    return False


def download_db(name, drive):
    folderName = "cb-database"
    folders = drive.ListFile(
        {
            "q": "title='"
            + folderName
            + "' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        }
    ).GetList()
    for folder in folders:
        if folder["title"] == folderName:
            file_list = drive.ListFile(
                {"q": "'{}' in parents and trashed=false".format(folder["id"])}
            ).GetList()
            for file in file_list:
                if file["title"] == name:
                    file.GetContentFile(name)
                    return True
    return False


def update_db(drive, clan):
    data_path = data_csv(clan.name)
    chat_log_path = chat_log_csv(clan.name)
    togspread(data_path, clan.gs_db, clan.gs_sheet)
    togspread(chat_log_path, clan.gs_chat_log, clan.gs_sheet)
    upload_db(drive, f"{clan.name}.db")
    os.remove(data_path)
    os.remove(chat_log_path)


def replace_num(num):
    if num[-1] in ["k", "m"]:
        return int(float(num[:-1]) * 10 ** (3 + 3 * (num[-1] == "m")))
    return int(float(num))
