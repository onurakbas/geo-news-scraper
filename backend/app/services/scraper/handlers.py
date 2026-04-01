import logging
from twisted.internet import defer

from curl_cffi.requests import AsyncSession
from scrapy.http import HtmlResponse, Request

logger = logging.getLogger(__name__)

class CurlCffiDownloadHandler:
    """
    A custom Scrapy Download Handler that uses `curl_cffi`.
    Spoofs Chrome TLS signatures to natively bypass Turnstile without UI.
    """
    lazy = False
    
    def __init__(self, settings, crawler=None) -> None:
        self.settings = settings
        self.crawler = crawler
        # Use a singleton session! Real browsers reuse HTTP/2 TLS connections.
        # Spinning up new identical TLS sessions concurrently triggers Cloudflare botnet alarms.
        self.session = AsyncSession(impersonate="chrome124", verify=False)

    @classmethod
    def from_crawler(cls, crawler) -> "CurlCffiDownloadHandler":
        return cls(crawler.settings, crawler)

    async def download_request(self, request: Request) -> HtmlResponse:
        # Scrapy injects basic User-Agent and Accept headers which conflict with
        # the perfect 'chrome124' impersonation profile of curl_cffi.
        # We ONLY forward explicit operational headers.
        allowed_headers = {"cookie", "referer", "authorization", "content-type"}
        headers = {}
        for k, v in request.headers.items():
            key_lower = k.decode('utf-8').lower()
            if key_lower in allowed_headers:
                headers[key_lower] = v[0].decode('utf-8')
                
        timeout = self.settings.getint("DOWNLOAD_TIMEOUT", 120)
        
        # Scrapy passes `b''` for GET requests. If we pass `data=b''` to curl_cffi, 
        # it might attach a `Content-Length: 0` header which Chrome mathematically 
        # never does for GET requests. This is a fatal Turnstile red flag.
        request_data = request.body if request.body else None
        
        try:
            resp = await self.session.request(
                method=request.method,
                url=request.url,
                headers=headers,
                data=request_data,
                allow_redirects=False,
                timeout=timeout
            )
        except Exception as e:
            logger.error(f"[curl_cffi] Failed to fetch {request.url}: {e}")
            raise e
        
        # curl_cffi auto-decompresses payloads but leaves the header.
        # We strip it so Scrapy doesn't double-decompress and crash!
        resp_headers = dict(resp.headers)
        resp_headers.pop("Content-Encoding", None)
        resp_headers.pop("content-encoding", None)
        
        return HtmlResponse(
            url=str(resp.url),
            status=resp.status_code,
            headers=resp_headers,
            body=resp.content,
            request=request
        )

    async def close(self):
        if self.session:
            await self.session.close()
