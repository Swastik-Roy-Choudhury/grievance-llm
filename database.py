"""
MongoDB database connection and operations - UPDATED
"""
from __future__ import annotations
from typing import Optional, Dict, Any
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
import logging
from app.config import settings

logger = logging.getLogger(__name__)


class Database:
    """Database connection manager with collection helpers"""
    
    client: Optional[AsyncIOMotorClient] = None
    db: Optional[AsyncIOMotorDatabase] = None
    
    # Collection names as constants
    GRIEVANCES = "grievances"
    CITIZENS = "citizens"
    OFFICIALS = "officials"
    ADMIN_HIERARCHY = "admin_hierarchy"
    AI_FEEDBACK = "ai_feedback"
    
    @classmethod
    async def connect_db(cls):
        """Connect to MongoDB and setup indexes"""
        try:
            cls.client = AsyncIOMotorClient(settings.MONGODB_URL)
            cls.db = cls.client[settings.DATABASE_NAME]
            
            # Test connection
            await cls.client.admin.command('ping')
            logger.info(f"Connected to MongoDB at {settings.MONGODB_URL}")
            
            # Setup indexes for performance
            await cls._setup_indexes()
            logger.info("Database indexes created successfully")
            
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
    
    @classmethod
    async def _setup_indexes(cls):
        """
        Create indexes for optimal query performance
        Based on RW-Frequency from PDF (Very High Read operations need indexes)
        """
        try:
            # GRIEVANCES Collection Indexes
            grievances = cls.db[cls.GRIEVANCES]
            
            # Primary lookups
            await grievances.create_index("grievance_id", unique=True)
            await grievances.create_index("citizen_id")
            
            # Dashboard filtering (Very High Read frequency)
            await grievances.create_index([("status", 1), ("created_at", -1)])
            await grievances.create_index([("department_id", 1), ("status", 1)])
            await grievances.create_index([("assigned_to", 1), ("status", 1)])
            await grievances.create_index([("priority", 1), ("created_at", -1)])
            
            # Geospatial routing (Very High Read - AI constantly queries)
            await grievances.create_index([("location.geo", "2dsphere")])
            await grievances.create_index("location.secretariat_id")
            
            # Duplicate detection & similarity search
            await grievances.create_index("duplicate_of_id")
            
            # SLA tracking
            await grievances.create_index([("sla_due_date", 1), ("status", 1)])
            
            logger.info("✓ Grievances indexes created")
            
            # CITIZENS Collection Indexes
            citizens = cls.db[cls.CITIZENS]
            await citizens.create_index("aadhaar_hash", unique=True)
            await citizens.create_index("mobile")
            await citizens.create_index("email")
            logger.info("✓ Citizens indexes created")
            
            # OFFICIALS Collection Indexes
            officials = cls.db[cls.OFFICIALS]
            await officials.create_index("employee_id", unique=True)
            await officials.create_index([("jurisdiction_level", 1), ("jurisdiction_unit_id", 1)])
            await officials.create_index("department")
            await officials.create_index("email", unique=True)
            logger.info("✓ Officials indexes created")
            
            # ADMIN_HIERARCHY Collection Indexes
            admin_hierarchy = cls.db[cls.ADMIN_HIERARCHY]
            await admin_hierarchy.create_index("unit_id", unique=True)
            await admin_hierarchy.create_index("type")
            await admin_hierarchy.create_index("parent_id")
            # Geospatial index for boundary polygons
            await admin_hierarchy.create_index([("boundary", "2dsphere")])
            logger.info("✓ Admin Hierarchy indexes created")
            
            # AI_FEEDBACK Collection Indexes
            ai_feedback = cls.db[cls.AI_FEEDBACK]
            await ai_feedback.create_index("grievance_id")
            await ai_feedback.create_index("corrected_by")
            await ai_feedback.create_index([("used_for_training", 1), ("created_at", -1)])
            logger.info("✓ AI Feedback indexes created")
            
        except Exception as e:
            logger.error(f"Error creating indexes: {e}")
            # Don't fail startup if indexes exist
    
    @classmethod
    async def close_db(cls):
        """Close MongoDB connection"""
        if cls.client:
            cls.client.close()
            logger.info("Closed MongoDB connection")
    
    @classmethod
    def get_database(cls) -> AsyncIOMotorDatabase:
        """Get database instance"""
        if cls.db is None:
            raise Exception("Database not connected")
        return cls.db
    
    @classmethod
    def get_collection(cls, collection_name: str):
        """Get collection from database"""
        if cls.db is None:
            raise Exception("Database not connected")
        return cls.db[collection_name]
    
    # ===== Collection Helper Methods =====
    
    @classmethod
    def grievances(cls):
        """Get grievances collection"""
        return cls.get_collection(cls.GRIEVANCES)
    
    @classmethod
    def citizens(cls):
        """Get citizens collection"""
        return cls.get_collection(cls.CITIZENS)
    
    @classmethod
    def officials(cls):
        """Get officials collection"""
        return cls.get_collection(cls.OFFICIALS)
    
    @classmethod
    def admin_hierarchy(cls):
        """Get admin_hierarchy collection"""
        return cls.get_collection(cls.ADMIN_HIERARCHY)
    
    @classmethod
    def ai_feedback(cls):
        """Get ai_feedback collection"""
        return cls.get_collection(cls.AI_FEEDBACK)
    
    # ===== Utility Methods =====
    
    @classmethod
    async def get_collection_stats(cls) -> Dict[str, int]:
        """Get document counts for all collections (for health check)"""
        try:
            stats = {}
            for collection_name in [cls.GRIEVANCES, cls.CITIZENS, cls.OFFICIALS, 
                                   cls.ADMIN_HIERARCHY, cls.AI_FEEDBACK]:
                collection = cls.get_collection(collection_name)
                count = await collection.count_documents({})
                stats[collection_name] = count
            return stats
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {}
    
    @classmethod
    async def health_check(cls) -> Dict[str, Any]:
        """Comprehensive health check"""
        try:
            # Ping database
            await cls.client.admin.command('ping')
            
            # Get collection stats
            stats = await cls.get_collection_stats()
            
            return {
                "connected": True,
                "database": settings.DATABASE_NAME,
                "collections": stats,
                "status": "healthy"
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "connected": False,
                "error": str(e),
                "status": "unhealthy"
            }
    
    @classmethod
    async def generate_grievance_id(cls, district_code: str, year: int = None) -> str:
        """
        Generate unique grievance ID in format: AP-{DISTRICT}-{SEQUENTIAL}-{YEAR}
        Example: AP-VSP-00001-2026
        """
        from datetime import datetime
        
        if year is None:
            year = datetime.utcnow().year
        
        # Find the last grievance ID for this district and year
        pattern = f"AP-{district_code}-.*-{year}"
        last_grievance = await cls.grievances().find_one(
            {"grievance_id": {"$regex": pattern}},
            sort=[("created_at", -1)]
        )
        
        if last_grievance:
            # Extract sequence number and increment
            parts = last_grievance["grievance_id"].split("-")
            sequence = int(parts[2]) + 1
        else:
            sequence = 1
        
        return f"AP-{district_code}-{sequence:05d}-{year}"


# Global database instance
db = Database()


# ===== Helper Functions for Common Queries =====

async def find_grievance_by_id(grievance_id: str) -> Optional[Dict[str, Any]]:
    """Find grievance by readable ID"""
    return await db.grievances().find_one({"grievance_id": grievance_id})


async def find_citizen_by_aadhaar(aadhaar_hash: str) -> Optional[Dict[str, Any]]:
    """Find citizen by Aadhaar hash"""
    return await db.citizens().find_one({"aadhaar_hash": aadhaar_hash})


async def find_official_by_employee_id(employee_id: str) -> Optional[Dict[str, Any]]:
    """Find official by employee ID"""
    return await db.officials().find_one({"employee_id": employee_id})


async def find_secretariat_by_location(longitude: float, latitude: float) -> Optional[Dict[str, Any]]:
    """
    Find secretariat containing the given coordinates
    Uses geospatial query on boundary polygons
    """
    return await db.admin_hierarchy().find_one({
        "type": "Secretariat",
        "boundary": {
            "$geoIntersects": {
                "$geometry": {
                    "type": "Point",
                    "coordinates": [longitude, latitude]
                }
            }
        }
    })


async def find_officials_by_jurisdiction(jurisdiction_unit_id: str) -> list:
    """Find all officials for a specific jurisdiction"""
    cursor = db.officials().find({
        "jurisdiction_unit_id": jurisdiction_unit_id,
        "active": True
    })
    return await cursor.to_list(length=100)


async def create_ai_feedback(grievance_id: str, officer_id: str, officer_name: str,
                            original_prediction: Dict[str, Any],
                            correction: Dict[str, Any], reason: str) -> str:
    """Create RLHF feedback entry"""
    from datetime import datetime
    from bson import ObjectId
    
    feedback_doc = {
        "_id": ObjectId(),
        "grievance_id": grievance_id,
        "corrected_by": officer_id,
        "corrected_by_name": officer_name,
        "original_prediction": original_prediction,
        "human_correction": {
            **correction,
            "reason": reason
        },
        "created_at": datetime.utcnow(),
        "used_for_training": False
    }
    
    result = await db.ai_feedback().insert_one(feedback_doc)
    return str(result.inserted_id)