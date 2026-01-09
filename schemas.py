"""
Pydantic schemas for request/response models - UPDATED FOR MONGODB SCHEMA
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ===== ENUMS =====

class GrievanceStatus(str, Enum):
    """Grievance status enum - aligned with PDF"""
    SUBMITTED = "Submitted"
    IN_PROGRESS = "In Progress"
    RESOLVED = "Resolved"
    CLOSED = "Closed"


class Priority(str, Enum):
    """Priority levels"""
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class Language(str, Enum):
    """Supported languages"""
    TELUGU = "te"
    ENGLISH = "en"
    HINDI = "hi"


class JurisdictionLevel(str, Enum):
    """Administrative levels"""
    DISTRICT = "District"
    MANDAL = "Mandal"
    SECRETARIAT = "Secretariat"


# ===== INPUT DATA MODELS =====

class InputData(BaseModel):
    """Original input from citizen"""
    original_text: str = Field(..., description="Original complaint text (e.g., in Telugu)")
    voice_url: Optional[str] = Field(None, description="S3 URL for voice inputs (IVR/App)")
    image_urls: List[str] = Field(default_factory=list, description="URLs to uploaded images")


# ===== AI ANALYSIS MODELS =====

class Explainability(BaseModel):
    """Explainability for LLM classification decisions"""
    category_reason: str = Field("", description="Why this category was chosen")
    department_reason: str = Field("", description="Why this department was assigned")
    priority_reason: str = Field("", description="Why this priority level was set")


class AIAnalysis(BaseModel):
    """AI analysis output - matches MongoDB schema"""
    english_text: str = Field(..., description="AI translated text for processing")
    predicted_category: str = Field(..., description="AI categorized topic (e.g., Sanitation)")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence for auto-routing threshold")
    vector_embedding: Optional[List[float]] = Field(None, description="For semantic search (Deduplication)")
    summary: Optional[str] = Field(None, description="Brief summary of the issue")
    keywords: List[str] = Field(default_factory=list, description="Key topics")
    explanation: Optional[Explainability] = Field(None, description="Why these classifications were made")


# ===== LOCATION MODELS =====

class GeoLocation(BaseModel):
    """GeoJSON Point for location"""
    type: str = Field("Point", const=True)
    coordinates: List[float] = Field(..., description="[Longitude, Latitude]")


class LocationDetails(BaseModel):
    """Embedded location details"""
    district: Optional[str] = None
    mandal: Optional[str] = None
    secretariat_name: Optional[str] = None


class Location(BaseModel):
    """Location information - matches MongoDB schema"""
    geo: GeoLocation = Field(..., description="GeoJSON Point [Longitude, Latitude]")
    secretariat_id: str = Field(..., description="Mapped Ward/Village Secretariat ID")
    details: Optional[LocationDetails] = Field(None, description="Embedded admin boundary details")


# ===== HISTORY & AUDIT =====

class StatusTransition(BaseModel):
    """Status change history entry"""
    from_status: str
    to_status: str
    changed_by: str
    changed_by_name: str
    timestamp: datetime
    remarks: Optional[str] = None


class AssignmentHistory(BaseModel):
    """Assignment change history"""
    from_officer: Optional[str] = None
    to_officer: str
    assigned_by: str
    assigned_by_name: str
    timestamp: datetime
    reason: Optional[str] = None


# ===== DOCUMENT ANALYSIS =====

class DocumentEntities(BaseModel):
    """Extracted entities from document"""
    dates: List[str] = Field(default_factory=list)
    amounts: List[str] = Field(default_factory=list)
    locations: List[str] = Field(default_factory=list)
    people: List[str] = Field(default_factory=list)
    organizations: List[str] = Field(default_factory=list)


class DocumentAnalysisResult(BaseModel):
    """Result of document understanding analysis"""
    success: bool
    extracted_text: str = Field("", description="Full text extracted from document")
    key_entities: DocumentEntities = Field(default_factory=DocumentEntities)
    document_type: str = Field("other", description="Type: complaint_letter, application, etc.")
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    error: Optional[str] = None


# ===== CORE GRIEVANCE MODEL (MongoDB Document) =====

class Grievance(BaseModel):
    """
    Complete grievance model - MongoDB document structure
    Aligned with MongoDB Schema 4 review.pdf
    """
    # Primary Keys
    grievance_id: str = Field(..., description="Readable ID (AP-VSP-PDT-2026-001)")
    
    # Citizen Reference
    citizen_id: str = Field(..., description="Reference to Citizens collection (ObjectId as string)")
    
    # Basic Info
    title: str = Field(..., description="Short summary of the issue")
    
    # Input Data (Embedded)
    input_data: InputData = Field(..., description="Original input from citizen")
    
    # AI Analysis (Embedded)
    ai_analysis: AIAnalysis = Field(..., description="AI processing results")
    
    # Location (Embedded with references)
    location: Location = Field(..., description="Geospatial and administrative location")
    
    # Department & Assignment
    department_id: str = Field(..., description="Reference to Officials jurisdiction_unit_id")
    assigned_to: Optional[str] = Field(None, description="Reference to Officer ObjectId")
    
    # Priority & Status
    priority: Priority = Field(..., description="Urgency level")
    status: GrievanceStatus = Field(GrievanceStatus.SUBMITTED, description="Current workflow status")
    sla_due_date: Optional[datetime] = Field(None, description="Deadline based on SLA")
    
    # Attachments
    attachments: List[str] = Field(default_factory=list, description="URLs to uploaded files")
    
    # Document Analysis (Optional)
    document_analysis: Optional[DocumentAnalysisResult] = None
    
    # History (Embedded arrays)
    history: List[StatusTransition] = Field(default_factory=list, description="Status transition log")
    assignment_history: List[AssignmentHistory] = Field(default_factory=list)
    
    # Duplicate Detection
    duplicate_of_id: Optional[str] = Field(None, description="Self-reference to master ticket if duplicate")
    similar_cases: List[str] = Field(default_factory=list, description="Similar grievance IDs")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    
    # Processing Logs
    processing_logs: List[Dict[str, Any]] = Field(default_factory=list)
    
    class Config:
        use_enum_values = True


# ===== CITIZEN MODEL =====

class SavedLocation(BaseModel):
    """Saved location for quick complaint submission"""
    location_id: str = Field(..., description="Reference to admin_hierarchy")
    label: str = Field(..., description="e.g., 'Home', 'Office'")
    geo: GeoLocation
    secretariat_id: str
    details: Optional[LocationDetails] = None


class Citizen(BaseModel):
    """
    Citizen/User model - MongoDB document
    Manages user profiles for beneficiaries
    """
    # Identity
    aadhaar_hash: str = Field(..., description="Secure hash of Aadhaar for uniqueness")
    full_name: str = Field(..., description="Citizen Name")
    
    # Contact
    mobile: Optional[str] = None
    email: Optional[str] = None
    
    # Preferences
    preferred_language: Language = Field(Language.TELUGU, description="Language code for AI translation")
    
    # Saved Locations (Embedded)
    saved_locations: List[SavedLocation] = Field(default_factory=list)
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    active: bool = True


# ===== OFFICIAL/OFFICER MODEL =====

class JurisdictionDetails(BaseModel):
    """Embedded jurisdiction information"""
    district: Optional[str] = None
    mandal: Optional[str] = None
    secretariat_name: Optional[str] = None


class Official(BaseModel):
    """
    Official/Officer model - MongoDB document
    Government employees who resolve grievances
    """
    # Identity
    employee_id: str = Field(..., description="Government Employee ID")
    full_name: str = Field(..., description="Officer Name")
    designation: str = Field(..., description="Role/Post")
    
    # Contact
    mobile: Optional[str] = None
    email: str = Field(..., description="Official email")
    
    # Jurisdiction (with embedded details)
    jurisdiction_level: JurisdictionLevel = Field(..., description="District, Mandal, or Secretariat")
    jurisdiction_unit_id: str = Field(..., description="ID of the unit they administer")
    jurisdiction_details: Optional[JurisdictionDetails] = Field(None, description="Embedded area details")
    
    # Department
    department: str = Field(..., description="Department name (Sanitation, Electrical, etc.)")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    active: bool = True


# ===== ADMIN HIERARCHY MODEL =====

class AdminUnit(BaseModel):
    """
    Administrative hierarchy - MongoDB document
    Represents AP governance structure (District -> Mandal -> Secretariat)
    """
    # Custom ID (not ObjectId)
    unit_id: str = Field(..., description="Custom ID (e.g., DIST_VSP)")
    
    # Type and Names
    type: JurisdictionLevel = Field(..., description="District, Mandal, or Secretariat")
    name_english: str = Field(..., description="Name in English")
    name_telugu: str = Field(..., description="Name in Telugu")
    
    # Hierarchy
    parent_id: Optional[str] = Field(None, description="Reference to parent administrative unit")
    
    # Geospatial Boundary
    boundary: Optional[Dict[str, Any]] = Field(None, description="GeoJSON Polygon for auto-routing")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    active: bool = True


# ===== AI FEEDBACK (RLHF) MODEL =====

class HumanCorrection(BaseModel):
    """Correction data provided by officer"""
    corrected_category: Optional[str] = None
    corrected_department: Optional[str] = None
    corrected_priority: Optional[Priority] = None
    reason: str = Field(..., description="Why the correction was made")


class AIFeedback(BaseModel):
    """
    AI Feedback model - MongoDB document
    RLHF data for model improvement
    """
    # References
    grievance_id: str = Field(..., description="Link to original grievance")
    corrected_by: str = Field(..., description="Officer ID who made correction")
    corrected_by_name: str = Field(..., description="Officer name (embedded)")
    
    # Original AI Prediction
    original_prediction: Dict[str, Any] = Field(..., description="What AI predicted")
    
    # Human Correction
    human_correction: HumanCorrection = Field(..., description="Correct data for retraining")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    used_for_training: bool = False


# ===== REQUEST/RESPONSE MODELS =====

class GrievanceInput(BaseModel):
    """Input model for grievance submission"""
    text: str = Field(..., description="Grievance text in Telugu or English")
    language: Language = Field(Language.ENGLISH)
    user_name: Optional[str] = None
    user_contact: Optional[str] = None
    location_lat: Optional[float] = None
    location_lon: Optional[float] = None
    attachments: List[str] = Field(default_factory=list)


class GrievanceResponse(BaseModel):
    """API response for grievance"""
    success: bool
    grievance_id: str
    message: str
    data: Optional[Grievance] = None


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    llm_provider: str
    database_connected: bool
    collections: Optional[Dict[str, int]] = None


# ===== AUDIO & IMAGE PROCESSING =====

class AudioTranscription(BaseModel):
    """Audio transcription result"""
    success: bool
    text: Optional[str] = None
    language: Optional[str] = None
    confidence: float = 0.0
    error: Optional[str] = None


class ImageOCR(BaseModel):
    """Image OCR result"""
    success: bool
    text: Optional[str] = None
    confidence: float = 0.0
    error: Optional[str] = None