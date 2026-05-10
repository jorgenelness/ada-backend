"""Web-server for Ada — tar imot meldinger og svarer."""

from flask import Flask, request, jsonify
from flask_cors import CORS
from ada import svar_paa_melding, MARIA_INNBOKS, MARIA_REGNSKAP, MARIA_FAKTURAER, MARIA_UTKAST

app = Flask(__name__)
CORS(app)  # Tillat at landingssiden snakker med oss

# Lagrer samtale-historikk per okt (in-memory, nullstilles ved omstart)
SAMTALER = {}


@app.route("/")
def home():
    return jsonify({"status": "Ada lever", "versjon": "0.1"})


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.json
    melding = data.get("melding", "")
    okt_id = data.get("okt_id", "default")
    
    if not melding:
        return jsonify({"feil": "Ingen melding mottatt"}), 400
    
    # Hent samtale-historikk for denne okta
    historikk = SAMTALER.get(okt_id, [])
    
    # La Ada svare
    resultat = svar_paa_melding(melding, historikk)
    
    # Lagre oppdatert historikk
    SAMTALER[okt_id] = resultat["samtale_historikk"]
    
    return jsonify({
        "svar": resultat["svar"],
        "handlinger": resultat["handlinger"],
        "tilstand": resultat["tilstand"]
    })


@app.route("/api/innboks", methods=["GET"])
def innboks():
    return jsonify(MARIA_INNBOKS)


@app.route("/api/tilstand", methods=["GET"])
def tilstand():
    return jsonify({
        "regnskap": MARIA_REGNSKAP,
        "fakturaer": MARIA_FAKTURAER,
        "utkast": MARIA_UTKAST
    })


@app.route("/api/nullstill", methods=["POST"])
def nullstill():
    """Nullstill alle data for ny demo-okt."""
    MARIA_REGNSKAP.clear()
    MARIA_FAKTURAER.clear()
    MARIA_UTKAST.clear()
    SAMTALER.clear()
    return jsonify({"status": "Nullstilt"})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
