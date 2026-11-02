#!/usr/bin/env python3
"""
LagerPilot ERP Connector
Translates LagerPilot-Qwen audit decisions into standard enterprise ERP payloads:
- SAP S/4HANA / ECC 6.0 (BAPI_GOODSMVT_CREATE / MIGO Movement Types 101, 103, 122)
- proALPHA / Microsoft Dynamics 365 Business Central XML
- Standard Industrial CSV / WMS Flat File
"""

from datetime import datetime
from typing import Dict, Any, List

class ErpConnector:
    """
    Enterprise ERP Integration Service for German Warehouse Logistics.
    """

    @staticmethod
    def generate_sap_bapi_payload(audit_result: Dict[str, Any], delivery_note_id: str = "LS-UNKNOWN", po_number: str = "PO-UNKNOWN") -> Dict[str, Any]:
        """
        Generates SAP BAPI_GOODSMVT_CREATE structure.
        Mapping:
          - FREIGABE                 -> Movement Type 101 (Wareneingang ins freie Lager)
          - MÄNGELRÜGE_ERFORDERLICH  -> Movement Type 103 (Wareneingang in den gesperrten Bestand / Klärplatz)
          - SPERRE                   -> Movement Type 122 (Rücklieferung an den Lieferanten / Annahme verweigert)
        """
        data = audit_result.get("data", {})
        status = data.get("audit_status", "MÄNGELRÜGE_ERFORDERLICH")
        today = datetime.now().strftime("%Y%m%d")

        move_type_map = {
            "FREIGABE": "101",
            "MÄNGELRÜGE_ERFORDERLICH": "103",
            "SPERRE": "122"
        }
        bapi_move_type = move_type_map.get(status, "103")

        # Extract items
        items = data.get("artikel_abgleich", [])
        if not items and "mangelruege" in data:
            mr = data["mangelruege"]
            if isinstance(mr, dict):
                items = [{
                    "artikel_nummer": mr.get("artNr") or mr.get("artikel_nummer", "MATERIAL-01"),
                    "geliefert_menge": mr.get("geliefert_menge") or mr.get("bestellmenge", 1),
                    "einheit": mr.get("einheit", "ST"),
                    "charge": mr.get("charge", "")
                }]

        bapi_items = []
        for idx, item in enumerate(items, start=1):
            bapi_items.append({
                "LINE_ID": f"{idx:04d}",
                "MATERIAL": item.get("artikel_nummer", "UNKNOWN"),
                "PLANT": "1000",          # German default plant
                "STGE_LOC": "0001" if bapi_move_type == "101" else "0099", # 0099 = Klärplatz / Sperrlager
                "MOVE_TYPE": bapi_move_type,
                "PO_NUMBER": po_number,
                "PO_ITEM": f"{idx * 10:05d}",
                "ENTRY_QNT": item.get("geliefert_menge", 0),
                "ENTRY_UOM": item.get("einheit", "ST"),
                "BATCH": item.get("charge", ""),
                "ITEM_TEXT": f"§377 HGB: {status} - {data.get('mangel_detail', 'LagerPilot Audit')[:40]}"
            })

        return {
            "BAPI_NAME": "BAPI_GOODSMVT_CREATE",
            "GOODSMVT_HEADER": {
                "PSTNG_DATE": today,
                "DOC_DATE": today,
                "REF_DOC_NO": delivery_note_id,
                "BILL_OF_LADING": f"CMR-{today}",
                "HEADER_TXT": f"LagerPilot §377 HGB Audit: {status}"
            },
            "GOODSMVT_CODE": {"GM_CODE": "01"}, # 01 = MB01 / MIGO Goods Receipt for PO
            "GOODSMVT_ITEM": bapi_items,
            "HGB_COMPLIANCE": {
                "status": status,
                "movement_code": bapi_move_type,
                "storage_location": "HOCHREGAL_FREI" if bapi_move_type == "101" else "KLÄRPLATZ_GESPERRT",
                "hgb_notice_required": data.get("hgb_377_bewertung", {}).get("ruege_notwendig", False)
            }
        }

    @staticmethod
    def generate_proalpha_xml(audit_result: Dict[str, Any], delivery_note_id: str = "LS-UNKNOWN") -> str:
        """
        Generates proALPHA XML Dispatch Advice Import.
        """
        data = audit_result.get("data", {})
        status = data.get("audit_status", "FREIGABE")
        today = datetime.now().strftime("%Y-%m-%d")

        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<proALPHA_Wareneingang Version="7.1">
  <BelegKopf>
    <LieferscheinNr>{delivery_note_id}</LieferscheinNr>
    <EingangsDatum>{today}</EingangsDatum>
    <AuditStatus>{status}</AuditStatus>
    <HGB_377_Gesperrt>{"WAHR" if status != "FREIGABE" else "FALSCH"}</HGB_377_Gesperrt>
  </BelegKopf>
  <RampenAnweisung>{data.get("rampen_anweisung_kurz", "")}</RampenAnweisung>
</proALPHA_Wareneingang>"""
        return xml

if __name__ == "__main__":
    dummy_audit = {
        "data": {
            "audit_status": "MÄNGELRÜGE_ERFORDERLICH",
            "mangel_detail": "Fehlmenge von 80 Stück festgestellt.",
            "artikel_abgleich": [{
                "artikel_nummer": "6205-2RSH",
                "geliefert_menge": 420,
                "einheit": "ST",
                "charge": "LOT-SKF-992"
            }],
            "hgb_377_bewertung": {"ruege_notwendig": True}
        }
    }
    sap = ErpConnector.generate_sap_bapi_payload(dummy_audit, "LS-44102", "PO-2026-512")
    import json
    print("SAP Payload:\n", json.dumps(sap, indent=2, ensure_ascii=False))
