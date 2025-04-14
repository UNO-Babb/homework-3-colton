# HexRush.py
# Name: Colton Janes
# Date: 04/13/2025
# Assignment: Homework 3

from flask import Flask, render_template, request, jsonify
from markupsafe import Markup
import random

app = Flask(__name__)

#game structure
tiles = [
    {"id": 1, "resource": "wood", "number": 8, "settlements": [], "contents": []},
    {"id": 2, "resource": "ore", "number": 6, "settlements": [], "contents": []},
    {"id": 3, "resource": "wheat", "number": 4, "settlements": [], "contents": []},
    {"id": 4, "resource": "brick", "number": 5, "settlements": [], "contents": []},
    {"id": 5, "resource": "wood", "number": 9, "settlements": [], "contents": []},
    {"id": 6, "resource": "desert", "number": 7, "settlements": [], "contents": []},
    {"id": 7, "resource": "wheat", "number": 10, "settlements": [], "contents": []},
    {"id": 8, "resource": "ore", "number": 11, "settlements": [], "contents": []},
    {"id": 9, "resource": "wood", "number": 3, "settlements": [], "contents": []},
    {"id": 10, "resource": "brick", "number": 6, "settlements": [], "contents": []},
]

players = {
    1: {"name": "Player 1", "color": "red", "resources": {"wood": 0, "brick": 0, "wheat": 0, "ore": 0}, "points": 0},
    2: {"name": "Player 2", "color": "blue", "resources": {"wood": 0, "brick": 0, "wheat": 0, "ore": 0}, "points": 0},
}

current_player = 1
rolled_this_turn = False

setup_rolls = {1: None, 2: None}
game_phase = "setup"  #setup, placement, main
placement_order = []
placement_index = 0
event_log = []

#Flask routes

@app.route('/')
def index():
    return render_template("hexrush.html", tiles=tiles, players=players,
                           current_player=current_player, setup_rolls=setup_rolls,
                           game_phase=game_phase, placement_index=placement_index,
                           placement_order=placement_order, event_log=event_log)

@app.route('/setup_roll', methods=["POST"])
def setup_roll():
    global setup_rolls, game_phase, placement_order, current_player

    if setup_rolls[current_player] is not None:
        return jsonify({
            "message": "You already rolled.",
            "game_phase": game_phase,
            "current_player": current_player
        })

    roll = random.randint(1, 6) + random.randint(1, 6)
    setup_rolls[current_player] = roll
    event_log.append(f"{players[current_player]['name']} rolled {roll} in setup.")

    if setup_rolls[1] is not None and setup_rolls[2] is not None:
        if setup_rolls[1] > setup_rolls[2]:
            placement_order[:] = [1, 2, 2, 1, 1, 2, 2, 1]
        elif setup_rolls[2] > setup_rolls[1]:
            placement_order[:] = [2, 1, 1, 2, 2, 1, 1, 2]

        else:
            setup_rolls[1], setup_rolls[2] = None, None
            event_log.append("Tie in setup rolls. Players must roll again.")
            return jsonify({"message": "Tie! Roll again.", "game_phase": game_phase})
        
        game_phase = "placement"
        current_player = placement_order[0]
        event_log.append("Players will now place 4 starting settlements each.")

    else:
        current_player = 2 if current_player == 1 else 1

    return jsonify({"roll": roll, "message": f"You rolled: {roll}"})

@app.route('/place_starting_settlement', methods=["POST"])
def place_starting_settlement():
    global placement_index, current_player, game_phase

    data = request.json
    tile_id = data.get("tile_id")
    tile = next((t for t in tiles if t["id"] == tile_id), None)

    if not tile or current_player in tile["settlements"]:
        return jsonify({"success": False, "message": "Invalid tile or already settled."})

    tile["settlements"].append(current_player)
    tile["contents"].append(f"Player {current_player}")
    players[current_player]["points"] += 1

    #Grant 1 resource if tile has a valid resource type
    resource = tile["resource"]
    if resource != "desert":
        players[current_player]["resources"][resource] += 1
        event_log.append(f"{players[current_player]['name']} received 1 {resource} for starting on Tile {tile_id}.")

    event_log.append(f"{players[current_player]['name']} placed a starting settlement on Tile {tile_id}.")

    placement_index += 1
    if placement_index < len(placement_order):
        current_player = placement_order[placement_index]
    else:
        game_phase = "main"
        current_player = 1

    return jsonify({"success": True, "tile_id": tile_id})

@app.route('/roll_dice', methods=["POST"])
def roll_dice():
    global current_player, rolled_this_turn, game_phase
    if game_phase != "main":
        return jsonify({"roll": None, "message": "Game not started."})
    if rolled_this_turn:
        return jsonify({"roll": None, "message": "You already rolled this turn."})

    rolled_this_turn = True
    roll = random.randint(1, 6) + random.randint(1, 6)
    event_log.append(f"{players[current_player]['name']} rolled {roll}.")

    for tile in tiles:
        if tile["number"] == roll and tile["resource"] != "desert":
            for owner in tile["settlements"]:
                players[owner]["resources"][tile["resource"]] += 1

    return jsonify({"roll": roll})

@app.route('/build_settlement', methods=["POST"])
def build_settlement():
    global current_player, game_phase
    if game_phase != "main":
        return jsonify({"success": False, "message": "You can’t build settlements yet."})

    data = request.json
    tile_id = data.get("tile_id")
    tile = next((t for t in tiles if t["id"] == tile_id), None)

    if not tile or current_player in tile["settlements"]:
        return jsonify({"success": False, "message": "Invalid move or already settled."})

    cost = {"wood": 1, "brick": 1, "wheat": 1, "ore": 1}
    resources = players[current_player]["resources"]

    for r in cost:
        if resources[r] < cost[r]:
            return jsonify({"success": False, "message": "Not enough resources."})

    for r in cost:
        resources[r] -= cost[r]

    tile["settlements"].append(current_player)
    tile["contents"].append(f"Player {current_player}")
    players[current_player]["points"] += 1
    event_log.append(f"{players[current_player]['name']} built a settlement on Tile {tile_id}.")

    if players[current_player]["points"] >= 10:
        event_log.append(f"{players[current_player]['name']} wins the game!")
        return jsonify({"success": True, "winner": players[current_player]["name"]})

    return jsonify({"success": True})

@app.route('/end_turn', methods=["POST"])
def end_turn():
    global current_player, rolled_this_turn
    event_log.append(f"{players[current_player]['name']} ended their turn.")
    current_player = 2 if current_player == 1 else 1
    rolled_this_turn = False
    return jsonify({"current_player": current_player})

@app.route('/reset', methods=["POST"])
def reset_game():
    global players, tiles, current_player, rolled_this_turn
    global setup_rolls, game_phase, placement_index, placement_order, event_log

    current_player = 1
    rolled_this_turn = False
    setup_rolls = {1: None, 2: None}
    game_phase = "setup"
    placement_order = []
    placement_index = 0
    event_log = []

    for p in players:
        players[p]["resources"] = {"wood": 0, "brick": 0, "wheat": 0, "ore": 0}
        players[p]["points"] = 0

    for tile in tiles:
        tile["settlements"] = []
        tile["contents"] = []

    return jsonify({"success": True})

@app.route('/save', methods=["POST"])
def save_game():
    with open("game_save.txt", "w") as f:
        #Game phase and current turn
        f.write(f"Phase: {game_phase}\n")
        f.write(f"Turn: {players[current_player]['name']}\n")
        f.write(f"Placement Index: {placement_index}\n")
        f.write(f"Player 1 Points: {players[1]['points']}\n")
        f.write(f"Player 2 Points: {players[2]['points']}\n")
        f.write("Setup Rolls:\n")
        f.write(f"Player 1: {setup_rolls[1]}\n")
        f.write(f"Player 2: {setup_rolls[2]}\n")

        #Resources
        f.write("Resources:\n")
        for pid in players:
            res = players[pid]["resources"]
            res_str = ", ".join(f"{k}={v}" for k, v in res.items())
            f.write(f"Player {pid}: {res_str}\n")

        #Tile contents
        f.write("\nTiles:\n")
        for tile in tiles:
            if tile["contents"]:
                f.write(f"{tile['id']}: {', '.join(tile['contents'])}\n")

        #Event log
        f.write("\nEvent Log:\n")
        for entry in event_log:
            f.write(entry + "\n")

    return jsonify({"success": True})

@app.route("/load", methods=["POST"])
def load_game():
    global game_phase, current_player, placement_index
    global players, tiles, event_log, setup_rolls, placement_order

    try:
        with open("game_save.txt", "r") as f:
            lines = f.readlines()

        section = ""
        event_log.clear()
        setup_rolls[1] = None
        setup_rolls[2] = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if line.endswith(":") and not line.startswith("Player"):
                section = line[:-1]
                continue

            if section == "Phase":
                game_phase = line.split(": ")[1]
            elif section == "Turn":
                current_player = int(line.split(" ")[1])
            elif section == "Placement Index":
                placement_index = int(line.split(": ")[1])
            elif section == "Player 1 Points":
                players[1]["points"] = int(line.split(": ")[1])
            elif section == "Player 2 Points":
                players[2]["points"] = int(line.split(": ")[1])
            elif section == "Setup Rolls":
                pass  # no action, just a header
            elif section == "Resources":
                if line.startswith("Player"):
                    pid = int(line.split(":")[0].split(" ")[1])
                    parts = line.split(": ")[1].split(", ")
                    for item in parts:
                        k, v = item.split("=")
                        players[pid]["resources"][k] = int(v)
            elif section == "Tiles":
                tid, content = line.split(": ")
                tile = next((t for t in tiles if str(t["id"]) == tid), None)
                tile["contents"] = [c.strip() for c in content.split(",")]
                tile["settlements"] = []
                if "Player 1" in tile["contents"]:
                    tile["settlements"].append(1)
                if "Player 2" in tile["contents"]:
                    tile["settlements"].append(2)
            elif section == "Event Log":
                event_log.append(line)
            elif section.startswith("Player") and "Setup Rolls" in lines:
                # Catch setup rolls even if they show up like: Player 1: 8
                pid = int(line.split(":")[0].split(" ")[1])
                setup_rolls[pid] = int(line.split(": ")[1])

        #Recalculate placement_order based on setup rolls
        if setup_rolls[1] is not None and setup_rolls[2] is not None:
            if setup_rolls[1] > setup_rolls[2]:
                placement_order[:] = [1, 2, 2, 1, 1, 2, 2, 1]
            elif setup_rolls[2] > setup_rolls[1]:
                placement_order[:] = [2, 1, 1, 2, 2, 1, 1, 2]

        #Set correct player in placement phase
        if game_phase == "placement":
            current_player = placement_order[placement_index]

        return jsonify({"success": True})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

#Game tile renderer

@app.context_processor
def utility_processor():
    def render_tile(tile):
        emoji_map = {
            "wood": "🌲",
            "brick": "🧱",
            "wheat": "🌾",
            "ore": "⛰️",
            "desert": "🏜️"
        }
        resource = emoji_map.get(tile["resource"], "?")
        num = tile["number"]
        settlements = tile["settlements"]
        display = f"<div class='tile' onclick='handleTileClick({tile['id']})'>"
        display += f"{resource}<br>{num}<br><div class='settlement'>"
        if 1 in settlements:
            display += "🔴"
        if 2 in settlements:
            display += "🔵"
        display += "</div></div>"
        return Markup(display)
    return dict(render_tile=render_tile)

if __name__ == "__main__":
    app.run(debug=True)