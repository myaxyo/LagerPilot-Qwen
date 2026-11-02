#!/usr/bin/env python3
"""
LagerPilot GS1-128 & VDA 4902 Barcode / 2D DataMatrix Parser
Parses standard industrial barcode strings scanned at the German loading ramp
and extracts structured metadata (GTIN, Batch/Charge, MHD, Quantity, VPE, PO).
"""

import re
from datetime import datetime
from typing import Dict, Any

class IndustrialBarcodeParser:
    """
    Decodes GS1-128 and VDA 4902 (German Automotive Standard) barcode strings.
    """

    @staticmethod
    def parse_gs1(barcode_str: str) -> Dict[str, Any]:
        """
        Parses GS1-128 string containing Application Identifiers (AIs).
        Example: (01)04012345678901(10)CH-2026-091(17)261231(30)50
        """
        data = {
            "format": "GS1-128",
            "gtin": None,
            "charge_lot": None,
            "mhd_date": None,
            "menge_count": None,
            "purchase_order": None,
            "raw": barcode_str
        }

        clean = barcode_str.strip()

        # Match AI (01) GTIN
        m_gtin = re.search(r'(?:\(01\)|(?<=^01))(\d{14})', clean)
        if m_gtin:
            data["gtin"] = m_gtin.group(1)

        # Match AI (10) Batch / Lot (alphanumeric, up to 20 chars)
        m_lot = re.search(r'(?:\(10\)|(?<=\b10))([A-Za-z0-9\-_]+)', clean)
        if m_lot:
            data["charge_lot"] = m_lot.group(1).split("(")[0]

        # Match AI (17) Expiration Date (YYMMDD)
        m_mhd = re.search(r'(?:\(17\)|(?<=\b17))(\d{6})', clean)
        if m_mhd:
            yymmdd = m_mhd.group(1)
            try:
                # Convert YYMMDD to YYYY-MM-DD
                year = 2000 + int(yymmdd[0:2])
                month = int(yymmdd[2:4])
                day = int(yymmdd[4:6])
                data["mhd_date"] = f"{year:04d}-{month:02d}-{day:02d}"
            except ValueError:
                data["mhd_date"] = yymmdd

        # Match AI (30) or (37) Count / Quantity
        m_qty = re.search(r'(?:\(30\)|\(37\)|(?<=\b30))(\d+)', clean)
        if m_qty:
            data["menge_count"] = int(m_qty.group(1))

        # Match AI (400) Customer PO
        m_po = re.search(r'(?:\(400\))([A-Za-z0-9\-_]+)', clean)
        if m_po:
            data["purchase_order"] = m_po.group(1)

        return data

    @staticmethod
    def parse_vda_4902(scan_str: str) -> Dict[str, Any]:
        """
        Parses German automotive standard VDA 4902 transport labels.
        Prefixes: P (Part number), Q (Quantity), V (Supplier ID), S (Serial/Lot), N (PO number).
        """
        data = {
            "format": "VDA-4902",
            "part_number": None,
            "quantity": None,
            "supplier_id": None,
            "lot_serial": None,
            "po_number": None,
            "raw": scan_str
        }

        tokens = scan_str.replace("\n", " ").split()
        for tok in tokens:
            if tok.startswith("P") and len(tok) > 1 and not data["part_number"]:
                data["part_number"] = tok[1:]
            elif tok.startswith("Q") and len(tok) > 1 and not data["quantity"]:
                try:
                    data["quantity"] = int(tok[1:])
                except ValueError:
                    pass
            elif tok.startswith("V") and len(tok) > 1 and not data["supplier_id"]:
                data["supplier_id"] = tok[1:]
            elif tok.startswith("S") and len(tok) > 1 and not data["lot_serial"]:
                data["lot_serial"] = tok[1:]
            elif tok.startswith("N") and len(tok) > 1 and not data["po_number"]:
                data["po_number"] = tok[1:]

        return data

if __name__ == "__main__":
    # Test sample
    test_gs1 = "(01)04012345678901(10)LOT-SKF-881(17)261231(30)50"
    print("Parsed GS1:", IndustrialBarcodeParser.parse_gs1(test_gs1))

    test_vda = "P114000 Q10 V99821 S2026-CH-01"
    print("Parsed VDA 4902:", IndustrialBarcodeParser.parse_vda_4902(test_vda))
