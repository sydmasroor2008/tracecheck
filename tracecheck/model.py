"""Pydantic models for the synthetic ground truth and for extracted fields.

The ground truth is what tools/make_factory.py writes before it draws the
documents. The app never reads it; it reads extracted fields instead.
"""

from typing import Any, List, Literal, Optional

from pydantic import BaseModel


class Chemistry(BaseModel):
    C: Optional[float] = None
    Mn: Optional[float] = None
    Si: Optional[float] = None
    Cr: Optional[float] = None
    Ni: Optional[float] = None
    other: Optional[float] = None


class Purchase(BaseModel):
    invoice_no: str
    supplier: str
    supplier_type: Literal["mill", "trader"]
    heat: str
    tonnes: float
    date: str
    emissions_claim: Optional[str] = None


class DeliveryNote(BaseModel):
    note_no: str
    supplier: str
    mill: str
    heats: List[str]


class Certificate(BaseModel):
    cert_no: str
    heat: str
    mill: str
    grade: str
    tonnes: float
    production_date: str
    chemistry: Chemistry
    layout: str = "across"


class VerificationReport(BaseModel):
    report_no: str
    mill: str
    period_year: int
    precursor_see: float
    label: str


class ProductionRow(BaseModel):
    month: str
    tonnes: float
    cn_code: str
    heats: List[str]


class StockRow(BaseModel):
    heat: str
    tonnes: float
    mill: Optional[str] = None


class Stock(BaseModel):
    opening: List[StockRow]
    closing: List[StockRow]
    count_note: Optional[str] = None


class Scrap(BaseModel):
    tonnes: float
    pre_consumer_share: float
    sources: str


class FuelInvoice(BaseModel):
    invoice_no: str
    month: str
    fuel: str
    quantity: float
    unit: str
    emission_factor_t_per_tj: float


class Shipment(BaseModel):
    invoice_no: str
    date: str
    destination: str
    cn_code: str
    tonnes: float
    production_months: List[str]


class GroundTruth(BaseModel):
    folder: str
    factory: str
    reporting_year: int
    cn_codes: List[str]
    purchases: List[Purchase]
    delivery_notes: List[DeliveryNote]
    certificates: List[Certificate]
    verification_reports: List[VerificationReport]
    production: List[ProductionRow]
    stock: Stock
    scrap: Scrap
    fuel: List[FuelInvoice]
    shipments: List[Shipment]
    planted_issues: List[str]
    documents: List[str]


class ExtractedField(BaseModel):
    key: str                 # path into the facility data, e.g. "certificates[2].chemistry.Mn"
    doc: str
    label: str
    value: Any
    unit: Optional[str] = None
    source_file: str
    page: int
    mode: Literal["MANUAL", "CACHED", "LIVE"]
    confidence: float
    needs_review: bool
    reviewer: Optional[str] = None
    reviewed_at: Optional[str] = None
