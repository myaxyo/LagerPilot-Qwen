#!/usr/bin/env python3
"""
Comprehensive Test Suite for LagerPilot-Qwen
Tests all modules:
1. Python Core Inference Engine (LagerPilotAuditor)
2. Automated Benchmark & Edge Cases (§ 377 HGB Scenarios)
3. FastAPI Edge REST API (Live HTTP requests)
"""

import os
import sys
import json
import time
import subprocess
import requests

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.inference import LagerPilotAuditor

def test_inference_engine():
    print("\n" + "=" * 70)
    print("TEST 1: DIRECT CORE INFERENCE ENGINE TEST")
    print("=" * 70)

    auditor = LagerPilotAuditor(device="cpu")

    # Scenario: Shortage of 30 cylinders
    test_ocr = """LIEFERSCHEIN:
Lieferant: Festo SE & Co. KG
LS-Nr: LS-90912 | Datum: 02.11.2026 | PO: PO-8841
Pos 1: PNEU-VENTIL-52-G18 - 70 Stück - Charge: LOT-FE-991"""

    test_po = """ERP-BESTELLUNG:
PO: PO-8841 | Pos 1: PNEU-VENTIL-52-G18 - 100 Stück"""

    test_ramp = "Nachzählung an Rampe 3: Fehlmenge von 30 Stück festgestellt."

    t0 = time.time()
    res = auditor.audit_delivery(test_ocr, test_po, test_ramp)
    elapsed = (time.time() - t0) * 1000

    print(f"Inference Latency: {elapsed:.1f} ms")
    print(f"Success: {res['success']}")
    assert res["success"] is True, "Inference failed!"
    
    data = res["data"]
    print(f"Audit Status: {data.get('audit_status')}")
    print(f"§ 377 Rüge erforderlich: {data.get('hgb_377_bewertung', {}).get('ruege_notwendig')}")
    print(f"Rampen-Anweisung: {data.get('rampen_anweisung_kurz')}")
    
    assert data.get("audit_status") in ["MÄNGELRÜGE_ERFORDERLICH", "SPERRE"], "Shortage was not flagged as discrepancy!"
    print("✅ TEST 1 PASSED: Core inference engine successfully executed and parsed!")
    return True

def test_benchmark_suite():
    print("\n" + "=" * 70)
    print("TEST 2: EVALUATION BENCHMARK SUITE")
    print("=" * 70)
    
    from evaluation.benchmark import run_benchmark
    run_benchmark()
    print("✅ TEST 2 PASSED: Benchmark suite completed successfully!")
    return True

def test_fastapi_server():
    print("\n" + "=" * 70)
    print("TEST 3: FASTAPI ON-PREM EDGE REST API TEST")
    print("=" * 70)

    # Start FastAPI server in background
    port = 8008
    cmd = [
        sys.executable, "-m", "uvicorn", "src.api:app",
        "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    base_url = f"http://127.0.0.1:{port}"

    # Wait for server to become healthy
    print("Waiting for FastAPI server to initialize model...")
    server_ready = False
    for attempt in range(15):
        try:
            r = requests.get(f"{base_url}/health", timeout=2)
            if r.status_code == 200:
                server_ready = True
                print(f"Server ready after {attempt+1} seconds!")
                break
        except requests.exceptions.RequestException:
            pass
        time.sleep(1)

    assert server_ready, "FastAPI server failed to start within 15 seconds!"
    try:
        # 1. Health check
        print(f"Checking GET {base_url}/health ...")
        resp = requests.get(f"{base_url}/health", timeout=10)
        assert resp.status_code == 200, f"Health check failed with {resp.status_code}"
        health_data = resp.json()
        print(f"Health Response: {health_data}")
        assert health_data.get("status") == "online"

        # 2. Audit POST request
        print(f"Checking POST {base_url}/api/v1/audit ...")
        payload = {
            "lieferschein_ocr": "Lieferant: Würth Industrie Service\nLS-Nr: LS-1122\nPos 1: SCHR-DIN912-M8-30 - 5 Karton (à 100 Stk)\nCharge: LOT-1",
            "purchase_order_erp": "PO: BEST-1\nPos 1: SCHR-DIN912-M8-30 - 500 Stück",
            "ramp_notes": "5 Kartons unbeschädigt angeliefert."
        }
        resp = requests.post(f"{base_url}/api/v1/audit", json=payload, timeout=45)
        assert resp.status_code == 200, f"Audit POST failed with {resp.status_code}"
        audit_res = resp.json()
        print("API Audit Response:")
        print(json.dumps(audit_res, indent=2, ensure_ascii=False))
        assert audit_res.get("success") is True
        assert audit_res.get("data", {}).get("audit_status") == "FREIGABE"

        # Test Web UI endpoint
        ui_resp = requests.get(base_url, timeout=10)
        assert ui_resp.status_code == 200 and "LagerPilot-Qwen" in ui_resp.text
        print("Web UI Terminal: 200 OK")

        # Test Barcode parser endpoint
        bc_resp = requests.post(f"{base_url}/api/v1/parse-barcode", json={"barcode": "(01)04012345678901(10)LOT-1(30)50"})
        assert bc_resp.status_code == 200 and bc_resp.json().get("gtin") == "04012345678901"
        print("Barcode Parser API: 200 OK")

        # Test ERP payload endpoint
        erp_resp = requests.post(f"{base_url}/api/v1/erp-payload", json={"audit_result": audit_res})
        assert erp_resp.status_code == 200 and erp_resp.json().get("GOODSMVT_CODE", {}).get("GM_CODE") == "01"
        print("SAP BAPI Generator API: 200 OK")

        print("✅ TEST 3 PASSED: FastAPI microservice and Web Terminal responded with 200 OK!")
    finally:
        proc.terminate()
        proc.wait()

def main():
    print("=" * 70)
    print("STARTING FULL TEST SUITE FOR LAGERPILOT-QWEN")
    print("=" * 70)

    t_start = time.time()
    test_inference_engine()
    test_benchmark_suite()
    test_fastapi_server()

    total_time = time.time() - t_start
    print("\n" + "=" * 70)
    print(f"ALL TESTS COMPLETED SUCCESSFULLY IN {total_time:.1f} SECONDS!")
    print("=" * 70)

if __name__ == "__main__":
    main()
