extends Node

# Backend communication layer - talks to Python HTTP server on localhost
# This is the bridge between Godot (game) and Python (data/API)

const BASE_URL = "http://127.0.0.1:8766"
var token: String = ""
var state: Dictionary = {}

signal state_loaded(state: Dictionary)
signal request_completed(endpoint: String, result: Dictionary)
signal request_failed(endpoint: String, error: String)

func _ready():
	# Try to load state on startup
	load_state()

func load_state() -> void:
	var http = HTTPRequest.new()
	add_child(http)
	http.request_completed.connect(_on_state_loaded)
	var err = http.request(BASE_URL + "/api/state")
	if err != OK:
		push_error("Failed to connect to backend: " + str(err))

func _on_state_loaded(result: int, response_code: int, headers: PackedStringArray, body: PackedByteArray) -> void:
	if response_code == 200:
		var json = JSON.new()
		var parse_err = json.parse(body.get_string_from_utf8())
		if parse_err == OK:
			state = json.get_data()
			token = state.get("token", "")
			emit_signal("state_loaded", state)
		else:
			push_error("Failed to parse state JSON")
	else:
		push_error("Backend returned code: " + str(response_code))

func post(endpoint: String, data: Dictionary = {}) -> void:
	var http = HTTPRequest.new()
	add_child(http)
	http.request_completed.connect(func(result, code, headers, body):
		if code == 200:
			var json = JSON.new()
			if json.parse(body.get_string_from_utf8()) == OK:
				emit_signal("request_completed", endpoint, json.get_data())
			else:
				emit_signal("request_failed", endpoint, "Parse error")
		else:
			var json = JSON.new()
			var msg = "HTTP " + str(code)
			if json.parse(body.get_string_from_utf8()) == OK:
				msg = json.get_data().get("error", msg)
			emit_signal("request_failed", endpoint, msg)
	)
	var headers = ["Content-Type: application/json", "X-Local-Token: " + token]
	var body = JSON.stringify(data)
	http.request(BASE_URL + endpoint, headers, HTTPClient.METHOD_POST, body)

func get(endpoint: String) -> void:
	var http = HTTPRequest.new()
	add_child(http)
	http.request_completed.connect(func(result, code, headers, body):
		if code == 200:
			var json = JSON.new()
			if json.parse(body.get_string_from_utf8()) == OK:
				emit_signal("request_completed", endpoint, json.get_data())
			else:
				emit_signal("request_failed", endpoint, "Parse error")
		else:
			emit_signal("request_failed", endpoint, "HTTP " + str(code))
	)
	http.request(BASE_URL + endpoint)
