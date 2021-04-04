from flask import Flask, jsonify, request, abort
from flask_cors import CORS
import requests

from calc import CharacterStats, Comp, CharacterStatFactory
from pps.sch import SchPps

app = Flask(__name__)
CORS(app)

@app.route('/calc_damage', methods=["POST"])
def main():
    """Calculates damage based on input. Accepts and returns JSON. JSON format is as follows:
    'player': Object
        'weaponDamage': int
        'mainStat': int
        'det': int
        'crit': int
        'dh': int
        'speed': int
        'ten': int
        'pie': int
    'job': string
    'comp': Array
    """
    data = request.get_json()

    if not data:
        return "abort", abort(400)

    player_data = data['player']

    try:
        my_job = CharacterStatFactory.create_job(data['job'])[0]
    except KeyError:
        return f"Currently {data['job']} is not supported."

    player = CharacterStats(
        my_job,
        player_data['weaponDamage'],
        player_data['mainStat'],
        player_data['det'],
        player_data['crit'],
        player_data['dh'],
        player_data['speed'],
        player_data['ten'],
        player_data['pie']
    )
    my_sch_pps = SchPps()
    potency = my_sch_pps.get_pps(player)
    try:
        comp_jobs = [CharacterStatFactory.create_job(comp_job)[0] for comp_job in data['comp']]
    except KeyError:
        return "A job was not supported in that team comp."

    my_comp = Comp(comp_jobs)

    dps = round(player.calc_damage(potency, my_comp), 2)
    return jsonify({"dps": dps})


@app.route('/calc_damage/etro', methods=["POST"])
def etro_main():
    """Calculates damage, given a gearsetID from Etro. Should check database to see if gearset exist first.
    JSON format:
    'job': String,
    'comp': Array,
    'etro_id': String,
    """

    data = request.get_json()

    # Check comp first before making request
    if not data:
        return "abort", abort(400)
    try:
        comp_jobs = [CharacterStatFactory.create_job(comp_job)[0] for comp_job in data['comp']]
    except KeyError:
        return "An unsupported job was found in the team composition."

    my_comp = Comp(comp_jobs)

    player_job_data = CharacterStatFactory.create_job(data['job'])

    # TODO: Check internal database to see if cached before request

    try:
        etro_data = requests.get("/".join(["https://etro.gg/api/gearsets", data["etro_id"]])).json()
    except requests.exceptions.RequestException:
        return "There was an error making the etro request"

    etro_stats = etro_data["totalParams"]
    eq_stats = {stat["name"]: stat["value"] for stat in etro_stats}

    # For Etro sets that are non-tanks
    if "TEN" not in eq_stats:
        eq_stats["TEN"] = 0

    # Making speed job-agnostic
    if "SPS" in eq_stats:
        eq_stats["SPEED"] = eq_stats["SPS"]
    else:
        eq_stats["SPEED"] = eq_stats["SKS"]

    player = CharacterStats(
        player_job_data[0],
        eq_stats["Weapon Damage"],
        eq_stats[player_job_data[1]],
        eq_stats["DET"],
        eq_stats["CRT"],
        eq_stats["DH"],
        eq_stats["SPEED"],
        eq_stats["TEN"],
        eq_stats["PIE"],
    )

    my_sch_pps = SchPps()
    potency = my_sch_pps.get_pps(player)

    dps = player.calc_damage(potency, my_comp)
    return jsonify({"dps": dps})


if __name__ == "__main__":
    app.run()