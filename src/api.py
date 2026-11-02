#!/usr/bin/env python3
"""
LagerPilot-Qwen On-Prem Edge REST API
FastAPI service running locally on warehouse hardware (NUC / ThinkCentre / mini-server)
for instant goods receipt verification and § 377 HGB compliance.
"""

import os
import sys
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.inference import LagerPilotAuditor
from src.gs1_parser import IndustrialBarcodeParser
from src.erp_connector import ErpConnector

app = FastAPI(
    title="LagerPilot § 377 HGB Wareneingangs-Auditor",
    description="Edge-KI Service zur automatischen Lieferschein-Auditierung und Mängelrügenerstellung im deutschen Mittelstandslager.",
    version="1.0.0"
)

auditor: Optional[LagerPilotAuditor] = None

@app.on_event("startup")
def startup_event():
    global auditor
    auditor = LagerPilotAuditor()

@app.get("/", response_class=HTMLResponse)
def get_ramp_dashboard():
    """Serves the interactive rugged warehouse terminal web dashboard."""
    html_path = os.path.join(os.path.dirname(__file__), "web_ui.html")
    with open(html_path, "r", encoding="utf-8") as f:
        return f.read()

class AuditRequest(BaseModel):
    lieferschein_ocr: str = Field(..., description="Vollständiger OCR-Text oder Rohscan des Lieferscheins")
    purchase_order_erp: str = Field(..., description="Offene ERP-Bestellpositionen (Soll-Vorgabe)")
    ramp_notes: Optional[str] = Field(default="", description="Physische Sichtprüfungs-Notizen des Rampenmitarbeiters")

class BarcodeRequest(BaseModel):
    barcode: str

class ErpPayloadRequest(BaseModel):
    audit_result: Dict[str, Any]
    delivery_note_id: Optional[str] = "LS-RAMPE-01"
    po_number: Optional[str] = "PO-ERP-01"

@app.post("/api/v1/parse-barcode")
def parse_barcode_endpoint(req: BarcodeRequest):
    bc = req.barcode.strip()
    if bc.startswith("(") or "01" in bc:
        return IndustrialBarcodeParser.parse_gs1(bc)
    return IndustrialBarcodeParser.parse_vda_4902(bc)

@app.post("/api/v1/erp-payload")
def generate_erp_payload_endpoint(req: ErpPayloadRequest):
    sap = ErpConnector.generate_sap_bapi_payload(
        audit_result=req.audit_result,
        delivery_note_id=req.delivery_note_id or "LS-RAMPE-01",
        po_number=req.po_number or "PO-ERP-01"
    )
    return sap

class AuditResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    raw_text: Optional[str] = None

@app.get("/health")
def health_check():
    return {
        "status": "online",
        "service": "LagerPilot-Qwen",
        "device": auditor.device if auditor else "uninitialized"
    }

@app.post("/api/v1/audit", response_model=AuditResponse)
def run_audit(req: AuditRequest):
    if not auditor:
        raise HTTPException(status_code=503, detail="LagerPilot Auditor is still initializing.")
    
    res = auditor.audit_delivery(
        lieferschein_ocr=req.lieferschein_ocr,
        purchase_order_erp=req.purchase_order_erp,
        ramp_notes=req.ramp_notes or ""
    )
    return res

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api:app", host="0.0.0.0", port=8000, reload=False)
