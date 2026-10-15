from decimal import Decimal, InvalidOperation
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

class Strict(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)

class Fact(Strict):
    property: str = Field(min_length=1,max_length=80)
    operator: Literal['eq','ge','le']
    value: str
    unit: str = Field(min_length=1,max_length=16)
    conditions: dict[str,str] = Field(default_factory=dict)
    source_ids: list[str] = Field(min_length=1,max_length=30)

    @field_validator('value')
    @classmethod
    def finite(cls,v):
        try:d=Decimal(v)
        except InvalidOperation as exc:raise ValueError('Quantity must be a decimal number') from exc
        if not d.is_finite() or abs(d)>Decimal('1e15'):raise ValueError('Quantity must be finite and bounded')
        return str(d)

class Candidate(Fact):
    title: str = Field(min_length=1,max_length=200)
    phase: Literal['purchase','acceptance','delivery']='purchase'
    equipment_type: Literal['transformer']='transformer'

class Supplier(Strict):
    name: str = Field(min_length=1,max_length=120)
    configuration: str | None = Field(default=None,min_length=1,max_length=120)
    revision: str | None = Field(default=None,min_length=1,max_length=60)
    serial: str | None = Field(default=None,max_length=120)
    family: str | None = Field(default=None,max_length=120)
    price_cents: int | None = Field(default=None,ge=0,le=10**14)
    currency: Literal['USD','CHF','EUR'] | None = None
    delivery_weeks: int | None = Field(default=None,ge=0,le=520)
    # What delivery_weeks is counted from. Only project_start is comparable with a project-week milestone;
    # None means the source did not say, which is treated as not comparable.
    delivery_basis: Literal['project_start','after_order','after_drawing_approval','other'] | None = None
    # Whether price_cents is per unit or a combined amount for several units.
    price_basis: Literal['unit','lot_total'] | None = None
    expedite_cents: int | None = Field(default=None,ge=0,le=10**14)
    rework_cents: int | None = Field(default=None,ge=0,le=10**14)
    # A bid tabulation can carry prices without any technical guarantee, so facts may be empty.
    # Offer-level sources cite the bidder and its commercial values; facts cite their own spans.
    facts: list[Fact] = Field(default_factory=list,max_length=100)
    source_ids: list[str] = Field(default_factory=list,max_length=30)

class Evidence(Strict):
    title: str = Field(min_length=1,max_length=200)
    kind: Literal['routine','type','nameplate']
    serial: str | None = Field(default=None,max_length=120)
    family: str | None = Field(default=None,max_length=120)
    configuration: str | None = Field(default=None,min_length=1,max_length=120)
    revision: str | None = Field(default=None,min_length=1,max_length=60)
    conditions: dict[str,str] = Field(default_factory=dict)
    measurements: list[Fact] = Field(default_factory=list,max_length=100)
    source_ids: list[str] = Field(min_length=1,max_length=30)
    approved_family_coverage: Literal[False]=False

class SnapshotRequest(Strict):
    snapshot_hash: str = Field(pattern=r'^[0-9a-f]{64}$')

class ReviewRequest(SnapshotRequest):
    accepted: bool
    witness_answer: bool | None = None

class DecisionRequest(SnapshotRequest):
    supplier_id: str
    gate: Literal['purchase','shipment']

class ReleaseRequest(SnapshotRequest):
    idempotency_key: str = Field(min_length=1,max_length=200)

class ExtractRequest(SnapshotRequest):
    kind: Literal['requirements','supplier','evidence']='requirements'
    supplier_id: str | None=None

class ProposalApprovalRequest(SnapshotRequest):
    family_coverage_confirmed: bool=False
    supersedes_evidence_id: str | None=None

class SupplierPriceCorrectionRequest(SnapshotRequest):
    price_cents: int | None = Field(ge=0,le=10**14,strict=True)
    currency: Literal['USD','CHF','EUR'] | None
    source_id: str = Field(min_length=1,max_length=500)
    reason: str = Field(min_length=1,max_length=2000)

class ScheduleRequest(SnapshotRequest):
    required_delivery_week: int = Field(ge=0,le=520)
    source_id: str

class ProjectMetadataRequest(SnapshotRequest):
    name: str = Field(min_length=1,max_length=200)
    customer: str = Field(default='',max_length=200)
    equipment: str = Field(min_length=1,max_length=500)
