"""
Database seeding script - Populate initial data
Run this to setup admin hierarchy and sample data
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.database import db
from datetime import datetime
from bson import ObjectId
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def seed_admin_hierarchy():
    """Seed administrative hierarchy for Andhra Pradesh"""
    logger.info("Seeding admin_hierarchy collection...")
    
    admin_units = [
        # Districts
        {
            "_id": "DIST_VSP",
            "unit_id": "DIST_VSP",
            "type": "District",
            "name_english": "Visakhapatnam",
            "name_telugu": "విశాఖపట్నం",
            "parent_id": None,
            "boundary": None,  # Add GeoJSON polygon if available
            "created_at": datetime.utcnow(),
            "active": True
        },
        {
            "_id": "DIST_VJA",
            "unit_id": "DIST_VJA",
            "type": "District",
            "name_english": "Vijayawada",
            "name_telugu": "విజయవాడ",
            "parent_id": None,
            "boundary": None,
            "created_at": datetime.utcnow(),
            "active": True
        },
        
        # Mandals under Visakhapatnam
        {
            "_id": "MNDL_VSP_PDT",
            "unit_id": "MNDL_VSP_PDT",
            "type": "Mandal",
            "name_english": "Pedagantyada",
            "name_telugu": "పెడగంత్యాడ",
            "parent_id": "DIST_VSP",
            "boundary": None,
            "created_at": datetime.utcnow(),
            "active": True
        },
        {
            "_id": "MNDL_VSP_MVP",
            "unit_id": "MNDL_VSP_MVP",
            "type": "Mandal",
            "name_english": "Madhurawada",
            "name_telugu": "మధురవాడ",
            "parent_id": "DIST_VSP",
            "boundary": None,
            "created_at": datetime.utcnow(),
            "active": True
        },
        
        # Secretariats under Pedagantyada Mandal
        {
            "_id": "SCRT_VSP_PDT_001",
            "unit_id": "SCRT_VSP_PDT_001",
            "type": "Secretariat",
            "name_english": "Gandhi Nagar Secretariat",
            "name_telugu": "గాంధీ నగర్ సచివాలయం",
            "parent_id": "MNDL_VSP_PDT",
            "boundary": {
                "type": "Polygon",
                "coordinates": [[
                    [83.2185, 17.7231],
                    [83.2285, 17.7231],
                    [83.2285, 17.7331],
                    [83.2185, 17.7331],
                    [83.2185, 17.7231]
                ]]
            },
            "created_at": datetime.utcnow(),
            "active": True
        },
        {
            "_id": "SCRT_VSP_PDT_002",
            "unit_id": "SCRT_VSP_PDT_002",
            "type": "Secretariat",
            "name_english": "Kamma Rajuvari Street Secretariat",
            "name_telugu": "కమ్మ రాజువారి వీధి సచివాలయం",
            "parent_id": "MNDL_VSP_PDT",
            "boundary": {
                "type": "Polygon",
                "coordinates": [[
                    [83.2085, 17.7131],
                    [83.2185, 17.7131],
                    [83.2185, 17.7231],
                    [83.2085, 17.7231],
                    [83.2085, 17.7131]
                ]]
            },
            "created_at": datetime.utcnow(),
            "active": True
        }
    ]
    
    collection = db.admin_hierarchy()
    
    # Clear existing data
    await collection.delete_many({})
    
    # Insert new data
    result = await collection.insert_many(admin_units)
    logger.info(f"✓ Inserted {len(result.inserted_ids)} admin units")


async def seed_officials():
    """Seed sample officials/officers"""
    logger.info("Seeding officials collection...")
    
    officials = [
        {
            "_id": ObjectId(),
            "employee_id": "EMP001",
            "full_name": "Ramesh Kumar",
            "designation": "Sanitation Officer",
            "mobile": "9876543210",
            "email": "ramesh.kumar@ap.gov.in",
            "jurisdiction_level": "Secretariat",
            "jurisdiction_unit_id": "SCRT_VSP_PDT_001",
            "jurisdiction_details": {
                "district": "Visakhapatnam",
                "mandal": "Pedagantyada",
                "secretariat_name": "Gandhi Nagar Secretariat"
            },
            "department": "Sanitation",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "active": True
        },
        {
            "_id": ObjectId(),
            "employee_id": "EMP002",
            "full_name": "Lakshmi Devi",
            "designation": "Electrical Engineer",
            "mobile": "9876543211",
            "email": "lakshmi.devi@ap.gov.in",
            "jurisdiction_level": "Mandal",
            "jurisdiction_unit_id": "MNDL_VSP_PDT",
            "jurisdiction_details": {
                "district": "Visakhapatnam",
                "mandal": "Pedagantyada",
                "secretariat_name": None
            },
            "department": "Electrical",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "active": True
        },
        {
            "_id": ObjectId(),
            "employee_id": "EMP003",
            "full_name": "Suresh Babu",
            "designation": "Road Maintenance Officer",
            "mobile": "9876543212",
            "email": "suresh.babu@ap.gov.in",
            "jurisdiction_level": "Secretariat",
            "jurisdiction_unit_id": "SCRT_VSP_PDT_002",
            "jurisdiction_details": {
                "district": "Visakhapatnam",
                "mandal": "Pedagantyada",
                "secretariat_name": "Kamma Rajuvari Street Secretariat"
            },
            "department": "Road Maintenance",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "active": True
        }
    ]
    
    collection = db.officials()
    
    # Clear existing data
    await collection.delete_many({})
    
    # Insert new data
    result = await collection.insert_many(officials)
    logger.info(f"✓ Inserted {len(result.inserted_ids)} officials")


async def seed_citizens():
    """Seed sample citizens"""
    logger.info("Seeding citizens collection...")
    
    import hashlib
    
    citizens = [
        {
            "_id": ObjectId(),
            "aadhaar_hash": hashlib.sha256("123456789012".encode()).hexdigest(),
            "full_name": "Venkata Rao",
            "mobile": "9876541111",
            "email": "venkata.rao@example.com",
            "preferred_language": "te",
            "saved_locations": [
                {
                    "location_id": "SCRT_VSP_PDT_001",
                    "label": "Home",
                    "geo": {
                        "type": "Point",
                        "coordinates": [83.2235, 17.7281]
                    },
                    "secretariat_id": "SCRT_VSP_PDT_001",
                    "details": {
                        "district": "Visakhapatnam",
                        "mandal": "Pedagantyada",
                        "secretariat_name": "Gandhi Nagar Secretariat"
                    }
                }
            ],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "active": True
        },
        {
            "_id": ObjectId(),
            "aadhaar_hash": hashlib.sha256("123456789013".encode()).hexdigest(),
            "full_name": "Sita Devi",
            "mobile": "9876541112",
            "email": "sita.devi@example.com",
            "preferred_language": "te",
            "saved_locations": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "active": True
        }
    ]
    
    collection = db.citizens()
    
    # Clear existing data
    await collection.delete_many({})
    
    # Insert new data
    result = await collection.insert_many(citizens)
    logger.info(f"✓ Inserted {len(result.inserted_ids)} citizens")


async def main():
    """Main seeding function"""
    try:
        logger.info("Starting database seeding...")
        
        # Connect to database
        await db.connect_db()
        
        # Seed collections
        await seed_admin_hierarchy()
        await seed_officials()
        await seed_citizens()
        
        logger.info("✅ Database seeding completed successfully!")
        
        # Print stats
        stats = await db.get_collection_stats()
        logger.info(f"\nCollection counts:")
        for collection, count in stats.items():
            logger.info(f"  {collection}: {count}")
        
    except Exception as e:
        logger.error(f"❌ Seeding failed: {e}")
        raise
    finally:
        await db.close_db()


if __name__ == "__main__":
    asyncio.run(main())