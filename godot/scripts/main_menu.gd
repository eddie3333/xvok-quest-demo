extends Control

@onready var continue_btn = $MenuButtons/ContinueBtn
@onready var roster_btn = $MenuButtons/RosterBtn
@onready var quests_btn = $MenuButtons/QuestsBtn
@onready var vault_btn = $MenuButtons/VaultBtn
@onready var arena_btn = $MenuButtons/ArenaBtn
@onready var settings_btn = $MenuButtons/SettingsBtn
@onready var guild_label = $GuildLabel

var state: Dictionary = {}

func _ready():
	# Connect to backend
	Backend.state_loaded.connect(_on_state_loaded)
	Backend.request_completed.connect(_on_request_completed)
	Backend.request_failed.connect(_on_request_failed)
	
	# Connect button signals
	continue_btn.pressed.connect(_on_continue)
	roster_btn.pressed.connect(_on_roster)
	quests_btn.pressed.connect(_on_quests)
	vault_btn.pressed.connect(_on_vault)
	arena_btn.pressed.connect(_on_arena)
	settings_btn.pressed.connect(_on_settings)
	
	# Load state
	Backend.load_state()

func _on_state_loaded(s: Dictionary) -> void:
	state = s
	guild_label.text = s.get("guild_name", "EXODUS") + " Guild"
	# Update button text based on state
	continue_btn.text = "Continue (" + str(s.get("artist", {}).get("name", "Manager")) + ")"

func _on_request_completed(endpoint: String, result: Dictionary) -> void:
	pass

func _on_request_failed(endpoint: String, error: String) -> void:
	push_error("Request to " + endpoint + " failed: " + error)

func _on_continue() -> void:
	print("Continue pressed")

func _on_roster() -> void:
	print("Roster pressed")

func _on_quests() -> void:
	print("Quests pressed")

func _on_vault() -> void:
	print("Vault pressed")

func _on_arena() -> void:
	print("Arena pressed")

func _on_settings() -> void:
	print("Settings pressed")
