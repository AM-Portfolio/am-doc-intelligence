import os
import pymongo
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

    def save_user_token(self, user_id, token_data):
        """Save user OAuth token (pickled binary) to MongoDB"""
        db = self.get_db()
        collection = db['user_tokens']
        
        # Upsert token
        result = collection.update_one(
            {'user_id': user_id},
            {'$set': {
                'token_data': token_data,
                'updated_at': datetime.utcnow()
            }},
            upsert=True
        )
        logger.info(f"Saved token for user {user_id}. Modified count: {result.modified_count}, Upserted ID: {result.upserted_id}")

    def get_user_token(self, user_id):
        """Retrieve user OAuth token (pickled binary)"""
        db = self.get_db()
        collection = db['user_tokens']
        
        doc = collection.find_one({'user_id': user_id})
        if doc:
            logger.info(f"Token found for user {user_id}")
        else:
            logger.warning(f"No token found in DB for user {user_id}")
            
        if doc and 'token_data' in doc:
            return doc['token_data']
        return None

    def delete_user_token(self, user_id):
        """Delete user OAuth token"""
        db = self.get_db()
        collection = db['user_tokens']
        result = collection.delete_one({'user_id': user_id})
        logger.info(f"Deleted token for user {user_id}. Deleted count: {result.deleted_count}")

# Global instance
db_instance = Database()

def get_db():
    return db_instance
