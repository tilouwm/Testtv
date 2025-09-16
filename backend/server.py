from fastapi import FastAPI, APIRouter, HTTPException, Query
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI(title="Live TV Streaming API", version="1.0.0")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Models
class Channel(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    logo: str
    stream: str
    category: str = "General"
    description: Optional[str] = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ChannelCreate(BaseModel):
    name: str
    logo: str
    stream: str
    category: str = "General"
    description: Optional[str] = None

class ChannelUpdate(BaseModel):
    name: Optional[str] = None
    logo: Optional[str] = None
    stream: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

class UserFavorites(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    channel_ids: List[str] = []
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class UserFavoritesUpdate(BaseModel):
    channel_ids: List[str]

# Channel Management APIs
@api_router.get("/")
async def root():
    return {"message": "Live TV Streaming API", "version": "1.0.0"}

@api_router.get("/channels", response_model=List[Channel])
async def get_channels(
    category: Optional[str] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search in channel names"),
    active_only: bool = Query(True, description="Show only active channels")
):
    """Get all channels with optional filtering"""
    try:
        # Build filter query
        filter_query = {}
        if active_only:
            filter_query["is_active"] = True
        if category:
            filter_query["category"] = {"$regex": category, "$options": "i"}
        if search:
            filter_query["name"] = {"$regex": search, "$options": "i"}
        
        channels = await db.channels.find(filter_query).to_list(1000)
        return [Channel(**channel) for channel in channels]
    except Exception as e:
        logging.error(f"Error fetching channels: {e}")
        raise HTTPException(status_code=500, detail="Error fetching channels")

@api_router.post("/channels", response_model=Channel)
async def create_channel(channel: ChannelCreate):
    """Create a new channel"""
    try:
        channel_dict = channel.dict()
        channel_obj = Channel(**channel_dict)
        await db.channels.insert_one(channel_obj.dict())
        return channel_obj
    except Exception as e:
        logging.error(f"Error creating channel: {e}")
        raise HTTPException(status_code=500, detail="Error creating channel")

@api_router.get("/channels/{channel_id}", response_model=Channel)
async def get_channel(channel_id: str):
    """Get a specific channel by ID"""
    try:
        channel = await db.channels.find_one({"id": channel_id})
        if not channel:
            raise HTTPException(status_code=404, detail="Channel not found")
        return Channel(**channel)
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error fetching channel: {e}")
        raise HTTPException(status_code=500, detail="Error fetching channel")

@api_router.put("/channels/{channel_id}", response_model=Channel)
async def update_channel(channel_id: str, channel_update: ChannelUpdate):
    """Update a channel"""
    try:
        update_data = {k: v for k, v in channel_update.dict().items() if v is not None}
        if not update_data:
            raise HTTPException(status_code=400, detail="No valid fields to update")
        
        result = await db.channels.update_one(
            {"id": channel_id}, 
            {"$set": update_data}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Channel not found")
        
        updated_channel = await db.channels.find_one({"id": channel_id})
        return Channel(**updated_channel)
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error updating channel: {e}")
        raise HTTPException(status_code=500, detail="Error updating channel")

@api_router.delete("/channels/{channel_id}")
async def delete_channel(channel_id: str):
    """Delete a channel"""
    try:
        result = await db.channels.delete_one({"id": channel_id})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Channel not found")
        return {"message": "Channel deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error deleting channel: {e}")
        raise HTTPException(status_code=500, detail="Error deleting channel")

@api_router.get("/categories")
async def get_categories():
    """Get all available channel categories"""
    try:
        pipeline = [
            {"$group": {"_id": "$category", "count": {"$sum": 1}}},
            {"$sort": {"_id": 1}}
        ]
        categories = await db.channels.aggregate(pipeline).to_list(100)
        return [{"name": cat["_id"], "count": cat["count"]} for cat in categories]
    except Exception as e:
        logging.error(f"Error fetching categories: {e}")
        raise HTTPException(status_code=500, detail="Error fetching categories")

# User Favorites APIs
@api_router.get("/favorites/{user_id}", response_model=UserFavorites)
async def get_user_favorites(user_id: str):
    """Get user's favorite channels"""
    try:
        favorites = await db.favorites.find_one({"user_id": user_id})
        if not favorites:
            # Create empty favorites for new user
            favorites_obj = UserFavorites(user_id=user_id, channel_ids=[])
            await db.favorites.insert_one(favorites_obj.dict())
            return favorites_obj
        return UserFavorites(**favorites)
    except Exception as e:
        logging.error(f"Error fetching favorites: {e}")
        raise HTTPException(status_code=500, detail="Error fetching favorites")

@api_router.put("/favorites/{user_id}", response_model=UserFavorites)
async def update_user_favorites(user_id: str, favorites_update: UserFavoritesUpdate):
    """Update user's favorite channels"""
    try:
        update_data = {
            "channel_ids": favorites_update.channel_ids,
            "updated_at": datetime.utcnow()
        }
        
        result = await db.favorites.update_one(
            {"user_id": user_id},
            {"$set": update_data},
            upsert=True
        )
        
        favorites = await db.favorites.find_one({"user_id": user_id})
        return UserFavorites(**favorites)
    except Exception as e:
        logging.error(f"Error updating favorites: {e}")
        raise HTTPException(status_code=500, detail="Error updating favorites")

@api_router.post("/favorites/{user_id}/toggle/{channel_id}")
async def toggle_favorite(user_id: str, channel_id: str):
    """Toggle a channel in user's favorites"""
    try:
        favorites = await db.favorites.find_one({"user_id": user_id})
        if not favorites:
            favorites = {"user_id": user_id, "channel_ids": []}
        
        channel_ids = favorites.get("channel_ids", [])
        if channel_id in channel_ids:
            channel_ids.remove(channel_id)
            action = "removed"
        else:
            channel_ids.append(channel_id)
            action = "added"
        
        await db.favorites.update_one(
            {"user_id": user_id},
            {"$set": {"channel_ids": channel_ids, "updated_at": datetime.utcnow()}},
            upsert=True
        )
        
        return {"message": f"Channel {action} from favorites", "channel_id": channel_id}
    except Exception as e:
        logging.error(f"Error toggling favorite: {e}")
        raise HTTPException(status_code=500, detail="Error toggling favorite")

# Initialize with sample data
@api_router.post("/init-data")
async def initialize_sample_data():
    """Initialize the database with sample Haitian TV channels"""
    try:
        # Check if channels already exist
        existing_count = await db.channels.count_documents({})
        if existing_count > 0:
            return {"message": "Data already initialized", "channels": existing_count}
        
        sample_channels = [
            {"name": "Tele Pacific", "logo": "https://static.wikia.nocookie.net/logopedia/images/e/e6/Radio_T%C3%A9l%C3%A9_Pacific_Logo.png", "stream": "https://hls-p1st0n8r.livepush.io/live_cdn/nsOk3qoty1d5HDD/emB7xoUdyMbnjH8/tracks-v1a1/mono.m3u8", "category": "News"},
            {"name": "Tele Ginen", "logo": "https://static.wikia.nocookie.net/logopedia/images/0/09/RTG_Logo_%28With_Full_Name%29.png", "stream": "http://teleginen.srfms.com:1935/teleginen/livestream/chunklist_w531595620.m3u8", "category": "General"},
            {"name": "Haiti News", "logo": "https://m.media-amazon.com/images/I/611Ffvky5yL.png", "stream": "https://haititivi.com/website/haitinews/index.m3u8", "category": "News"},
            {"name": "Ayiti TV", "logo": "https://m.media-amazon.com/images/I/61k8Qk5j9-L.png", "stream": "http://fuego-iptv.net:80/play/live.php?mac=00:1A:79:7d:b0:58&stream=276315&extension=ts&play_token=G01xkhIy81", "category": "General"},
            {"name": "Telemix", "logo": "https://i.ibb.co/RB7dzZq/logo-mix-2.png", "stream": "https://haititivi.com/haiti/telemix1/tracks-v1a1/mono.m3u8", "category": "Entertainment"},
            {"name": "SNL", "logo": "https://i.ibb.co/2NW7kFM/images.jpg", "stream": "https://haititivi.com/haititv/tvs/mono.m3u8", "category": "General"},
            {"name": "Kajou TV", "logo": "https://static.wixstatic.com/media/d205b7_ced5950afd8849e2b21a72f36b3a16ff~mv2.png", "stream": "https://video1.getstreamhosting.com:1936/8055/8055/chunklist_w1507178321.m3u8", "category": "Entertainment"},
            {"name": "RTH 2000", "logo": "https://i.imgur.com/4z0FiEA.png", "stream": "https://2-fss-2.streamhoster.com/pl_120/amlst:206708-4203440/chunklist_b3500000.m3u8", "category": "General"},
            {"name": "Radio Tele Puissance", "logo": "https://radiotelepuissance.com/wp-content/uploads/2020/08/cropped-radio-logo-1.png", "stream": "https://video1.getstreamhosting.com:1936/8560/8560/chunklist_w486676635.m3u8", "category": "General"},
            {"name": "4Diaspo TV", "logo": "https://m.media-amazon.com/images/I/71w9kTfB7xL.png", "stream": "https://59d39900ebfb8.streamlock.net/4DIASPOTV/4DIASPOTV/chunklist_w507710567.m3u8", "category": "General"},
            {"name": "Tele Pam", "logo": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTabRikF9IncQwcgdXkg3Xu2TwVwrnIHbZdjA&s", "stream": "https://lakay.online/ott/telepam/tracks-v1a1/mono.m3u8", "category": "General"},
            {"name": "Trace Urban", "logo": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5c/Trace_Urban_logo_2010.svg/2560px-Trace_Urban_logo_2010.svg.png", "stream": "https://lightning-traceurban-samsungau.amagi.tv/playlist.m3u8", "category": "Music"},
            {"name": "Trace Latina", "logo": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/04/TRACE_Latina_Logo.png/1280px-TRACE_Latina_Logo.png", "stream": "https://cdn-ue1-prod.tsv2.amagi.tv/linear/amg01131-tracetv-tracelatinait-samsungit/playlist.m3u8", "category": "Music"},
            {"name": "Bblack Caribbean", "logo": "https://i1.wp.com/vjdid.com/wp-content/uploads/2017/10/logo-bblack-caribbean-contour-noir.png", "stream": "https://edge16.vedge.infomaniak.com/livecast/ik:bblackcaribbean/chunklist_w2059905249.m3u8", "category": "Music"},
            {"name": "Tele Louange", "logo": "https://images.givelively.org/nonprofits/cb2020c9-71c2-4920-ad32-36f63bd7aef6/logos/christian-multi-media-network_processed_96612ebe1aaa555d1ff9fcfdde6a3ca3be40c8313_logo.png", "stream": "https://5790d294af2dc.streamlock.net/8124/8124/chunklist_w1901943944.m3u8", "category": "Religious"}
        ]
        
        channels_to_insert = []
        for channel_data in sample_channels:
            channel = Channel(**channel_data)
            channels_to_insert.append(channel.dict())
        
        result = await db.channels.insert_many(channels_to_insert)
        return {"message": "Sample data initialized successfully", "channels_created": len(result.inserted_ids)}
    except Exception as e:
        logging.error(f"Error initializing data: {e}")
        raise HTTPException(status_code=500, detail="Error initializing data")

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()