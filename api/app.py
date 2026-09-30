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
    world = conn.execute(
        "SELECT red, green, blue, yellow FROM otherworld WHERE _id = ?",
        (otherworld_id,)).fetchone()
    if world is None:
        conn.close()
        return Response(
            response="otherworld not found",
            status=404,
            mimetype="text/plain")
    if not any(world.values()):
        conn.close()
        return Response(
            response="otherworld has no colours, so no encounter can be drawn for it",
            status=400,
            mimetype="text/plain")
    # without a matching card in the session's deck, the draw loop below would never end
    match = conn.execute("""SELECT 1 FROM otherworldcard owc
                            INNER JOIN session_expansion se ON se.expansionid = owc.expansionid
                                AND se.sessionid = ?
                            WHERE (owc.red = 1 AND ? = 1)
                                OR (owc.green = 1 AND ? = 1)
                                OR (owc.blue = 1 AND ? = 1)
                                OR (owc.yellow = 1 AND ? = 1)
                            LIMIT 1""",
                         (sessionid, world["red"], world["green"], world["blue"], world["yellow"],)).fetchone()
    if match is None:
        conn.close()
        return Response(
            response="no otherworld cards in this session's expansions match the otherworld's colours",
            status=404,
            mimetype="text/plain")

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
    # every card should have an encounter for "Other", so this is bad data rather than a bad request
    return Response(
        response=f"otherworld card {found_card_id} has no encounter for this otherworld or for Other",
        status=500,
        mimetype="text/plain")


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
    request_json = request.get_json(silent=True)
    if not isinstance(request_json, dict):
        return Response(
            response="request body must be a JSON object",
            status=400,
            mimetype="text/plain")
    if "title" not in request_json:
        return Response(
            response="title is required",
            status=400,
            mimetype="text/plain")
    if "expansions" not in request_json:
        return Response(
            response="expansions is required",
            status=400,
            mimetype="text/plain")
    title = request_json["title"]
    expansions = request_json["expansions"]
    # bool is a subclass of int, so rule it out explicitly
    if not isinstance(expansions, list) or \
            not all(isinstance(id, int) and not isinstance(id, bool) for id in expansions):
        return Response(
            response="expansions must be an array of expansion ids",
            status=400,
            mimetype="text/plain")
    duplicate_ids = sorted({id for id in expansions if expansions.count(id) > 1})
    if duplicate_ids:
        return Response(
            response=f"duplicate expansion ids: {', '.join(str(id) for id in duplicate_ids)}",
            status=400,
            mimetype="text/plain")

    conn = get_db_connection()
    valid_ids = {row["_id"] for row in conn.execute("SELECT _id FROM expansion").fetchall()}
    invalid_ids = sorted(set(expansions) - valid_ids)
    if invalid_ids:
        conn.close()
        return Response(
            response=f"invalid expansion ids: {', '.join(str(id) for id in invalid_ids)}",
            status=400,
            mimetype="text/plain")

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
