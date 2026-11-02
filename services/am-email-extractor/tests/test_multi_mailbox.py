"""Unit tests for multi-mailbox token storage."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import database as dbmod  # noqa: E402


class FakeCollection:
    def __init__(self):
        self.docs = []

    def find(self, query, **kwargs):
        return [d for d in self.docs if self._match(d, query)]

    def find_one(self, query, **kwargs):
        for d in self.docs:
            if self._match(d, query):
                return d
        return None

    def count_documents(self, query):
        return len([d for d in self.docs if self._match(d, query)])

    def update_one(self, filt, update, upsert=False):
        doc = self.find_one(filt)
        sets = update.get('$set', {})
        if doc:
            doc.update(sets)
            return MagicMock(modified_count=1, upserted_id=None)
        if upsert:
            new = {**filt, **sets}
            # flatten $or filters for insert
            if '$or' in new:
                del new['$or']
            self.docs.append(new)
            return MagicMock(modified_count=0, upserted_id='x')
        return MagicMock(modified_count=0, upserted_id=None)

    def update_many(self, filt, update):
        sets = update.get('$set', {})
        n = 0
        for d in self.docs:
            if self._match(d, filt):
                d.update(sets)
                n += 1
        return MagicMock(modified_count=n)

    def delete_one(self, filt):
        before = len(self.docs)
        self.docs = [d for d in self.docs if not self._match(d, filt)]
        return MagicMock(deleted_count=before - len(self.docs))

    def delete_many(self, filt):
        before = len(self.docs)
        self.docs = [d for d in self.docs if not self._match(d, filt)]
        return MagicMock(deleted_count=before - len(self.docs))

    def _match(self, doc, query):
        if not query:
            return True
        if '$or' in query:
            rest = {k: v for k, v in query.items() if k != '$or'}
            if rest and not self._match(doc, rest):
                return False
            return any(self._match(doc, clause) for clause in query['$or'])
        for k, v in query.items():
            if isinstance(v, dict) and '$exists' in v:
                exists = k in doc
                if v['$exists'] and not exists:
                    return False
                if not v['$exists'] and exists:
                    return False
                continue
            if doc.get(k) != v:
                return False
        return True


@pytest.fixture
def helper(monkeypatch):
    coll = FakeCollection()
    helper = dbmod.Database()
    helper.client = object()
    helper.db = MagicMock()
    helper.db.__getitem__ = lambda self, name: coll
    # sort() on find — FakeCollection.find returns list; add sort stub
    orig_find = coll.find

    def find_sorted(query, **kwargs):
        class R(list):
            def sort(self, *a, **k):
                return self

        return R(orig_find(query, **kwargs))

    coll.find = find_sorted
    return helper, coll


def test_two_mailboxes_same_user(helper):
    h, coll = helper
    h.save_user_token('u1', b'tok-a', email='a@gmail.com')
    h.save_user_token('u1', b'tok-b', email='b@gmail.com')
    boxes = h.list_mailboxes('u1')
    assert len(boxes) == 2
    emails = {m['email'] for m in boxes}
    assert emails == {'a@gmail.com', 'b@gmail.com'}
    assert sum(1 for m in boxes if m['is_default']) == 1
    assert h.get_user_token('u1', email='b@gmail.com') == b'tok-b'
    assert h.resolve_mailbox_email('u1', 'b@gmail.com') == 'b@gmail.com'


def test_cap_five_mailboxes(helper):
    h, _ = helper
    for i in range(5):
        h.save_user_token('u1', f'tok{i}'.encode(), email=f'u{i}@gmail.com')
    with pytest.raises(ValueError, match='Maximum 5'):
        h.save_user_token('u1', b'x', email='extra@gmail.com')


def test_delete_one_promotes_default(helper):
    h, _ = helper
    h.save_user_token('u1', b'a', email='a@gmail.com')
    h.save_user_token('u1', b'b', email='b@gmail.com')
    h.delete_user_token('u1', email='a@gmail.com')
    boxes = h.list_mailboxes('u1')
    assert len(boxes) == 1
    assert boxes[0]['email'] == 'b@gmail.com'
    assert boxes[0]['is_default'] is True


def test_resolve_default_without_mailbox_arg(helper):
    h, _ = helper
    h.save_user_token('u1', b'a', email='a@gmail.com')
    h.save_user_token('u1', b'b', email='b@gmail.com')
    assert h.resolve_mailbox_email('u1', None) == 'a@gmail.com'
