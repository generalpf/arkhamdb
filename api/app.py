import sqlite3
import json
from flask import Flask, Response

app = Flask(__name__)

def get_db_connection():
    conn = sqlite3.connect("../arkhamdb.sqlite3", autocommit=True)
    # to get dictionaries out of the result
    conn.row_factory = lambda c, r: dict([(col[0], r[idx]) for idx, col in enumerate(c.description)])
    return conn

def table_as_response(table: str) -> str:
    conn = get_db_connection()
    result = conn.execute(f"SELECT * FROM {table}").fetchall()
    conn.close()
    j = json.dumps(result)
    return Response(
        response=j,
        status=200,
        mimetype="application/json")

def row_as_response(table: str, id: int) -> str:
    conn = get_db_connection()
    result = conn.execute(f"SELECT * FROM {table} WHERE _id = ?", (id,)).fetchone()
    conn.close()
    if result is None:
        return Response(status=404)
    j = json.dumps(result)
    return Response(
        response=j,
        status=200,
        mimetype="application/json")

@app.route("/expansion")
def expansion_index():
    return table_as_response("expansion")

@app.route("/expansion/<int:expansion_id>")
def expansion_get(expansion_id: int):
    return row_as_response("expansion", expansion_id)

@app.route("/board")
def board_index():
    return table_as_response("board")

@app.route("/board/<int:board_id>")
def board_get(board_id: int):
    return row_as_response("board", board_id)

@app.route("/location")
def location_index():
    return table_as_response("location")

@app.route("/location/<int:location_id>")
def location_get(location_id: int):
    return row_as_response("location", location_id)

@app.route("/location/<int:location_id>/draw", methods=["POST"])
def draw_location_card(location_id: int):
    conn = get_db_connection()
    result = conn.execute("SELECT * FROM locationencounter le INNER JOIN neighbourhoodcard nc ON nc._id = le.cardid AND nc.discarded = 0 WHERE le.locationid = ? ORDER BY RANDOM() LIMIT 1", (location_id,)).fetchone()
    if result is None:
        conn.execute("UPDATE neighbourhoodcard SET discarded = 0 WHERE neighbourhoodid = (SELECT neighbourhoodid FROM location WHERE _id = ?)", (location_id,))
        result = conn.execute("SELECT * FROM locationencounter le INNER JOIN neighbourhoodcard nc ON nc._id = le.cardid AND nc.discarded = 0 WHERE le.locationid = ? ORDER BY RANDOM() LIMIT 1", (location_id,)).fetchone()
    conn.execute("UPDATE neighbourhoodcard SET discarded = 1 WHERE _id = ?", (result["cardid"],))
    conn.close()
    j = json.dumps(result)
    return Response(
        response=j,
        status=200,
        mimetype="application/json")

@app.route("/otherworld")
def otherworld_index():
    return table_as_response("otherworld")

@app.route("/otherworld/<int:otherworld_id>")
def otherworld_get(otherworld_id: int):
    return row_as_response("otherworld", otherworld_id)

@app.route("/otherworld/<int:otherworld_id>/draw", methods=["POST"])
def draw_otherworld_card(otherworld_id: int):
    conn = get_db_connection()
    found_card_id = None
    while found_card_id is None:
        query = """ SELECT owc._id AS card_id,
                    owc.red AS card_red, owc.green AS card_green, owc.blue AS card_blue, owc.yellow AS card_yellow,
                    ow.red AS world_red, ow.green AS world_green, ow.blue AS world_blue, ow.yellow AS world_yellow
                    FROM otherworldcard owc
                    JOIN otherworld ow ON ow._id = ?
                    WHERE owc.discarded = 0
                    ORDER BY random()
                    LIMIT 5"""
        result = conn.execute(query, (otherworld_id,))
        if result is None:
            # shuffle
            continue
        discarded_cards = []
        while True:
            row = result.fetchone()
            if row is None:
                if not discarded_cards:
                    # shuffle the whole deck
                    conn.execute("UPDATE otherworldcard SET discarded = 0")
                break
            discarded_cards.append(row["card_id"])
            if row["card_red"] + row["world_red"] == 2 or \
                    row["card_green"] + row["world_green"] == 2 or \
                    row["card_blue"] + row["world_blue"] == 2 or \
                    row["card_yellow"] + row["world_yellow"] == 2:
                found_card_id = row["card_id"]
                break
        # discard all the discarded cards
        in_clause = ", ".join(str(id) for id in discarded_cards)
        conn.execute(f"UPDATE otherworldcard SET discarded = 1 WHERE _id IN ({in_clause})")
    result = conn.execute("SELECT owe.*, ow.title FROM otherworldencounter owe INNER JOIN otherworld ow ON ow._id = owe.otherworldid WHERE owe.otherworldcardid = ? ORDER BY otherworldid", (found_card_id,)).fetchall()
    conn.close()
    for encounter in result:
        if encounter["otherworldid"] == otherworld_id or encounter["title"] == "Other":
            j = json.dumps(encounter)
            return Response(
                response=j,
                status=200,
                mimetype="application/json")
