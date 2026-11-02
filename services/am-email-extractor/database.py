import os
import pymongo
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MAX_MAILBOXES_PER_USER = 5


def _norm_email(email):
    if not email:
        return None
    return str(email).strip().lower() or None


class Database:
    def __init__(self):
        self.mongo_uri = os.environ.get('MONGODB_URL', 'mongodb://admin:password123@localhost:27017/portfolio?authSource=admin')
        self.db_name = os.environ.get('MONGO_DATABASE', 'portfolio')
        self.client = None
        self.db = None
        
    def connect(self):
        """Establish connection to MongoDB"""
        if not self.client:
            try:
                self.client = pymongo.MongoClient(self.mongo_uri)
                self.db = self.client[self.db_name]
                logger.info(f"Connected to MongoDB: {self.db_name}")
            except Exception as e:
                logger.error(f"Failed to connect to MongoDB: {e}")
                raise e
    
    def get_db(self):
        """Get database instance, connecting if necessary"""
        if self.db is None:
            self.connect()
        return self.db

    def save_holdings(self, user_id, broker, holdings, metadata=None):
        """
        Save extracted holdings to MongoDB
        
        Args:
            user_id: The ID of the user (e.g. email or auth sub)
            broker: Broker name (zerodha, groww, etc.)
            holdings: List of holding dictionaries
            metadata: Optional metadata (email subject, date, etc.)
            
        Returns:
            The inserted document ID
        """
        db = self.get_db()
        collection = db['portfolio_holdings']
        
        document = {
            'user_id': user_id,
            'broker': broker,
            'holdings': holdings,
            'extracted_at': datetime.utcnow(),
            'source': 'gmail_extraction',
            'metadata': metadata or {}
        }
        
        
        result = collection.insert_one(document)
        logger.info(f"Saved {len(holdings)} holdings for user {user_id} from {broker}. Doc ID: {result.inserted_id}")
        return str(result.inserted_id)

    def get_latest_holdings(self, user_id, broker=None):
        """Get latest holdings for a user, optionally filtered by broker"""
        db = self.get_db()
        collection = db['portfolio_holdings']
        
        query = {'user_id': user_id}
        if broker:
            query['broker'] = broker
            
        # Sort by extraction time descending
        return collection.find_one(query, sort=[('extracted_at', -1)])

    def list_mailboxes(self, user_id):
        """Return mailbox summaries for a user (email, is_default, updated_at)."""
        self._migrate_legacy_tokens(user_id)
        db = self.get_db()
        collection = db['user_tokens']
        docs = list(collection.find({'user_id': user_id}).sort('updated_at', pymongo.ASCENDING))
        out = []
        for i, doc in enumerate(docs):
            email = _norm_email(doc.get('email'))
            if not email:
                continue
            out.append({
                'email': email,
                'is_default': bool(doc.get('is_default')) or i == 0,
                'updated_at': doc.get('updated_at').isoformat() + 'Z' if doc.get('updated_at') else None,
            })
        # Ensure exactly one default
        if out and not any(m['is_default'] for m in out):
            out[0]['is_default'] = True
        return out

    def mailbox_count(self, user_id):
        return len(self.list_mailboxes(user_id))

    def resolve_mailbox_email(self, user_id, mailbox=None):
        """
        Resolve which mailbox email to use.
        mailbox query → that email if owned; else default; else sole legacy.
        """
        self._migrate_legacy_tokens(user_id)
        wanted = _norm_email(mailbox)
        mailboxes = self.list_mailboxes(user_id)
        if not mailboxes:
            return None
        if wanted:
            for m in mailboxes:
                if m['email'] == wanted:
                    return wanted
            return None
        for m in mailboxes:
            if m.get('is_default'):
                return m['email']
        return mailboxes[0]['email']

    def save_user_token(self, user_id, token_data, email=None, *, is_default=None):
        """
        Save OAuth token for user+mailbox.
        email required for new multi-mailbox docs; without email, upserts legacy/default slot.
        """
        db = self.get_db()
        collection = db['user_tokens']
        email_n = _norm_email(email)

        if email_n:
            existing = collection.find_one({'user_id': user_id, 'email': email_n})
            total = collection.count_documents({'user_id': user_id})
            if not existing and total >= MAX_MAILBOXES_PER_USER:
                raise ValueError(f'Maximum {MAX_MAILBOXES_PER_USER} mailboxes per user')

            if is_default is None:
                # First mailbox for user becomes default; updates keep prior flag
                is_default = total == 0 or (
                    bool(existing) and bool(existing.get('is_default'))
                )
            if is_default:
                collection.update_many({'user_id': user_id}, {'$set': {'is_default': False}})

            result = collection.update_one(
                {'user_id': user_id, 'email': email_n},
                {'$set': {
                    'user_id': user_id,
                    'email': email_n,
                    'token_data': token_data,
                    'updated_at': datetime.utcnow(),
                    'is_default': bool(is_default),
                }},
                upsert=True,
            )
            # Remove legacy doc without email once we have a named mailbox
            collection.delete_many({
                'user_id': user_id,
                '$or': [{'email': {'$exists': False}}, {'email': None}, {'email': ''}],
            })
            logger.info(
                f"Saved token for user {user_id} mailbox {email_n}. "
                f"Modified={result.modified_count} Upserted={result.upserted_id}"
            )
            return email_n

        # Legacy path: single token without email (compat)
        result = collection.update_one(
            {
                'user_id': user_id,
                '$or': [{'email': {'$exists': False}}, {'email': None}, {'email': ''}],
            },
            {'$set': {
                'token_data': token_data,
                'updated_at': datetime.utcnow(),
                'is_default': True,
            }},
            upsert=True,
        )
        logger.info(f"Saved legacy token for user {user_id}. Modified={result.modified_count}")
        return None

    def get_user_token(self, user_id, email=None):
        """Retrieve OAuth token bytes for user (optional mailbox email)."""
        self._migrate_legacy_tokens(user_id)
        db = self.get_db()
        collection = db['user_tokens']
        email_n = _norm_email(email)

        if email_n:
            doc = collection.find_one({'user_id': user_id, 'email': email_n})
        else:
            resolved = self.resolve_mailbox_email(user_id, None)
            if resolved:
                doc = collection.find_one({'user_id': user_id, 'email': resolved})
            else:
                doc = collection.find_one({
                    'user_id': user_id,
                    '$or': [{'email': {'$exists': False}}, {'email': None}, {'email': ''}],
                })

        if doc and 'token_data' in doc:
            logger.info(f"Token found for user {user_id} mailbox={doc.get('email')}")
            return doc['token_data']
        logger.warning(f"No token for user {user_id} mailbox={email_n}")
        return None

    def delete_user_token(self, user_id, email=None):
        """Delete one mailbox token, or all if email is None (legacy disconnect-all)."""
        db = self.get_db()
        collection = db['user_tokens']
        email_n = _norm_email(email)
        if email_n:
            result = collection.delete_one({'user_id': user_id, 'email': email_n})
            logger.info(f"Deleted mailbox {email_n} for user {user_id}. count={result.deleted_count}")
            # Promote another to default if needed
            remaining = list(
                collection.find({'user_id': user_id}).sort('updated_at', pymongo.ASCENDING)
            )
            if remaining and not any(r.get('is_default') for r in remaining):
                first_email = remaining[0].get('email')
                if first_email:
                    collection.update_one(
                        {'user_id': user_id, 'email': first_email},
                        {'$set': {'is_default': True}},
                    )
            return result.deleted_count
        result = collection.delete_many({'user_id': user_id})
        logger.info(f"Deleted all tokens for user {user_id}. count={result.deleted_count}")
        return result.deleted_count

    def _migrate_legacy_tokens(self, user_id):
        """If a doc has token but no email, leave it; email filled on next successful status/connect."""
        # No-op placeholder — email backfill happens in app when creds are live.
        return


# Global instance
db_instance = Database()

def get_db():
    """Return the Database helper (methods: get_user_token, save_holdings, …).

    Callers must not treat this as a raw pymongo Database — use helper.get_db()
    if you need the pymongo db object.
    """
    return db_instance
