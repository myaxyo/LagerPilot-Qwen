#!/usr/bin/env python3
"""
LagerPilot-Qwen Evaluation & Benchmark Suite
Tests model performance across diverse German logistics edge cases, JSON validity,
and statutory § 377 HGB compliance determinations.
"""

import os
import sys
import json
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.inference import LagerPilotAuditor

def run_benchmark():
    test_cases_path = "/Users/jon/Documents/privateProjects/lagerAI/evaluation/test_cases.json"
    with open(test_cases_path, "r", encoding="utf-8") as f:
        cases = json.load(f)

    auditor = LagerPilotAuditor()

    print("=" * 70)
    print("LAGERPILOT-QWEN: BENCHMARK FÜR DEN DEUTSCHEN WARENEINGANG (§ 377 HGB)")
    print("=" * 70)

    total = len(cases)
    json_valid_count = 0
    status_correct_count = 0
    ruege_correct_count = 0
    latencies = []

    for i, tc in enumerate(cases, 1):
        print(f"\n[Testfall {i}/{total}]: {tc['id']} - {tc['description']}")
        
        t0 = time.time()
        res = auditor.audit_delivery(
            lieferschein_ocr=tc["lieferschein_ocr"],
            purchase_order_erp=tc["po_erp"],
            ramp_notes=tc["ramp_notes"]
        )
        latency = (time.time() - t0) * 1000
        latencies.append(latency)

        if not res["success"]:
            print(f"  ❌ FEHLER: Ungültiges JSON generiert!")
            print(f"     Details: {res.get('error')}")
            continue

        json_valid_count += 1
        data = res["data"]
        
        pred_status = data.get("audit_status")
        pred_ruege = data.get("hgb_377_bewertung", {}).get("ruege_notwendig")
        ramp_cmd = data.get("rampen_anweisung_kurz", "N/A")

        status_match = (pred_status == tc["expected_status"])
        ruege_match = (pred_ruege == tc["expected_ruege"])

        if status_match:
            status_correct_count += 1
        if ruege_match:
            ruege_correct_count += 1

        print(f"  - Latenz: {latency:.1f} ms", flush=True)
        print(f"  - Status Soll/Ist: {tc['expected_status']} / {pred_status} -> {'✅ OK' if status_match else '❌ ABWEICHUNG'}", flush=True)
        print(f"  - §377 Rüge Soll/Ist: {tc['expected_ruege']} / {pred_ruege} -> {'✅ OK' if ruege_match else '❌ ABWEICHUNG'}", flush=True)
        print(f"  - Rampen-Anweisung: {ramp_cmd}", flush=True)

    print("\n" + "=" * 70)
    print("BENCHMARK-GESAMTERGEBNIS:")
    print(f"  - JSON-Konformität:        {json_valid_count}/{total} ({json_valid_count/total*100:.1f}%)")
    print(f"  - Status-Genauigkeit:      {status_correct_count}/{total} ({status_correct_count/total*100:.1f}%)")
    print(f"  - § 377 Rüge-Genauigkeit:  {ruege_correct_count}/{total} ({ruege_correct_count/total*100:.1f}%)")
    print(f"  - Mittlere Latenz:         {sum(latencies)/len(latencies):.1f} ms pro Lieferschein")
    print("=" * 70)

if __name__ == "__main__":
    run_benchmark()
