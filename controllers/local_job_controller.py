import json
import uuid
import random
from datetime import datetime, timezone

from fastapi import Request, UploadFile
from schemas.local_job_schemas import GetLocalJobApplicationsRequest, GetLocalJobParams, GetLocalJobsbSchema, GetMeLocalJobsRequest, GuestGetLocalJobsSchema, LocalJobApplicationParam, LocalJobIdParam, SearchSuggestionsRequest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, col
from sqlalchemy import func, or_, and_, case, update, delete
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.orm import selectinload

from models.local_jobs.local_job import LocalJob
from models.local_jobs.local_job_image import LocalJobImage
from models.local_jobs.local_job_location import LocalJobLocation
from models.local_jobs.local_job_search_query import LocalJobSearchQuery
from models.local_jobs.local_job_applicant import LocalJobApplicant
from models.user import User
from models.chat_info import ChatInfo
from models.user_locations import UserLocation
from models.user_bookmark_local_jobs import UserBookmarkLocalJob
from config import BASE_URL, PROFILE_BASE_URL, MEDIA_BASE_URL
from helpers.response_helper import send_json_response, send_error_response
from utils.pagination.cursor import encode_cursor, decode_cursor
from utils.aws_s3 import upload_to_s3, delete_from_s3, delete_directory_from_s3
from kafka.notification_service_producer import send_local_job_applicant_applied_notification_to_kafka


# ── Shared helpers ─────────────────────────────────────────────────────────────

def _fmt_url(base, path):
    return f"{base}/{path}" if path else None


def _job_response(
    job:          LocalJob,
    owner:        User,
    images:       list[LocalJobImage],
    location:     LocalJobLocation | None,
    chat:         ChatInfo | None,
    is_bookmarked: bool = False,
    is_applied:   bool = False,
    distance:     float | None = None,
) -> dict:
    return {
        "user": {
            "user_id":               owner.user_id,
            "first_name":            owner.first_name,
            "last_name":             owner.last_name,
            "is_verified":           bool(owner.is_email_verified),
            "profile_pic_url":       _fmt_url(PROFILE_BASE_URL, owner.profile_pic_url),
            "profile_pic_url_small": _fmt_url(PROFILE_BASE_URL, owner.profile_pic_url_96x96),
            "online":                bool(chat.online) if chat else False,
            "joined_at":             str(owner.created_at.year) if owner.created_at else None,
        },
        "local_job": {
            "local_job_id":    job.local_job_id,
            "title":           job.title,
            "description":     job.description,
            "company":         job.company,
            "age_min":         job.age_min,
            "age_max":         job.age_max,
            "marital_statuses": json.loads(job.marital_statuses) if isinstance(job.marital_statuses, str) else job.marital_statuses,
            "salary_unit":     job.salary_unit,
            "salary_min":      job.salary_min,
            "salary_max":      job.salary_max,
            "country":         job.country,
            "state":           job.state,
            "status":          job.status,
            "slug":            f"{BASE_URL}/local-job/{job.short_code}",
            "is_bookmarked":   is_bookmarked,
            "is_applied":      is_applied,
            "distance":        distance,
            "images": [
                {
                    "image_id":  img.id,
                    "image_url": _fmt_url(MEDIA_BASE_URL, img.image_url),
                    "width":     img.width,
                    "height":    img.height,
                    "size":      img.size,
                    "format":    img.format,
                }
                for img in sorted(images, key=lambda x: x.created_at, reverse=True)
            ],
            "location": {
                "longitude":     location.longitude,
                "latitude":      location.latitude,
                "geo":           location.geo,
                "location_type": location.location_type,
            } if location else None,
        }
    }


def _paginate(items: list, last_row, page_size: int, next_token: str = None ) -> dict:
    has_next       = len(items) == page_size and last_row is not None
    next_token_out = encode_cursor({
        "created_at":      str(last_row.created_at),
        "id":              last_row.id,
        "distance":        float(getattr(last_row, "distance", None)) if  getattr(last_row, "distance", None) is not None else None,
        "total_relevance": float( getattr(last_row, "total_relevance", None)) if  getattr(last_row, "total_relevance", None) is not None else None,
    }) if has_next else None
    return {
        "data":           items,
        "next_token":     next_token_out,
        "previous_token": next_token if next_token else None,
    }

def _haversine(lat: float, lon: float):
    return (
        6371 * func.acos(
            func.cos(func.radians(lat)) *
            func.cos(func.radians(LocalJobLocation.latitude)) *
            func.cos(func.radians(LocalJobLocation.longitude) - func.radians(lon)) +
            func.sin(func.radians(lat)) *
            func.sin(func.radians(LocalJobLocation.latitude))
        )
    ).label("distance")

def _relevance(search: str):
    return (
        func.coalesce(func.match(LocalJob.title,             func.against(search)), 0) +
        func.coalesce(func.match(LocalJob.long_description,  func.against(search)), 0)
    ).label("total_relevance")

async def _query_jobs(
    db:        AsyncSession,
    user_id:   int,
    page_size: int,
    query:     str | None = None,
    user_lat:  float | None = None,
    user_lon:  float | None = None,
    next_token: str | None = None,
) -> tuple[list, any]:

    payload = decode_cursor(next_token) if next_token else None
    has_loc = user_lat is not None and user_lon is not None

    if query and not payload:
        stmt = insert(LocalJobSearchQuery).values(
            search_term=query,
            popularity=1,
            last_searched=datetime.now(timezone.utc),
            search_term_concatenated=query.replace(" ", ""),
        )
        stmt = stmt.on_duplicate_key_update(
            popularity=LocalJobSearchQuery.popularity + 1,
            last_searched=datetime.now(timezone.utc),
        )
        await db.execute(stmt)

    cols = [LocalJob]

    if has_loc:
        cols.append(_haversine(user_lat, user_lon))
    if query:
        cols.append(_relevance(query))
    if user_id:
        cols.append(UserBookmarkLocalJob)
        cols.append(LocalJobApplicant)
    q = (
        select(*cols)
        .options(
            selectinload(LocalJob.user),       
            selectinload(LocalJob.chat_info).selectinload(ChatInfo.user),
            selectinload(LocalJob.images),    
            selectinload(LocalJob.location) 
        )
    )

    if user_id:
        q = q.outerjoin(
            UserBookmarkLocalJob,
            and_(
                UserBookmarkLocalJob.local_job_id == LocalJob.local_job_id,
                UserBookmarkLocalJob.user_id == user_id,
            )
        ).outerjoin(
            LocalJobApplicant,
            and_(
                LocalJobApplicant.local_job_id == LocalJob.local_job_id,
                LocalJobApplicant.candidate_id == user_id,
            )
        )

    if query:
        title_rel = func.coalesce(func.match(LocalJob.title,       func.against(query)), 0)
        desc_rel  = func.coalesce(func.match(LocalJob.description, func.against(query)), 0)
        q = q.having(or_(title_rel > 0, desc_rel > 0))

    if payload:
        if has_loc and query:
            dist_expr = _haversine(user_lat, user_lon)
            rel_expr  = _relevance(query)
            q = q.having(or_(
                dist_expr > payload["distance"],
                and_(dist_expr == payload["distance"], rel_expr < payload["total_relevance"]),
                and_(dist_expr == payload["distance"], rel_expr == payload["total_relevance"], LocalJob.created_at < payload["created_at"]),
                and_(dist_expr == payload["distance"], rel_expr == payload["total_relevance"], LocalJob.created_at == payload["created_at"], LocalJob.id > payload["id"]),
            ))
        elif has_loc:
            dist_expr = _haversine(user_lat, user_lon)
            q = q.having(or_(
                dist_expr > payload["distance"],
                and_(dist_expr == payload["distance"], LocalJob.created_at < payload["created_at"]),
                and_(dist_expr == payload["distance"], LocalJob.created_at == payload["created_at"], LocalJob.id > payload["id"]),
            ))
        elif query:
            rel_expr = _relevance(query)
            q = q.having(or_(
                rel_expr < payload["total_relevance"],
                and_(rel_expr == payload["total_relevance"], LocalJob.created_at < payload["created_at"]),
                and_(rel_expr == payload["total_relevance"], LocalJob.created_at == payload["created_at"], LocalJob.id > payload["id"]),
            ))
        else:
            q = q.where(or_(
                LocalJob.created_at < payload["created_at"],
                and_(LocalJob.created_at == payload["created_at"], LocalJob.id > payload["id"]),
            ))

    q = q.group_by(LocalJob.local_job_id)

    if has_loc and query:
        q = q.order_by("distance ASC", "total_relevance DESC", LocalJob.created_at.desc(), LocalJob.id.asc())
    elif has_loc:
        q = q.order_by("distance ASC", LocalJob.created_at.desc(), LocalJob.id.asc())
    elif query:
        q = q.order_by("total_relevance DESC", LocalJob.created_at.desc(), LocalJob.id.asc())
    else:
        q = q.order_by(LocalJob.created_at.desc(), LocalJob.id.asc())

    q = q.limit(page_size)

    result = await db.execute(q)
    rows   = result.all()

    last_row  = None

    if rows:
        last_row = rows[-1]

    return _paginate(rows, last_row, page_size,next_token if payload else None)

    
async def get_local_jobs(
    request: Request,
    schema: GetLocalJobsbSchema,
    db: AsyncSession
):
    try:
        s = schema.s
        page_size = page_size
        next_token = schema.next_token

        user_id = request.state.user.user_id    
        
        loc = await db.scalar(select(UserLocation).where(UserLocation.user_id == user_id))
        lat, lon = (float(loc.latitude), float(loc.longitude)) if loc else (None, None)

        data = await _query_jobs(
            db, page_size, next_token, s, user_id, lat, lon
        )

        return send_json_response(200, "Local jobs fetched", data= data)
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def guest_get_local_jobs(
    request: Request,
    schema: GuestGetLocalJobsSchema,
    db: AsyncSession
):
    try:
    
        return send_json_response(200, "Local jobs fetched", data= None)
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def guest_get_local_job(request: Request, local_job_id: int, db: AsyncSession):
    try:
        job = await db.scalar(
            select(LocalJob)
            .options(
                selectinload(LocalJob.location),
                selectinload(LocalJob.images),
                selectinload(LocalJob.applicants) 
            )
            .where(LocalJob.local_job_id == local_job_id)
        )

        if not job:
            return send_error_response(request, 404, "Local job not exist")

        return send_json_response(200, "Local job retrived", data=_job_response(
            job,
            owner=job.created_by,  
            images=job.images,
            location=job.location,
            chat=None, 
        ))
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def get_local_job(request: Request, params: LocalJobIdParam, db: AsyncSession):
    try:
        user_id = request.state.suer.user_id
        local_job_id = params.local_job_id
        job = await db.scalar(
            select(LocalJob)
            .options(
                selectinload(LocalJob.location),
                selectinload(LocalJob.images),
                selectinload(LocalJob.applicants) 
            )
            .where(LocalJob.local_job_id == local_job_id)
        )

        if not job:
            return send_error_response(request, 404, "Local job not exist")
        
        is_applied = await db.scalar(
        select(LocalJobApplicant)
        .where(LocalJobApplicant.local_job_id == local_job_id)
        .where(LocalJobApplicant.candidate_id == str(user_id))
        ) is not None

        return send_json_response(200, "Local job retrived", data=_job_response(
            job,
            owner=job.created_by,  
            images=job.images,
            location=job.location,
            chat=None, 
            is_applied=bool(is_applied),
        ))
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def apply_local_job(request: Request, params: LocalJobIdParam, db: AsyncSession):
    try:
        user_id = request.state.user_id
        local_job_id = params.local_job_id
        job = await db.scalar(
            select(LocalJob).where(LocalJob.local_job_id == local_job_id)
        )
        if not job:
            return send_error_response(request, 404, "Local job not exist")
        applicant= LocalJobApplicant(
            candidate_id=user_id,
            local_job_id=local_job_id,
        )
        db.add(applicant)
        await db.flush() 
        
        kafka_key = f"{local_job_id}:{job.created_by}:{user_id}"
        send_local_job_applicant_applied_notification_to_kafka(kafka_key, {
            "user_id":         job.created_by,
            "candidate_id":    user_id,
            "local_job_title": job.title,
            "application_id":  applicant.application_id,
        })
        return send_json_response(200, "Applied successfully")
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def create_or_update_local_job(
    request:          Request,
    user_id:          int,
    title:            str,
    description:      str,
    company:          str,
    age_min:          int,
    age_max:          int,
    marital_statuses: list,
    salary_unit:      str,
    salary_min:       int,
    salary_max:       int,
    country:          str,
    state:            str,
    files:            list[UploadFile] | None,
    location_json:    str,
    keep_image_ids:   list[int],
    local_job_id:     int,
    db:               AsyncSession,
):
    uploaded_keys = []
    try:
        media_id = await db.scalar(select(User.media_id).where(User.user_id == user_id))
        if not media_id:
            return send_error_response(request, 400, "Unable to retrieve media_id")

        marital_statuses_json = json.dumps(marital_statuses)

        existing = await db.scalar(
            select(LocalJob).where(
                LocalJob.local_job_id == local_job_id,
                LocalJob.created_by == user_id,
            )
        ) if local_job_id else None

        if existing:
            existing.title            = title
            existing.description      = description
            existing.company          = company
            existing.age_min          = age_min
            existing.age_max          = age_max
            existing.marital_statuses = marital_statuses_json
            existing.salary_unit      = salary_unit
            existing.salary_min       = salary_min
            existing.salary_max       = salary_max
            existing.country          = country
            existing.state            = state
            existing.updated_at       = datetime.now(timezone.utc)
            db.add(existing)
            job_id = existing.local_job_id
        else:
            new_id = await _generate_unique_local_job_id(db)
            new_job = LocalJob(
                local_job_id      = new_id,
                title             = title,
                description       = description,
                company           = company,
                age_min           = age_min,
                age_max           = age_max,
                marital_statuses  = marital_statuses_json,
                salary_unit       = salary_unit,
                salary_min        = salary_min,
                salary_max        = salary_max,
                country           = country,
                state             = state,
                created_by        = user_id,
            )
            db.add(new_job)
            await db.flush()
            job_id = new_job.local_job_id

        # images — delete removed ones
        old_images = (await db.execute(
            select(LocalJobImage).where(LocalJobImage.local_job_id == job_id)
        )).scalars().all()

        for img in old_images:
            if img.id not in keep_image_ids:
                await delete_from_s3(img.image_url)
                await db.delete(img)

        # upload new images
        for file in (files or []):
            contents = await file.read()
            key      = f"media/{media_id}/local-jobs/{job_id}/{uuid.uuid4()}-{file.filename}"
            await upload_to_s3(contents, key, file.content_type)
            uploaded_keys.append(key)
            db.add(LocalJobImage(
                local_job_id = job_id,
                image_url    = key,
                width        = 0,
                height       = 0,
                size         = len(contents),
                format       = file.content_type or "",
            ))

        # location
        location = json.loads(location_json)
        loc = await db.scalar(
            select(LocalJobLocation).where(LocalJobLocation.local_job_id == job_id)
        )
        if loc:
            loc.latitude      = location["latitude"]
            loc.longitude     = location["longitude"]
            loc.geo           = location["geo"]
            loc.location_type = location["location_type"]
            db.add(loc)
        else:
            db.add(LocalJobLocation(
                local_job_id  = job_id,
                latitude      = location["latitude"],
                longitude     = location["longitude"],
                geo           = location["geo"],
                location_type = location["location_type"],
            ))

        await db.flush()

        result = await db.execute(
            select(LocalJob, LocalJobLocation, User)
            .join(LocalJobLocation, LocalJobLocation.local_job_id == LocalJob.local_job_id, isouter=True)
            .join(User, User.user_id == LocalJob.created_by)
            .where(LocalJob.local_job_id == job_id)
        )
        row = result.first()
        job, loc, owner = row
        images = (await db.execute(
            select(LocalJobImage).where(LocalJobImage.local_job_id == job_id).order_by(LocalJobImage.created_at.desc())
        )).scalars().all()

        return send_json_response(200, "Local job saved", data=_job_response(job, owner, images, loc, None))

    except Exception:
        for key in uploaded_keys:
            await delete_from_s3(key)
        return send_error_response(request, 500, "Internal server error")


async def get_me_local_jobs(
    request: Request,
    params: GetMeLocalJobsRequest,
    db: AsyncSession,
):
    user_id = request.state.user_id
    next_token = params.next_token
    page_size = page_size or 20
    payload = decode_cursor(next_token) if next_token else None

    q = (
        select(LocalJob)
        .where(LocalJob.created_by == user_id)
        .options(
            selectinload(LocalJob.images),      
            selectinload(LocalJob.location),   
            selectinload(LocalJob.user),      
        )
    )

    if payload:
        q = q.where(or_(
            LocalJob.created_at < payload["created_at"],
            and_(LocalJob.created_at == payload["created_at"], LocalJob.id > payload["id"]),
        ))

    q = q.order_by(LocalJob.created_at.desc(), LocalJob.id.asc()).limit(page_size)

    jobs = (await db.execute(q)).scalars().all()

    items = [_job_response(job, job.user, job.images, job.location, None) for job in jobs]
    last_row = jobs[-1] if jobs else None

    return send_json_response(
        200,
        "Local jobs retrieved",
        data=_paginate(items, last_row, page_size, next_token, payload)
    )

async def delete_local_job(request: Request, params: LocalJobIdParam, db: AsyncSession):
    try:
        user_id = request.state.user_user_id,
        local_job_id = params.local_job_id,

        job = await db.scalar(
            select(LocalJob).where(LocalJob.local_job_id == local_job_id, LocalJob.created_by == user_id)
        )
        if not job:
            return send_error_response(request, 404, "Local job not exist")

        media_id = await db.scalar(select(User.media_id).where(User.user_id == user_id))

        await db.execute(delete(LocalJobImage).where(LocalJobImage.local_job_id == local_job_id))
        await db.execute(delete(LocalJobLocation).where(LocalJobLocation.local_job_id == local_job_id))
        await db.delete(job)

        if media_id:
            await delete_directory_from_s3(f"media/{media_id}/local-jobs/{local_job_id}")

        return send_json_response(200, "Local job deleted")
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def get_local_job_applications(
    request: Request,
    params: GetLocalJobApplicationsRequest,
    db: AsyncSession,
):
    local_job_id = params.local_job_id,
    page_size = params.page_size
    next_token =  params.next_token

    payload   = decode_cursor(next_token) if next_token else None

    job = await db.scalar(select(LocalJob).where(LocalJob.local_job_id == local_job_id))
    if not job:
        return send_error_response(request, 404, "Local job not exist")

    q = (
        select(LocalJobApplicant)
        .where(LocalJobApplicant.local_job_id == local_job_id)
        .options(selectinload(LocalJobApplicant.user).selectinload(User.location))
    )

    if payload:
        q = q.where(or_(
            LocalJobApplicant.is_reviewed > payload["is_reviewed"],
            and_(LocalJobApplicant.is_reviewed == payload["is_reviewed"],
                 LocalJobApplicant.reviewed_at < payload["reviewed_at"]),
            and_(LocalJobApplicant.is_reviewed == payload["is_reviewed"],
                 LocalJobApplicant.reviewed_at == payload["reviewed_at"],
                 LocalJobApplicant.id > payload["id"]),
        ))

    q = q.order_by(
        LocalJobApplicant.is_reviewed.asc(),
        LocalJobApplicant.reviewed_at.desc(),
        LocalJobApplicant.id.asc(),
    ).limit(page_size)

    rows = (await db.execute(q)).scalars().all()

    items = []
    last_row = None

    for i, applicant in enumerate(rows):
        u  = applicant.user
        ul = u.location if u else None

        items.append({
            "application_id": applicant.application_id,
            "applied_at": applicant.applied_at,
            "is_reviewed": bool(applicant.is_reviewed),
            "contact_info": {
                "email": u.email,
                "phone_country_code": u.phone_country_code,
                "phone_number": u.phone_number,
            } if u else None,
            "user": {
                "user_id": u.user_id,
                "first_name": u.first_name,
                "last_name": u.last_name,
                "email": u.email,
                "is_email_verified": bool(u.is_email_verified),
                "phone_country_code": u.phone_country_code,
                "phone_number": u.phone_number,
                "is_phone_verified": bool(u.is_phone_verified),
                "profile_pic_url": _fmt_url(PROFILE_BASE_URL, u.profile_pic_url),
                "profile_pic_url_96x96": _fmt_url(PROFILE_BASE_URL, u.profile_pic_url_96x96),
                "geo": ul.geo if ul else None,
                "joined_at": str(u.created_at.year) if u.created_at else None,
            } if u else None,
        })
        last_row = applicant

    next_token_out = encode_cursor({
        "is_reviewed": last_row.is_reviewed,
        "reviewed_at": str(last_row.reviewed_at),
        "id": last_row.id,
    }) if len(items) == page_size and last_row else None

    return send_json_response(200, "Applications fetched", data={
        "data": items,
        "next_token": next_token_out,
        "previous_token": next_token if payload else None,
    })

async def mark_as_reviewed(request: Request, params: LocalJobApplicationParam, db: AsyncSession):
    try:
        user_id = request.state.user.user_id
        local_job_id = params.user_id
        application_id = params.application_id
        job = await db.scalar(
            select(LocalJob).where(LocalJob.local_job_id == local_job_id, LocalJob.created_by == user_id)
        )
        if not job:
            return send_error_response(request, 404, "Local job not found")

        await db.execute(
            update(LocalJobApplicant)
            .where(LocalJobApplicant.local_job_id == local_job_id, LocalJobApplicant.application_id == application_id)
            .values(is_reviewed=1, reviewed_at=datetime.now(timezone.utc))
        )
        return send_json_response(200, "Marked as reviewed")
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def unmark_as_reviewed(request: Request, params: LocalJobApplicationParam, db: AsyncSession):
    try:
        user_id = request.state.user.user_id
        local_job_id = params.user_id
        application_id = params.application_id
        
        job = await db.scalar(
            select(LocalJob).where(LocalJob.local_job_id == local_job_id, LocalJob.created_by == user_id)
        )
        if not job:
            return send_error_response(request, 404, "Local job not exist")

        await db.execute(
            update(LocalJobApplicant)
            .where(LocalJobApplicant.local_job_id == local_job_id, LocalJobApplicant.application_id == application_id)
            .values(is_reviewed=0, reviewed_at=None)
        )
        return send_json_response(200, "Unmarked as reviewed")
    except Exception:
        return send_error_response(request, 500, "Internal server error")
    
async def bookmark_local_job(request: Request, params:LocalJobIdParam, db: AsyncSession):
    try:
        user_id = request.state.user.user_id
        local_job_id = params.user_id
        db.add(UserBookmarkLocalJob(user_id=user_id, local_job_id=local_job_id))
        return send_json_response(200, "Bookmarked")
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def unbookmark_local_job(request: Request, params: LocalJobIdParam, db: AsyncSession):
    try:
        user_id = request.state.user.user_id
        local_job_id = params.user_id
        bookmark = await db.scalar(
            select(UserBookmarkLocalJob).where(
                UserBookmarkLocalJob.user_id == user_id,
                UserBookmarkLocalJob.local_job_id == local_job_id,
            )
        )
        if not bookmark:
            return send_error_response(request, 404, "Failed to remove bookmark")
        await db.delete(bookmark)
        return send_json_response(200, "Bookmark removed")
    except Exception:
        return send_error_response(request, 500, "Internal server error")
    
async def local_jobs_search_queries(request: Request, params: SearchSuggestionsRequest, db: AsyncSession):
    try:
        query = params.query
        clean = query.strip().lower()
        words = clean.split()
        result = await db.execute(
            select(LocalJobSearchQuery)
            .where(or_(
                LocalJobSearchQuery.search_term.ilike(f"{clean}%"),
                *[LocalJobSearchQuery.search_term.ilike(f"%{w}%") for w in words],
                LocalJobSearchQuery.search_term_concatenated.ilike(f"{clean.replace(' ', '')}%"),
            ))
            .where(LocalJobSearchQuery.popularity > 10)
            .order_by(LocalJobSearchQuery.popularity.desc())
            .limit(10)
        )
        return send_json_response(200, "Suggestions retrieved", data=[r.search_term for r in result.scalars()])
    except Exception:
        return send_error_response(request, 500, "Internal server error")