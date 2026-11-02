#!/usr/bin/env python3
"""
German Warehouse Data Generator for LagerPilot-Qwen
Generates compact, highly realistic, legally accurate training data for goods receipt audit & § 377 HGB compliance.
Optimized for ultra-fast edge fine-tuning (< 600 tokens per sequence).
"""

import json
import random
import os

SUPPLIERS = [
    {"name": "Würth Industrie Service GmbH & Co. KG", "city": "Bad Mergentheim"},
    {"name": "Festo SE & Co. KG", "city": "Esslingen"},
    {"name": "Klüber Lubrication München SE", "city": "München"},
    {"name": "Schaeffler Technologies AG & Co. KG", "city": "Herzogenaurach"},
    {"name": "Phoenix Contact GmbH & Co. KG", "city": "Blomberg"},
    {"name": "WAGO GmbH & Co. KG", "city": "Minden"},
    {"name": "Hoffmann Group SE", "city": "München"},
    {"name": "Thyssenkrupp Schulte GmbH", "city": "Essen"},
    {"name": "Freudenberg Sealing Technologies", "city": "Weinheim"},
    {"name": "SICK AG", "city": "Waldkirch"}
]

ARTICLES = [
    {"art_nr": "SCHR-DIN912-M8-30", "bezeichnung": "Zylinderschraube DIN 912 M8x30", "base_unit": "Stück", "vpe_types": [("Karton", 100), ("VPE", 50)]},
    {"art_nr": "DICHT-OR-40X3-NBR70", "bezeichnung": "O-Ring 40x3 mm NBR 70", "base_unit": "Stück", "vpe_types": [("Beutel", 25), ("Pack", 100)]},
    {"art_nr": "SCHM-SYN-400ML", "bezeichnung": "Hochtemp-Schmierfett 400ml", "base_unit": "Stück", "vpe_types": [("Karton", 12)]},
    {"art_nr": "KUGL-6204-2RSH", "bezeichnung": "Rillenkugellager 6204-2RSH SKF", "base_unit": "Stück", "vpe_types": [("Karton", 10)]},
    {"art_nr": "KLEM-WAGO-221-413", "bezeichnung": "WAGO Klemme 3-Leiter 221-413", "base_unit": "Stück", "vpe_types": [("Schachtel", 50)]},
    {"art_nr": "KBL-OELFLEX-3G15", "bezeichnung": "Steuerleitung Ölflex 3G1,5mm²", "base_unit": "Meter", "vpe_types": [("Ring", 50)]},
    {"art_nr": "PNEU-VENTIL-52-G18", "bezeichnung": "5/2-Wege-Magnetventil 1/8", "base_unit": "Stück", "vpe_types": [("Karton", 1)]},
    {"art_nr": "REIN-IND-ISOPROP-10L", "bezeichnung": "Reiniger Isopropanol UN 1219", "base_unit": "Liter", "vpe_types": [("Fass", 200)]}
]

def generate_sample(sample_id):
    scenario_type = random.choice([
        "clean_match",
        "clean_match_vpe",
        "under_delivery",
        "over_delivery",
        "unit_confusion",
        "aliud_wrong_part",
        "damaged_goods",
        "batch_mhd_violation",
        "hazardous_quarantine"
    ])

    supp = random.choice(SUPPLIERS)
    ls_nr = f"LS-{random.randint(10000, 99999)}"
    po_nr = f"PO-{random.randint(1000, 9999)}"
    date_str = "02.11.2026"

    art = random.choice(ARTICLES)
    vpe_name, vpe_factor = random.choice(art["vpe_types"])

    if scenario_type == "clean_match":
        order_qty = random.randint(10, 200)
        deliv_qty = order_qty
        deliv_unit = art["base_unit"]
        ramp_note = "Ware unversehrt."
        lot = f"CH-{random.randint(100, 999)}"
        audit_status = "FREIGABE"
        diff = 0
        status_pos = "OK"
        detail = "Lieferung entspricht Bestellung."
        ruege = False
        ruege_text = None
        instruction = "Ware vollständig. Sofort Bestandsbuchung durchführen."
        mvt = "101"

    elif scenario_type == "clean_match_vpe":
        boxes = random.randint(2, 10)
        deliv_qty = boxes
        deliv_unit = vpe_name
        order_qty = boxes * vpe_factor
        ramp_note = f"{boxes} {vpe_name} originalverpackt."
        lot = f"LOT-{random.randint(1000, 9999)}"
        audit_status = "FREIGABE"
        diff = 0
        status_pos = "OK"
        detail = f"VPE umgerechnet: {boxes} {vpe_name} * {vpe_factor} = {order_qty} {art['base_unit']}."
        ruege = False
        ruege_text = None
        instruction = f"Menge geprüft ({boxes} {vpe_name} = {order_qty} {art['base_unit']}). Freigabe erteilt."
        mvt = "101"

    elif scenario_type == "under_delivery":
        order_qty = 100
        deliv_qty = 70
        deliv_unit = art["base_unit"]
        ramp_note = f"Fehlmenge: Nur {deliv_qty} von {order_qty} {art['base_unit']} erhalten."
        lot = f"CH-{random.randint(100, 999)}"
        audit_status = "MÄNGELRÜGE_ERFORDERLICH"
        diff = -30
        status_pos = "MINDERLIEFERUNG"
        detail = f"Mindermenge von 30 {art['base_unit']} festgestellt."
        ruege = True
        ruege_text = f"MÄNGELRÜGE § 377 HGB: Zu LS {ls_nr} (Bestellung {po_nr}) rügen wir eine Mindermenge von 30 {art['base_unit']} bei Art. {art['art_nr']}. Wir fordern Nachlieferung binnen 5 Werktagen gem. § 439 BGB."
        instruction = f"Fehlmenge vermerken. Nur {deliv_qty} {art['base_unit']} buchen, Speditionsschein mit Mindervermerk quittieren."
        mvt = "101"

    elif scenario_type == "over_delivery":
        order_qty = 50
        deliv_qty = 75
        deliv_unit = art["base_unit"]
        ramp_note = f"Übermenge: {deliv_qty} statt {order_qty} {art['base_unit']}."
        lot = f"CH-{random.randint(100, 999)}"
        audit_status = "MÄNGELRÜGE_ERFORDERLICH"
        diff = 25
        status_pos = "UEBERLIEFERUNG"
        detail = f"Unautorisierte Überlieferung von +25 {art['base_unit']}."
        ruege = True
        ruege_text = f"ABWEICHUNGSRÜGE § 377 HGB: Zu LS {ls_nr} wurden 75 statt 50 {art['base_unit']} Art. {art['art_nr']} geliefert. Mehrlieferung von 25 {art['base_unit']} wird bis Klärung gesperrt."
        instruction = f"Nur 50 {art['base_unit']} vereinnahmen. Überschüssige 25 {art['base_unit']} auf Sperrlagerplatz stellen."
        mvt = "103"

    elif scenario_type == "unit_confusion":
        boxes = 5
        deliv_qty = boxes
        deliv_unit = "Karton"
        order_qty = 50
        actual_pcs = boxes * 15 # 75 pcs
        lot = f"CH-{random.randint(100, 999)}"
        ramp_note = "Kartonaufdruck: 15 Stk/Karton (= 75 Stk), bestellt waren 50 Stk."
        audit_status = "MÄNGELRÜGE_ERFORDERLICH"
        diff = actual_pcs - order_qty
        status_pos = "UEBERLIEFERUNG"
        detail = f"VPE-Abweichung: 5 Kartons à 15 Stk = 75 Stk statt bestellter 50 Stk (+25 Stk)."
        ruege = True
        ruege_text = f"MÄNGELRÜGE § 377 HGB: Gebindegröße weicht ab (5 Kartons à 15 Stk = 75 Stk vs 50 Stk bestellt). Wir rügen Übermenge von 25 Stk."
        instruction = "VPE-Konflikt! Nicht als 5 Stück buchen. Auf Klärplatz verbringen."
        mvt = "103"

    elif scenario_type == "aliud_wrong_part":
        order_qty = 20
        deliv_qty = 20
        deliv_unit = art["base_unit"]
        wrong_art = art["art_nr"] + "-REV2"
        ramp_note = "Falscher Artikel geliefert. Typenschild stimmt nicht."
        lot = f"CH-{random.randint(100, 999)}"
        audit_status = "MÄNGELRÜGE_ERFORDERLICH"
        diff = -order_qty
        status_pos = "FALSCHLIEFERUNG"
        detail = f"Aliud-Lieferung gem. § 434 BGB: {wrong_art} geliefert statt {art['art_nr']}."
        ruege = True
        ruege_text = f"MÄNGELRÜGE § 377 HGB (ALIUD): Zu LS {ls_nr} wurde Falschartikel {wrong_art} statt {art['art_nr']} geliefert. Wir verweigern die Annahme und fordern Nachlieferung binnen 4 Werktagen."
        instruction = "Falschlieferung! Nicht einlagern. Ware in Quarantäne stellen."
        mvt = "122"

    elif scenario_type == "damaged_goods":
        order_qty = 40
        deliv_qty = 40
        deliv_unit = art["base_unit"]
        ramp_note = "Transportschaden: Kartons eingedrückt und durchnässt. Frachtbrief gegengezeichnet."
        lot = f"CH-{random.randint(100, 999)}"
        audit_status = "MÄNGELRÜGE_ERFORDERLICH"
        diff = 0
        status_pos = "BESCHAEDIGT"
        detail = "Erheblicher Transportschaden festgestellt. CMR-Vermerk liegt vor."
        ruege = True
        ruege_text = f"MÄNGELRÜGE § 377 HGB / CMR: Zu LS {ls_nr} rügen wir schweren Transportschaden (Nässe/Stauchung). Quittierung unter Vorbehalt auf Frachtbrief erfolgt. Wir fordern Ersatzlieferung."
        instruction = "Transportschaden! Fotos machen, Sperretikett kleben, Quarantänelager."
        mvt = "103"

    elif scenario_type == "batch_mhd_violation":
        order_qty = 10
        deliv_qty = 10
        deliv_unit = art["base_unit"]
        mhd = "20.11.2026"
        ramp_note = "MHD-Unterschreitung: Restlaufzeit unter 30 Tage (Vertrag: 6 Monate)."
        lot = f"CH-EXP-{random.randint(10, 99)}"
        audit_status = "MÄNGELRÜGE_ERFORDERLICH"
        diff = 0
        status_pos = "CHARGENFEHLER"
        detail = "MHD unterschreitet Mindestrestlaufzeit."
        ruege = True
        ruege_text = f"MÄNGELRÜGE § 377 HGB: Zu LS {ls_nr} unterschreitet Charge {lot} (MHD {mhd}) die vertragliche Mindestrestlaufzeit. Ware wird gesperrt."
        instruction = "MHD-Fehler! Annahme verweigert, Quarantäneplatz."
        mvt = "103"

    else: # hazardous_quarantine
        order_qty = 2
        deliv_qty = 2
        deliv_unit = "Fass"
        ramp_note = "Gefahrgut UN 1219 leckt am Spundloch, Sicherheitsdatenblatt fehlt."
        lot = f"LOT-HAZ-{random.randint(10, 99)}"
        audit_status = "SPERRE"
        diff = 0
        status_pos = "BESCHAEDIGT"
        detail = "Gefahrgutsperre: Undichtigkeit & fehlendes Sicherheitsdatenblatt (ADR/REACH)."
        ruege = True
        ruege_text = f"SICHERHEITSSPERRE & RÜGE NACH § 377 HGB: Gefahrgutlieferung zu LS {ls_nr} weist Leckage auf und Sicherheitsdatenblatt fehlt. Sendung im externen Quarantänebereich isoliert."
        instruction = "GEFAHRGUT-ALARM! Sofort in Auffangwanne isolieren, Sicherheitsbeauftragten rufen."
        mvt = "105"

    input_text = f"""LIEFERSCHEIN:
Lieferant: {supp['name']}
LS-Nr: {ls_nr} | Datum: {date_str} | PO: {po_nr}
Pos 1: {art['art_nr'] if scenario_type != 'aliud_wrong_part' else wrong_art} - {deliv_qty} {deliv_unit} - Charge: {lot}

ERP-BESTELLUNG:
PO: {po_nr} | Pos 1: {art['art_nr']} - {order_qty} {art['base_unit']}

RAMPEN-NOTIZ:
{ramp_note}"""

    output_payload = {
        "audit_status": audit_status,
        "beleg_info": {"lieferschein_nr": ls_nr, "bestell_nr": po_nr, "lieferant": supp["name"], "datum": date_str},
        "positions_abgleich": [
            {
                "pos": 1,
                "bestell_art_nr": art["art_nr"],
                "lieferschein_art_nr": art["art_nr"] if scenario_type != 'aliud_wrong_part' else wrong_art,
                "bezeichnung": art["bezeichnung"],
                "bestellmenge": order_qty,
                "bestell_einheit": art["base_unit"],
                "gelieferte_menge_basis": deliv_qty * vpe_factor if deliv_unit == vpe_name else (actual_pcs if scenario_type == 'unit_confusion' else deliv_qty),
                "mengendifferenz": diff,
                "charge_ist": lot,
                "status": status_pos,
                "mangel_detail": detail
            }
        ],
        "hgb_377_bewertung": {"ruege_notwendig": ruege, "begruendung": detail if ruege else "Lieferung ordnungsgemäß."},
        "maengelruege_schreiben": ruege_text,
        "rampen_anweisung_kurz": instruction,
        "erp_buchungs_payload": {"bewegungsart": mvt, "buchungsmenge": deliv_qty if scenario_type in ["clean_match", "under_delivery"] else (order_qty if scenario_type == "over_delivery" else 0)}
    }

    return {
        "id": f"sample_{sample_id:04d}",
        "messages": [
            {"role": "user", "content": input_text.strip()},
            {"role": "assistant", "content": json.dumps(output_payload, ensure_ascii=False, indent=2)}
        ]
    }

def main():
    os.makedirs("/Users/jon/Documents/privateProjects/lagerAI/data", exist_ok=True)
    random.seed(42)

    print("Generating German Warehouse § 377 HGB dataset (Fast Edge Format)...")
    train_samples = [generate_sample(i) for i in range(1, 101)]
    val_samples = [generate_sample(i) for i in range(101, 121)]

    train_path = "/Users/jon/Documents/privateProjects/lagerAI/data/train_dataset.json"
    val_path = "/Users/jon/Documents/privateProjects/lagerAI/data/val_dataset.json"

    with open(train_path, "w", encoding="utf-8") as f:
        json.dump(train_samples, f, ensure_ascii=False, indent=2)

    with open(val_path, "w", encoding="utf-8") as f:
        json.dump(val_samples, f, ensure_ascii=False, indent=2)

    print(f"Generated {len(train_samples)} training samples at {train_path}")
    print(f"Generated {len(val_samples)} validation samples at {val_path}")

if __name__ == "__main__":
    main()
