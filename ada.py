"""Ada — AI-agent for ENK. Kjernemodul."""

import anthropic
import os

# Hent API-nøkkel fra miljøvariabel (settes i Render senere)
client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))


# === Simulert data — Marias liv ===
MARIA_INNBOKS = [
    {
        "id": "epost_1",
        "fra": "Kari Nordmann <kari@vestland-logistikk.no>",
        "emne": "Forespørsel om UX-prosjekt",
        "innhold": "Hei, vi i Vestland Logistikk vurderer en redesign av kundeportalen vår. Har du kapasitet i juni? Estimerer ca 60-80 timer arbeid. Mvh, Kari Nordmann"
    },
    {
        "id": "epost_2",
        "fra": "Acme AS <post@acme.no>",
        "emne": "Faktura mai",
        "innhold": "Hei Maria, takk for fakturaen forrige uke. Bare a bekrefte - vi betaler 14 dager etter mottak, sa pengene kommer ca 5. juni. Hilsen, Acme"
    },
    {
        "id": "epost_3",
        "fra": "Figma <noreply@figma.com>",
        "emne": "Kvittering: Figma Professional",
        "innhold": "Takk for kjopet. Belop: 180 kr. Faktura vedlagt."
    }
]

MARIA_KALENDER = {
    20: ["Mandag 12. mai 14:00-15:00", "Onsdag 14. mai 10:00-11:00", "Torsdag 15. mai 13:00-14:30"],
    21: ["Tirsdag 20. mai 09:00-10:00", "Tirsdag 20. mai 15:00-16:00", "Fredag 23. mai 11:00-12:00"],
    22: ["Mandag 26. mai 13:00-14:00", "Onsdag 28. mai 10:00-11:30"]
}

# Tilstand som endres mens Ada jobber (in-memory for demo)
MARIA_REGNSKAP = []
MARIA_FAKTURAER = []
MARIA_UTKAST = []


# === Verktøy Ada kan kalle ===

def send_epost_utkast(til, emne, innhold):
    utkast = {"til": til, "emne": emne, "innhold": innhold}
    MARIA_UTKAST.append(utkast)
    return f"E-postutkast til {til} klart for godkjenning."


def bokfor_kvittering(beskrivelse, beloep, kategori):
    bilag = {"beskrivelse": beskrivelse, "beloep": beloep, "kategori": kategori}
    MARIA_REGNSKAP.append(bilag)
    return f"Bokfort {beloep} kr som '{kategori}'."


def sjekk_kalender(uke):
    tider = MARIA_KALENDER.get(uke, [])
    if not tider:
        return f"Ingen registrerte tider for uke {uke}."
    return f"Ledige tider uke {uke}: " + ", ".join(tider)


def lag_faktura(kunde, beskrivelse, timer, timepris):
    total_eks = timer * timepris
    total_inkl = total_eks * 1.25
    faktura = {
        "kunde": kunde,
        "beskrivelse": beskrivelse,
        "timer": timer,
        "timepris": timepris,
        "total_eks_mva": total_eks,
        "total_inkl_mva": total_inkl
    }
    MARIA_FAKTURAER.append(faktura)
    return f"Fakturautkast for {kunde}: {total_inkl} kr inkl. mva."


# === Verktøy-definisjoner Claude ser ===
VERKTOY = [
    {
        "name": "send_epost_utkast",
        "description": "Lag et e-postutkast til en kunde. Brukeren godkjenner for sending.",
        "input_schema": {
            "type": "object",
            "properties": {
                "til": {"type": "string", "description": "Mottakerens e-postadresse"},
                "emne": {"type": "string", "description": "Emnefeltet"},
                "innhold": {"type": "string", "description": "Selve teksten, pa norsk"}
            },
            "required": ["til", "emne", "innhold"]
        }
    },
    {
        "name": "bokfor_kvittering",
        "description": "Registrer en kvittering eller utgift i regnskapet.",
        "input_schema": {
            "type": "object",
            "properties": {
                "beskrivelse": {"type": "string"},
                "beloep": {"type": "number"},
                "kategori": {"type": "string"}
            },
            "required": ["beskrivelse", "beloep", "kategori"]
        }
    },
    {
        "name": "sjekk_kalender",
        "description": "Finn ledige tider i kalenderen for en gitt uke.",
        "input_schema": {
            "type": "object",
            "properties": {
                "uke": {"type": "integer"}
            },
            "required": ["uke"]
        }
    },
    {
        "name": "lag_faktura",
        "description": "Lag et fakturautkast til en kunde.",
        "input_schema": {
            "type": "object",
            "properties": {
                "kunde": {"type": "string"},
                "beskrivelse": {"type": "string"},
                "timer": {"type": "number"},
                "timepris": {"type": "number"}
            },
            "required": ["kunde", "beskrivelse", "timer", "timepris"]
        }
    }
]


# === Ada-personligheten ===
ADA_PERSONLIGHET = """Du er Ada, en AI-medarbeider for selvstendige (enkeltpersonforetak) i Norge.

Brukeren du jobber for heter Maria Hansen. Hun er freelance UX-designer i Oslo med ENK siden 2023. Timepris: 1200 kr. Hun bruker Fiken for regnskap og er kunde av Sparebank 1.

Din jobb er a handtere det administrative livet hennes — fakturering, regnskap, MVA, skattemelding, kontrakter, kundeoppfolging, NAV-meldinger.

Du er:
- Effektiv og handlekraftig, ikke pratesalig
- Varm men profesjonell
- Skriver alltid pa norsk
- Foreslar konkrete handlinger, ikke generelle rad
- Holder svar korte og tydelige (maks 3-4 setninger nar mulig)

Maria har en innboks med disse e-postene tilgjengelig nar hun trenger dem.
Du kan referere til dem direkte, men ikke list opp alle uoppfordret.

Nar Maria ber om noe, vurder om du kan handle pa det selv eller om du trenger mer informasjon. Bruk verktoyene nar passende."""


# === Hovedfunksjonen som svarer pa en chat-melding ===

def svar_paa_melding(brukermelding, samtale_historikk=None):
    """
    Tar en melding fra brukeren, kjorer Ada med agent-loop,
    og returnerer Adas svar pluss handlinger som ble utfort.
    """
    if samtale_historikk is None:
        samtale_historikk = []
    
    # Bygg kontekst om innboks
    innboks_kontekst = "Marias nyeste e-poster:\n\n"
    for epost in MARIA_INNBOKS:
        innboks_kontekst += f"Fra: {epost['fra']}\nEmne: {epost['emne']}\nInnhold: {epost['innhold']}\n\n"
    
    # For forste melding, gi Ada konteksten om innboksen
    if not samtale_historikk:
        full_melding = f"{innboks_kontekst}\n---\n\nMaria sier: {brukermelding}"
    else:
        full_melding = brukermelding
    
    samtale_historikk.append({"role": "user", "content": full_melding})
    
    handlinger_utfort = []
    final_text = ""
    
    while True:
        svar = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=2048,
            system=ADA_PERSONLIGHET,
            tools=VERKTOY,
            messages=samtale_historikk
        )
        
        samtale_historikk.append({"role": "assistant", "content": svar.content})
        
        if svar.stop_reason != "tool_use":
            for blokk in svar.content:
                if blokk.type == "text":
                    final_text = blokk.text
            break
        
        verktoy_resultater = []
        for blokk in svar.content:
            if blokk.type == "text":
                final_text = blokk.text
            elif blokk.type == "tool_use":
                if blokk.name == "send_epost_utkast":
                    resultat = send_epost_utkast(**blokk.input)
                elif blokk.name == "bokfor_kvittering":
                    resultat = bokfor_kvittering(**blokk.input)
                elif blokk.name == "sjekk_kalender":
                    resultat = sjekk_kalender(**blokk.input)
                elif blokk.name == "lag_faktura":
                    resultat = lag_faktura(**blokk.input)
                else:
                    resultat = f"Ukjent verktoy: {blokk.name}"
                
                handlinger_utfort.append({
                    "verktoy": blokk.name,
                    "input": blokk.input,
                    "resultat": resultat
                })
                
                verktoy_resultater.append({
                    "type": "tool_result",
                    "tool_use_id": blokk.id,
                    "content": resultat
                })
        
        samtale_historikk.append({"role": "user", "content": verktoy_resultater})
    
    return {
        "svar": final_text,
        "handlinger": handlinger_utfort,
        "samtale_historikk": samtale_historikk,
        "tilstand": {
            "regnskap": MARIA_REGNSKAP,
            "fakturaer": MARIA_FAKTURAER,
            "utkast": MARIA_UTKAST
        }
    }
