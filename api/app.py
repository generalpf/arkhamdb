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
		result = conn.execute("SELECT neighbourhoodid FROM location WHERE _id = ?", (location_id,)).fetchone()
		conn.execute("UPDATE neighbourhoodcard SET discarded = 0 WHERE neighbourhoodid = ?", (result["neighbourhoodid"],))
		result = conn.execute("SELECT * FROM locationencounter le INNER JOIN neighbourhoodcard nc ON nc._id = le.cardid AND nc.discarded = 0 WHERE le.locationid = ? ORDER BY RANDOM() LIMIT 1", (location_id,)).fetchone()
	conn.execute("UPDATE neighbourhoodcard SET discarded = 1 WHERE _id = ?", (result["cardid"],))
	conn.close()
	j = json.dumps(result)
	return Response(
		response=j,
		status=200,
		mimetype="application/json")
