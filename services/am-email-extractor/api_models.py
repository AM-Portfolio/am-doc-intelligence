from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional


@dataclass
class DiscoverResponse:
    found: bool
    broker: Optional[str] = None
    mailbox: Optional[str] = None
    needs_password: Optional[bool] = None
    error: Optional[str] = None
    email: Optional[Mapping[str, Any]] = None
    attachment: Optional[Mapping[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {'found': self.found}
        if self.broker is not None:
            out['broker'] = self.broker
        if self.mailbox is not None:
            out['mailbox'] = self.mailbox
        if self.needs_password is not None:
            out['needs_password'] = self.needs_password
        if self.error is not None:
            out['error'] = self.error
        if self.email is not None:
            out['email'] = dict(self.email)
        if self.attachment is not None:
            out['attachment'] = dict(self.attachment)
        return out


@dataclass
class ExtractSuccessResponse:
    broker: str
    count: int
    holdings: list[Any]
    db_id: str
    identity_match: Optional[str]
    metadata: Optional[dict[str, Any]] = None
    success: bool = True

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            'success': self.success,
            'broker': self.broker,
            'count': self.count,
            'holdings': self.holdings,
            'db_id': self.db_id,
            'identity_match': self.identity_match,
        }
        if self.metadata is not None:
            out['metadata'] = self.metadata
        return out


@dataclass
class ExtractErrorResponse:
    error: str
    success: Optional[bool] = None
    code: Optional[str] = None
    broker: Optional[str] = None
    count: Optional[int] = None
    db_id: Optional[str] = None
    identity_match: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {'error': self.error}
        if self.success is not None:
            out['success'] = self.success
        if self.code is not None:
            out['code'] = self.code
        if self.broker is not None:
            out['broker'] = self.broker
        if self.count is not None:
            out['count'] = self.count
        if self.db_id is not None:
            out['db_id'] = self.db_id
        if self.identity_match is not None:
            out['identity_match'] = self.identity_match
        return out
