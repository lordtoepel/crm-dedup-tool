"""Contact data models for deduplication."""
from __future__ import annotations
from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime


class Contact(BaseModel):
    """Represents a CRM contact record."""
    id: str
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    job_title: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    association_count: int = 0  # Number of deals, activities, etc.
    raw_properties: dict[str, Any] = {}

    @property
    def email_domain(self) -> Optional[str]:
        """Extract domain from email for blocking."""
        if self.email and "@" in self.email:
            return self.email.split("@")[1].lower()
        return None

    @property
    def name_prefix(self) -> Optional[str]:
        """Get first 3 chars of name for blocking."""
        name = self.full_name or f"{self.first_name or ''} {self.last_name or ''}".strip()
        if name:
            return name[:3].lower()
        return None

    @property
    def normalized_name(self) -> str:
        """Get normalized full name for comparison."""
        name = self.full_name or f"{self.first_name or ''} {self.last_name or ''}".strip()
        return name.lower().strip()

    @property
    def normalized_email(self) -> Optional[str]:
        """Get normalized email for comparison."""
        if self.email:
            return self.email.lower().strip()
        return None


class DuplicateSet(BaseModel):
    """A set of duplicate contacts with a determined winner."""
    confidence: float  # 0-100
    winner: Contact
    losers: list[Contact]
    merged_preview: dict[str, Any]  # What the merged record will look like
