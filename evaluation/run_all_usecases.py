#!/usr/bin/env python3
"""
Comprehensive 10-Use-Case Benchmark for German Warehouse Goods Receipt (§ 377 HGB).
Tests the LagerPilot-Qwen system across the full spectrum of real-world German logistics scenarios.
"""

import os
import sys
import json
import time
from tabulate import tabulate

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.inference import LagerPilotAuditor

def run_comprehensive_benchmark():
    test_suite_path = os.path.join(os.path.dirname(__file__), "comprehensive_test_suite.json")
    with open(test_suite_path, "r", encoding="utf-8") as f:
        use_cases = json.load(f)

    print("=" * 85)
    print("LAGERPILOT-QWEN: UMFASSENDER 10-USE-CASE STRESSTEST FÜR DEUTSCHEN WARENEINGANG")
    print("=" * 85)
    print(f"Lade {len(use_cases)} reale Praxis-Szenarien aus der Kontrakt- & Industrielogistik...\n")

    auditor = LagerPilotAuditor()

    results = []
    total_start = time.time()

    for idx, uc in enumerate(use_cases, 1):
        print(f"\n[{idx:02d}/{len(use_cases):02d}]: {uc['id']} - {uc['title']} ({uc['category']})")
        t0 = time.time()
        res = auditor.audit_delivery(
            lieferschein_ocr=uc["delivery_note"],
            purchase_order_erp=uc["purchase_order"],
            ramp_notes=uc.get("ramp_notes", "")
        )
        latency_ms = (time.time() - t0) * 1000

        data = res.get("data", {})
        predicted_status = data.get("audit_status", "UNKNOWN")
        predicted_ruege = data.get("hgb_377_bewertung", {}).get("ruege_notwendig", False)
        ramp_instruction = data.get("rampen_anweisung_kurz", "")

        status_ok = (predicted_status == uc["expected_status"])
        ruege_ok = (predicted_ruege == uc["expected_ruege"])

        print(f"  - Status Soll/Ist: {uc['expected_status']} / {predicted_status} -> {'✅ OK' if status_ok else '❌ FEHLER'}")
        print(f"  - §377 Rüge Soll/Ist: {uc['expected_ruege']} / {predicted_ruege} -> {'✅ OK' if ruege_ok else '❌ FEHLER'}")
        print(f"  - Rampen-Anweisung: {ramp_instruction}")
        print(f"  - Latenz: {latency_ms:.1f} ms")

        results.append({
            "id": uc["id"],
            "title": uc["title"],
            "category": uc["category"],
            "expected_status": uc["expected_status"],
            "predicted_status": predicted_status,
            "status_match": status_ok,
            "expected_ruege": uc["expected_ruege"],
            "predicted_ruege": predicted_ruege,
            "ruege_match": ruege_ok,
            "latency_ms": latency_ms,
            "ramp_instruction": ramp_instruction,
            "complaint_drafted": bool(data.get("maengelruege_schreiben"))
        })

    total_duration = time.time() - total_start
    avg_latency = sum(r["latency_ms"] for r in results) / len(results)
    status_accuracy = sum(1 for r in results if r["status_match"]) / len(results) * 100
    ruege_accuracy = sum(1 for r in results if r["ruege_match"]) / len(results) * 100

    print("\n" + "=" * 85)
    print("ERGEBNISÜBERSICHT: ALLE PRAXIS-USE-CASES")
    print("=" * 85)

    table_data = []
    for r in results:
        status_symbol = "✅" if r["status_match"] else "❌"
        ruege_symbol = "✅" if r["ruege_match"] else "❌"
        table_data.append([
            r["id"],
            r["category"],
            r["expected_status"],
            r["predicted_status"],
            f"{status_symbol} ({r['latency_ms']:.0f}ms)",
            ruege_symbol,
            "Ja" if r["complaint_drafted"] else "Nein"
        ])

    headers = ["Use Case ID", "Kategorie", "Soll-Status", "Ist-Status", "Status OK", "§377 OK", "Mängelrüge Text"]
    print(tabulate(table_data, headers=headers, tablefmt="grid"))

    print("\nZUSAMMENFASSUNG:")
    print(f"  - Gesamtanzahl Szenarien: {len(results)}")
    print(f"  - Status-Genauigkeit:     {status_accuracy:.1f}% ({sum(1 for r in results if r['status_match'])}/{len(results)})")
    print(f"  - § 377 Rüge-Genauigkeit: {ruege_accuracy:.1f}% ({sum(1 for r in results if r['ruege_match'])}/{len(results)})")
    print(f"  - Mittlere Latenz:        {avg_latency:.1f} ms pro Lieferschein")
    print(f"  - Gesamtlaufzeit:         {total_duration:.1f} Sekunden")
    print("=" * 85)

    # Save results to json
    report_path = os.path.join(os.path.dirname(__file__), "comprehensive_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({
            "metrics": {
                "total_cases": len(results),
                "status_accuracy_pct": status_accuracy,
                "ruege_accuracy_pct": ruege_accuracy,
                "avg_latency_ms": avg_latency
            },
            "cases": results
        }, f, indent=2, ensure_ascii=False)

    print(f"\n[LagerPilot] Detaillierter Audit-Report gespeichert in: {report_path}")

if __name__ == "__main__":
    run_comprehensive_benchmark()
