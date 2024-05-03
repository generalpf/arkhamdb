from datetime import datetime, timezone
from flask import Flask, Response, request
import json
import sqlite3
import uuid

app = Flask(__name__)


def get_db_connection():
    conn = sqlite3.connect("../arkhamdb.sqlite3", autocommit=True)
    conn.execute("PRAGMA foreign_keys=1")
    # to get dictionaries out of the result
    conn.row_factory = lambda c, r: dict(
        [(col[0], r[idx]) for idx, col in enumerate(c.description)])
    return conn


def get_session_id() -> int:
    if "sessionid" not in request.headers:
        raise HttpException(400, "sessionid is required")
    conn = get_db_connection()
    result = conn.execute(
        "SELECT _id FROM session WHERE sessionid = ?",
        (request.headers["sessionid"],)).fetchone()
    conn.close()
    if result is None:
        raise HttpException(401, "sessionid is invalid")
    return result["_id"]


def table_as_response(table: str):
    conn = get_db_connection()
    result = conn.execute(f"SELECT * FROM {table}").fetchall()
    conn.close()
    j = json.dumps(result)
    return Response(
        response=j,
        status=200,
        mimetype="application/json")


def row_as_response(table: str, id: int):
    conn = get_db_connection()
    result = conn.execute(
        f"SELECT * FROM {table} WHERE _id = ?",
        (id,)).fetchone()
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
    try:
        sessionid = get_session_id()
    except HttpException as e:
        return Response(
            response=e.message,
            status=e.status_code)

    conn = get_db_connection()
    query = """ SELECT le.* FROM locationencounter le
                INNER JOIN neighbourhoodcard nc ON nc._id = le.cardid
                INNER JOIN session_expansion se ON se.expansionid = nc.expansionid
                    AND se.sessionid = ?
                LEFT OUTER JOIN session_neighbourhoodcard snc ON snc.neighbourhoodcardid = nc._id
                    AND snc.discarded = 1
                    AND snc.sessionid = ?
                WHERE le.locationid = ?
                    AND snc.neighbourhoodcardid IS NULL
                ORDER BY RANDOM()
                LIMIT 1"""
    result = conn.execute(query, (sessionid, sessionid, location_id,)).fetchone()
    if result is None:
        conn.execute("""DELETE FROM session_neighbourhoodcard
                        WHERE sessionid = ?
                            AND discarded = 1
                            AND neighbourhoodcardid IN (
                                SELECT nc._id FROM neighbourhoodcard nc
                                INNER JOIN neighbourhood n ON n._id = nc.neighbourhoodid
                                INNER JOIN location l ON l.neighbourhoodid = n._id
                                    AND l._id = ?
                            )""", (sessionid, location_id,))
        result = conn.execute(query, (sessionid, sessionid, location_id,)).fetchone()
        if result is None:
            return Response(status=404)
    conn.execute(
        "INSERT INTO session_neighbourhoodcard(neighbourhoodcardid, sessionid, discarded) VALUES(?, ?, ?)",
        (result["cardid"], sessionid, 1,))
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
    try:
        sessionid = get_session_id()
    except HttpException as e:
        return Response(
            response=e.message,
            status=e.status_code)

    conn = get_db_connection()
    found_card_id = None
    while found_card_id is None:
        query = """ SELECT owc._id AS card_id,
                        owc.red AS card_red, owc.green AS card_green, owc.blue AS card_blue, owc.yellow AS card_yellow,
                        ow.red AS world_red, ow.green AS world_green, ow.blue AS world_blue, ow.yellow AS world_yellow
                    FROM otherworldcard owc
                    INNER JOIN session_expansion se ON se.expansionid = owc.expansionid
                        AND se.sessionid = ?
                    LEFT OUTER JOIN session_otherworldcard sowc ON sowc.otherworldcardid = owc._id
                        AND sowc.discarded = 1
                        AND sowc.sessionid = ?
                    JOIN otherworld ow ON ow._id = ?
                    WHERE sowc.otherworldcardid IS NULL
                    ORDER BY RANDOM()
                    LIMIT 5"""
        result = conn.execute(query, (sessionid, sessionid, otherworld_id,))
        if result is None:
            # shuffle
            continue
        discarded_cards = []
        while True:
            row = result.fetchone()
            if row is None:
                if not discarded_cards:
                    # shuffle the whole deck
                    conn.execute("DELETE FROM session_otherworldcard WHERE discarded = 1 AND sessionid = ?", (sessionid,))
                break
            discarded_cards.append(row["card_id"])
            if row["card_red"] + row["world_red"] == 2 or \
                    row["card_green"] + row["world_green"] == 2 or \
                    row["card_blue"] + row["world_blue"] == 2 or \
                    row["card_yellow"] + row["world_yellow"] == 2:
                found_card_id = row["card_id"]
                break
        # discard all the discarded cards
        args = [(sessionid, id, 1,) for id in discarded_cards]
        conn.executemany("INSERT INTO session_otherworldcard(sessionid, otherworldcardid, discarded) VALUES(?, ?, ?)", args)

    result = conn.execute("""   SELECT owe.*, ow.title
                                FROM otherworldencounter owe
                                INNER JOIN otherworld ow ON ow._id = owe.otherworldid
                                WHERE owe.otherworldcardid = ?
                                ORDER BY otherworldid""", (found_card_id,)).fetchall()
    conn.close()
    for encounter in result:
        if encounter["otherworldid"] == otherworld_id or encounter["title"] == "Other":
            j = json.dumps(encounter)
            return Response(
                response=j,
                status=200,
                mimetype="application/json")


def draw_standard_discardable(table: str):
    try:
        sessionid = get_session_id()
    except HttpException as e:
        return Response(
            response=e.message,
            status=e.status_code)

    conn = get_db_connection()
    query = f"""SELECT t.* FROM {table} t
                INNER JOIN session_expansion se ON se.expansionid = t.expansionid
                    AND se.sessionid = ?
                LEFT OUTER JOIN session_{table} st ON st.{table}id = t._id
                    AND st.discarded = 1
                    AND st.sessionid = ?
                WHERE st.{table}id IS NULL
                ORDER BY RANDOM()
                LIMIT 1"""
    result = conn.execute(query, (sessionid, sessionid,)).fetchone()
    if result is None:
        conn.execute(f"DELETE FROM session_{table} WHERE discarded = 1 AND sessionid = ?", (sessionid,))
        result = conn.execute(query, (sessionid, sessionid,)).fetchone()
    if result is None:
        return Response(status=404)
    conn.execute(
        f"INSERT INTO session_{table}({table}id, sessionid, discarded) VALUES(?, ?, ?)",
        (result["_id"], sessionid, 1,))
    conn.close()
    j = json.dumps(result)
    return Response(
        response=j,
        status=200,
        mimetype="application/json")


@app.route("/reckoning/draw", methods=["POST"])
def draw_reckoning_card():
    return draw_standard_discardable("reckoningcard")


@app.route("/exhibitencounter/draw", methods=["POST"])
def draw_exhibitencounter_card():
    return draw_standard_discardable("exhibitencountercard")


@app.route("/cultencounter/draw", methods=["POST"])
def draw_cultencounter_card():
    return draw_standard_discardable("cultencountercard")


@app.route("/session/create", methods=["POST"])
def session_create():
    sessionid = str(uuid.uuid4())
    sourceip = request.remote_addr
    if "title" not in request.form:
        return Response(
            response="title is required",
            status=400,
            mimetype="application/json")
    if "expansions" not in request.form:
        return Response(
            response="expansions is required",
            status=400,
            mimetype="application/json")
    title = request.form["title"]
    expansions = request.form.getlist("expansions")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO session(sessionid, sourceip, title, created) VALUES(?, ?, ?, ?)",
        (sessionid, sourceip, title, datetime.now(timezone.utc)))
    _id = cursor.lastrowid
    args = [(_id, id,) for id in expansions]
    conn.executemany("INSERT INTO session_expansion(sessionid, expansionid) VALUES(?, ?)", args)
    conn.close()
    j = json.dumps({"sessionid": sessionid})
    return Response(
        response=j,
        status=201,
        mimetype="application/json")


class HttpException(Exception):
    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
