# pylint: disable=no-name-in-module
# pylint: disable=too-few-public-methods
import logging
import time

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ffci.server.exception import Forbidden
from ffci.version import VERSION

router = APIRouter()

logger = logging.getLogger(__name__)


class VersionResp(BaseModel):
    version: str = Field(...)


@router.get("/", tags=["info"])
async def index():
    return await version()


@router.get("/error", tags=["debug"])
async def gen_error():
    raise Forbidden("test")


@router.get("/error_uncatched", tags=["debug"])
async def gen_error_uncatch():
    raise Exception()


@router.get("/slow", tags=["debug"])
async def slow_req():
    time.sleep(5)
    return {"ok": 200}


@router.get("/version", tags=["info"], response_model=VersionResp)
async def version() -> VersionResp:
    return VersionResp(version=VERSION.app_version)
