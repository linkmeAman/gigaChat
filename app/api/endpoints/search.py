from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
import httpx
import json
import redis
from datetime import datetime, timedelta
import backoff
from circuitbreaker import circuit
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.models.auth import User

router = APIRouter()

# Initialize Redis for caching
redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=0,
    decode_responses=True
)

class SearchClient:
    def __init__(self):
        self.base_url = settings.SEARXNG_URL
        self.timeout = settings.SEARCH_TIMEOUT_MS / 1000  # Convert to seconds
        self.cache_ttl = settings.SEARCH_CACHE_SECONDS

    @circuit(failure_threshold=5, recovery_timeout=60)
    @backoff.on_exception(
        backoff.expo,
        (httpx.TimeoutException, httpx.RequestError),
        max_tries=3
    )
    async def search(self, query: str, page: int = 1) -> List[dict]:
        """
        Perform a search using SearxNG with circuit breaker and caching.
        """
        # Check cache first
        cache_key = f"search:{query}:{page}"
        cached_result = redis_client.get(cache_key)
        if cached_result:
            return json.loads(cached_result)

        # If not in cache, perform search
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            params = {
                "q": query,
                "format": "json",
                "pageno": page,
                "engines": "google,wikipedia,arxiv",  # Free engines only
                "language": "en",
                "max_results": 10
            }
            
            response = await client.get(
                f"{self.base_url}/search",
                params=params
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Search engine error"
                )
            
            results = response.json()["results"]
            
            # Cache the results
            redis_client.setex(
                cache_key,
                self.cache_ttl,
                json.dumps(results)
            )
            
            return results

    async def wikipedia_search(self, query: str) -> Optional[dict]:
        """
        Perform a targeted Wikipedia search.
        """
        cache_key = f"wiki:{query}"
        cached_result = redis_client.get(cache_key)
        if cached_result:
            return json.loads(cached_result)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            params = {
                "q": f"site:wikipedia.org {query}",
                "format": "json",
                "engines": "wikipedia"
            }
            
            response = await client.get(
                f"{self.base_url}/search",
                params=params
            )
            
            if response.status_code != 200:
                return None
            
            results = response.json()["results"]
            if results:
                result = results[0]
                redis_client.setex(
                    cache_key,
                    self.cache_ttl,
                    json.dumps(result)
                )
                return result
            
            return None

    async def arxiv_search(self, query: str) -> List[dict]:
        """
        Search academic papers on ArXiv.
        """
        cache_key = f"arxiv:{query}"
        cached_result = redis_client.get(cache_key)
        if cached_result:
            return json.loads(cached_result)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            params = {
                "q": f"site:arxiv.org {query}",
                "format": "json",
                "engines": "arxiv",
                "max_results": 5
            }
            
            response = await client.get(
                f"{self.base_url}/search",
                params=params
            )
            
            if response.status_code != 200:
                return []
            
            results = response.json()["results"]
            redis_client.setex(
                cache_key,
                self.cache_ttl,
                json.dumps(results)
            )
            
            return results

# Initialize global search client
search_client = SearchClient()

@router.get("/search")
async def search(
    query: str,
    page: int = 1,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Perform a general web search.
    """
    try:
        results = await search_client.search(query, page)
        return {"results": results}
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail="Search service unavailable"
        )

@router.get("/search/wikipedia")
async def wikipedia_search(
    query: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Search specifically on Wikipedia.
    """
    result = await search_client.wikipedia_search(query)
    if not result:
        raise HTTPException(
            status_code=404,
            detail="No Wikipedia results found"
        )
    return result

@router.get("/search/arxiv")
async def arxiv_search(
    query: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Search academic papers on ArXiv.
    """
    results = await search_client.arxiv_search(query)
    return {"results": results}

@router.get("/search/health")
async def health_check():
    """
    Check the health of the search service.
    """
    try:
        # Attempt a simple search
        result = await search_client.search("test", 1)
        return {"status": "healthy", "message": "Search service is operational"}
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Search service is unhealthy: {str(e)}"
        )