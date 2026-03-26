from datetime import timezone
import io
import uuid
from pathlib import Path
from fastapi import Request
from typing import Optional, List

from PIL import Image

from config import BASE_URL
from models.common import City
from models.user import UserLocation
from schemas.job_schemas import ApplicantProfileSchema, GetJobsSchema, GetSavedJobsSchema, GuestGetJobsSchema, JobIdSchema, LocationSearchSuggestionsSchema, RoleSearchSuggestionsSchema, SkillSearchSuggestionsSchema, UpdateCertificatesSchema, UpdateEducationSchema, UpdateExperienceSchema, UpdateLanguagesSchema, UpdateNoExperienceSchema, UpdateProfessionalInfoSchema, UpdateResumeSchema, UpdateSkillsSchema
from schemas.service_schemas import UpdateIndustriesSchema

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func, or_, and_, delete, exists
from sqlalchemy.dialects.mysql import match
from sqlalchemy.orm import selectinload

from helpers.response_helper import send_error_response, send_json_response
from models.job import (
    ApplicantProfile,
    ApplicantProfileEducation,
    ApplicantProfileExperience,
    ApplicantProfileSkill,
    ApplicantProfileLanguage,
    ApplicantProfileResume,
    ApplicantProfileCertificate,
    Application,
    Job,
    JobIndustry,
    UserJobIndustry,
    UserBookmarkJob,
    Role,
    Skill,
)
from utils.aws_s3 import delete_from_s3, upload_to_s3
from utils.pagination.cursor import decode_cursor, encode_cursor

APPLICANT_PROFILE_STEPS = {
    "PROFESSIONAL_INFO":  "PROFESSIONAL_INFO",
    "EDUCATION":      "EDUCATION",
    "EXPERIENCE":     "EXPERIENCE",
    "SKILLS":         "SKILLS",
    "LANGUAGES":      "LANGUAGES",
    "RESUME":         "RESUME",
    "CERTIFICATES": "CERTIFICATES",
    "COMPLETE":       "COMPLETE",
}
ALL_STEPS = [s for s in APPLICANT_PROFILE_STEPS.values() if s != "COMPLETE"]

VALID_WORK_MODES = ["remote", "office", "hybrid", "flexible"]

def is_step_complete(profile: ApplicantProfile, step: str) -> bool:
    if not profile:
        return False
    if step == "PERSONAL_INFO":
        return all([profile.first_name, profile.last_name,
                    profile.gender, profile.email, profile.intro])
    if step == "EDUCATION":
        return len(profile.educations or []) > 0
    if step == "EXPERIENCE":
        return len(profile.experiences or []) > 0
    if step == "SKILLS":
        return len(profile.skills or []) > 0
    if step == "LANGUAGES":
        return len(profile.languages or []) > 0
    if step == "RESUME":
        return profile.resume is not None
    if step == "CERTIFICATES":
        return len(profile.certificates or []) > 0
    return True

def get_next_incomplete_step(profile: ApplicantProfile, supported_steps: List[str] = None) -> str:
    for step in (supported_steps or ALL_STEPS):
        if not is_step_complete(profile, step):
            return step
    return "COMPLETE"


def calculate_completion_percentage(profile: ApplicantProfile, supported_steps: List[str] = None) -> int:
    steps = supported_steps or ALL_STEPS
    if not profile:
        return 0
    completed = sum(1 for step in steps if is_step_complete(profile, step))
    return round((completed / len(steps)) * 100)

def get_missing_field_suggestions(profile: Optional[ApplicantProfile], supported_steps: List[str] = None) -> list:
    steps = supported_steps or ALL_STEPS
    suggestions = []
    w = 1 / 12

    all_s = {
        "PROFESSIONAL_INFO": [
            {"title": "Add your first name",      "message": "Tell us who you are.",                     "fieldKey": "firstName",  "contribution": w},
            {"title": "Add your last name",       "message": "Complete your full name.",                  "fieldKey": "lastName",   "contribution": w},
            {"title": "Select your gender",       "message": "Help recruiters know you better.",          "fieldKey": "gender",     "contribution": w},
            {"title": "Add your email",           "message": "Important for job notifications.",          "fieldKey": "email",      "contribution": w},
            {"title": "Write a short intro",      "message": "Let people know about you.",                "fieldKey": "intro",      "contribution": w},
            {"title": "Upload a profile picture", "message": "Profiles with pictures get more attention.","fieldKey": "profilePic", "contribution": w},
        ],
        "EDUCATION":      [{"title": "Add your education",       "message": "Show your academic background.",       "fieldKey": "education",    "contribution": w}],
        "EXPERIENCE":     [{"title": "Add your work experience", "message": "Highlight your career journey.",       "fieldKey": "experience",   "contribution": w}],
        "SKILLS":         [{"title": "Add your skills",          "message": "Tell us what you're good at!",         "fieldKey": "skills",       "contribution": w}],
        "LANGUAGES":      [{"title": "Add languages you speak",  "message": "Stand out with language proficiency.", "fieldKey": "languages",    "contribution": w}],
        "CERTIFICATES": [{"title": "Add certificates",         "message": "Show your achievements.",              "fieldKey": "certificates", "contribution": w}],
        "RESUME":         [{"title": "Upload your resume",       "message": "Required to apply for jobs.",          "fieldKey": "resume",       "contribution": w}],
    }

    if not profile:
        for step in steps:
            suggestions.extend(all_s.get(step, []))
        return suggestions

    if "PROFESSIONAL_INFO" in steps:
        if not profile.first_name:
            suggestions.append(all_s["PROFESSIONAL_INFO"][0])
        if not profile.last_name:
            suggestions.append(all_s["PROFESSIONAL_INFO"][1])
        if not profile.gender:
            suggestions.append(all_s["PROFESSIONAL_INFO"][2])
        if not profile.email:
            suggestions.append(all_s["PROFESSIONAL_INFO"][3])
        if not profile.intro:
            suggestions.append(all_s["PROFESSIONAL_INFO"][4])
        if not profile.profile_pic_url:
            suggestions.append(all_s["PROFESSIONAL_INFO"][5])

    if "EDUCATION"      in steps and not (profile.educations      or []):
        suggestions.extend(all_s["EDUCATION"])
    if "EXPERIENCE"     in steps and not (profile.experiences     or []):
        suggestions.extend(all_s["EXPERIENCE"])
    if "SKILLS"         in steps and not (profile.skills         or []):
        suggestions.extend(all_s["SKILLS"])
    if "LANGUAGES"      in steps and not (profile.languages      or []):
        suggestions.extend(all_s["LANGUAGES"])
    if "CERTIFICATES" in steps and not (profile.certificates   or []):
        suggestions.extend(all_s["CERTIFICATES"])
    if "RESUME"         in steps and not profile.resume:
        suggestions.extend(all_s["RESUME"])

    return suggestions

def _applicant_profile_response(profile: Optional[ApplicantProfile], supported_steps: List[str]) -> dict:
    if not profile:
        return {
            "professional_info":      None,
            "educations": [],
            "experiences":     [],
            "skills":          [],
            "languages":       [],
            "certificates":    [],
            "resume":                  None,
            "next_complete_step":                get_next_incomplete_step(None, supported_steps),
            "completion_percentage":             calculate_completion_percentage(None, supported_steps),
            "missing_field_suggestions":         get_missing_field_suggestions(None, supported_steps),
        }

    resume = profile.resume

    return {
        "professional_info": {
            "first_name":      profile.first_name,
            "last_name":       profile.last_name,
            "email":           profile.email,
            "gender":          profile.gender,
            "intro":           profile.intro,
            "profile_pic_url": profile.profile_pic_url,
        },
        "educations": [
            {
                "organization_name":  e.organization_name,
                "field_of_study":     e.field_of_study,
                "start_date": e.start_date.strftime("%d-%m-%Y") if e.start_date else None,
                "end_date":   e.end_date.strftime("%d-%m-%Y")   if e.end_date   else None,
                "grade":              str(e.grade) if e.grade is not None else None,
                "is_currently_studying": e.is_currently_studying,
            }
            for e in (profile.educations or [])
        ],
        "experiences": [
            {
                "job_title":            ex.job_title if ex.job_title else "",
                "employment_type":      ex.employment_type if  ex.employment_type else "",
                "organization_name":         ex.organization_name if  ex.organization_name else "",
                "is_currently_working": ex.current_working_here,
                "is_experienced":          ex.experienced,
                "start_date": ex.start_date.strftime("%d-%m-%Y") if ex.start_date else "",
                "end_date":   ex.end_date.strftime("%d-%m-%Y")   if ex.end_date   else "",
                "location":           ex.location if ex.location else "",
            }
            for ex in (profile.experiences or [])
        ],
        "skills": [
            {"name": sk.name, "code": sk.code}
            for sk in (profile.skills or [])
        ],
        "languages": [
            {            
                "language": lg.language,
                "language_code": lg.language_code,
                "proficiency": lg.proficiency,
                "proficiency_value": lg.proficiency_value
            }
            for lg in (profile.languages or [])
        ],
        "certificates": [
            {
                "issued_by":                ct.issued_by,
                "url": ct.certificate_url,
                "name":    ct.name,
                "size":         ct.size,
                "type":         ct.type,
            }
            for ct in (profile.certificates or [])
        ],
        "resume": {
            "url": resume.resume_url,
            "size":           resume.size,
            "type":                resume.type,
            "last_used":           str(resume.last_used.replace(tzinfo=timezone.utc).isoformat()) if resume.last_used else None,
        } if resume else None,
        "next_complete_step":        get_next_incomplete_step(profile, supported_steps),
        "completion_percentage":     calculate_completion_percentage(profile, supported_steps),
        "missing_field_suggestions": get_missing_field_suggestions(profile, supported_steps),
    }

async def _fetch_full_profile(db: AsyncSession, external_user_id: int) -> Optional[ApplicantProfile]:
    return await db.scalar(
        select(ApplicantProfile)
        .where(ApplicantProfile.external_user_id == external_user_id)
        .options(
            selectinload(ApplicantProfile.educations),
            selectinload(ApplicantProfile.experiences),
            selectinload(ApplicantProfile.skills),
            selectinload(ApplicantProfile.languages),
            selectinload(ApplicantProfile.resume),
            selectinload(ApplicantProfile.certificates),
        )
    )

def _paginate_jobs(items: list, service:Job | None, lastDistance: int | None, lastTotalRelavance: int | None,  page_size: int,  next_token: str = None ) -> dict:
    has_next       = len(items) == page_size and service is not None
    next_token_out = encode_cursor({
        "created_at":      str(service.created_at),
        "id":              service.id,
        "distance":        float(lastDistance) if lastDistance is not None else None,
        "total_relevance": float(lastTotalRelavance) if lastTotalRelavance is not None else None,
    }) if has_next else None
    return {
        "data":           items,
        "next_token":     next_token_out,
        "previous_token": next_token if next_token else None,
    }

def _paginate_jobs_by_job(items: list, job:Job | None, page_size: int, next_token: str = None ) -> dict:
    has_next       = len(items) == page_size and job is not None
    next_token_out = encode_cursor({
        "created_at":      str(job.created_at),
        "id":              job.id
    }) if has_next else None
    return {
        "data":           items,
        "next_token":     next_token_out,
        "previous_token": next_token if next_token else None,
    }

def _job_summary_response(
        job: Job,
        is_bookmarked: bool = False,
        is_applied: bool =False,
        distance:     float | None = None
        ) -> dict:
    return {
        "recruiter":{
                "recruiter_id": job.posted_by.id,
                "first_name": job.posted_by.first_name,
                "last_name": job.posted_by.last_name,
                "role": job.posted_by.role_display,
                "organization_name": job.posted_by.organization_name,
                "profile_pic_url": job.posted_by.profile_pic_url,
                "profile_pic_url_small": job.posted_by.profile_pic_url_small,
                "years_of_experience": job.posted_by.years_of_experience,
                "is_verified": bool(job.posted_by.is_verified),
        },
        "organization":{
            "organization_id": job.organization_id,
            "name": job.organization.name,
            "logo": job.organization.logo,
            "address": job.organization.name,
            "website": job.organization.website,
            
            "country": {
                "country_id":   job.organization.country.id,
                "name": job.organization.country.name
            },

            "state": {
                "country_id":   job.organization.state.country_id,
                "state_id":   job.organization.state.id,
                "name": job.organization.state.name
            },

            "city": {
                "country_id":   job.organization.city.country_id,
                "state_id":   job.organization.city.state_id,
                "city_id":   job.organization.city.id,
                "name": job.organization.city.name
            },

            "postal_code": job.organization.postal_code
        },
       "job": {
            "job_id":          job.job_id,
            "title":           job.title,
            "work_mode":       job.work_mode_display,
            "location": {
                "city_id":   job.city.id,
                "name": job.city.name
            },
            "experience":      job.experience_display,
            "salary_currency_type":      job.salary_currency_type_display,
            "salary":      job.salary_display,
            "must_have_skills":   job.must_have_skills_display,
            "good_to_have_skills":   job.good_to_have_skills_display,
            "employment_type":   job.employment_type_display,
            "vacancies":       job.vacancies,
            "posted_at":       str(job.posted_at.replace(tzinfo=timezone.utc).isoformat()),
            "slug":             f"{BASE_URL}/jobs/{job.slug}",
            "is_bookmarked":   is_bookmarked,
            "distance":        distance
       }
    }

def _job_detail_response(
        job: Job,
        is_bookmarked: bool = False,
        is_applied: bool =False,
        distance:     float | None = None
        ) -> dict:
    return {
        "recruiter":{
                "recruiter_id": job.posted_by.id,
                "first_name": job.posted_by.first_name,
                "last_name": job.posted_by.last_name,
                "role": job.posted_by.role_display,
                "organization_name": job.posted_by.organization_name,
                "profile_pic_url": job.posted_by.profile_pic_url,
                "profile_pic_url_small": job.posted_by.profile_pic_url_small,
                "years_of_experience": job.posted_by.years_of_experience,
                "is_verified": bool(job.posted_by.is_verified),
        },
        "organization":{
            "organization_id": job.organization_id,
            "name": job.organization.name,
            "logo": job.organization.logo,
            "address": job.organization.name,
            "website": job.organization.website,

            "country": {
                "country_id":   job.organization.country.id,
                "name": job.organization.country.name
            },

            "state": {
                "country_id":   job.organization.state.country_id,
                "state_id":   job.organization.state.id,
                "name": job.organization.state.name
            },

            "city": {
                "country_id":   job.organization.city.country_id,
                "state_id":   job.organization.city.state_id,
                "city_id":   job.organization.city.id,
                "name": job.organization.city.name
            },

            "postal_code": job.organization.postal_code
        },
       "job": {
            "job_id":          job.job_id,
            "title":           job.title,
            "work_mode":       job.work_mode_display,
            "location": {
                "city_id":   job.city.id,
                "name": job.city.name
            },
            "description":        job.description,
            "industry":   {
                            "code":   job.industry.code,
                            "name": job.industry.name
                        },
            "education": job.education.name,
            "role": job.role.name,
            "employment_type": job.employment_type_display,
            "department": job.department.name,
            "highlights": job.highlights_display,
            "experience_type": job.experience_type,
            "experience":      job.experience_display,
            "salary_currency_type":      job.salary_currency_type_display,
            "salary":      job.salary_display,
            "must_have_skills":   job.must_have_skills_display,
            "good_to_have_skills":   job.good_to_have_skills_display,
            "vacancies":       job.vacancies,
            "posted_at":       str(job.posted_at.replace(tzinfo=timezone.utc).isoformat()),
            "slug":             f"{BASE_URL}/jobs/{job.slug}",
            "is_bookmarked":   is_bookmarked,
            "is_applied": is_applied
       }
    }

def _haversine(lat: float, lon: float):
    return (
        6371 * func.acos(
            func.cos(func.radians(lat)) *
            func.cos(func.radians(City.latitude)) *
            func.cos(func.radians(City.longitude) - func.radians(lon)) +
            func.sin(func.radians(lat)) *
            func.sin(func.radians(City.latitude))
        )
    ).label("distance")

def _relevance(query: str):
    return match(
        Job.title,
        Job.description,
        against=query
    ).label("total_relevance")

async def _query_jobs(
    db: AsyncSession,
    page_size: int,
    industries: list[int],
    user_id: int | None = None,
    query: str | None = None,
    work_modes: list[str] | None = None,
    salary_min: int | None = None,
    salary_max: int | None = None,
    user_lat:  float | None = None,
    user_lon:  float | None = None,
    next_token: str | None = None,
):
    payload = decode_cursor(next_token) if next_token else None

    has_loc = user_lat is not None and user_lon is not None

    cols = [Job]

    bookmark_subq = (
        exists()
        .where(
            UserBookmarkJob.job_id == Job.job_id,
            UserBookmarkJob.external_user_id == user_id
        )
    ).label("is_bookmarked")

    if has_loc:
           distance_expr = _haversine(user_lat, user_lon)
           cols.append(distance_expr)
    if query:
            relevance_expr = _relevance(query)
            cols.append(relevance_expr)
    if user_id:
        cols.append(bookmark_subq)

    q = (
        select(*cols)
        .options(
            selectinload(Job.industry),
            selectinload(Job.role),
            selectinload(Job.education),
            selectinload(Job.department),
            selectinload(Job.must_have_skills),
            selectinload(Job.good_to_have_skills),
            selectinload(Job.organization),
            selectinload(Job.posted_by)
        )
        .where(
            Job.approval_status == "active",
            Job.status == "published"
        )
    )

    if has_loc:
        q = q.join(
            City,
            Job.location_id == City.id
        )

    if query:
        q = q.where(match(
            Job.title,
            Job.description,
            against=query
        ) > 0)

    if work_modes:
        q = q.where(Job.work_mode.in_(work_modes))

    if salary_min is not None:
        q = q.where(Job.salary_min >= salary_min)

    if salary_max is not None:
        q = q.where(Job.salary_max <= salary_max)

    if len(industries) > 0:
        q = q.where(Job.industry_code.in_(industries))     

    if payload:
        if has_loc and query:
                q = q.where(or_(
                    distance_expr > payload["distance"],
                    and_(distance_expr == payload["distance"], relevance_expr < payload["total_relevance"]),
                    and_(distance_expr == payload["distance"], relevance_expr == payload["total_relevance"], Job.created_at < payload["created_at"]),
                    and_(distance_expr == payload["distance"], relevance_expr == payload["total_relevance"], Job.created_at == payload["created_at"], Job.id > payload["id"]),
                ))
        elif has_loc:
            q = q.where(or_(
                distance_expr > payload["distance"],
                and_(distance_expr == payload["distance"], Job.created_at < payload["created_at"]),
                and_(distance_expr == payload["distance"], Job.created_at == payload["created_at"], Job.id > payload["id"]),
            ))
        elif query:
            q = q.where(or_(
                relevance_expr < payload["total_relevance"],
                and_(relevance_expr == payload["total_relevance"], Job.created_at < payload["created_at"]),
                and_(relevance_expr == payload["total_relevance"], Job.created_at == payload["created_at"], Job.id > payload["id"]),
            ))
        else:
            q = q.where(or_(
                Job.created_at < payload["created_at"],
                and_(Job.created_at == payload["created_at"], Job.id > payload["id"]),
            ))
    
    if has_loc and query:
        q = q.order_by(
            distance_expr.asc(),
            relevance_expr.desc(),
            Job.created_at.desc(),
            Job.id.asc()
        )
    elif has_loc:
        q = q.order_by(
            distance_expr.asc(),
            Job.created_at.desc(),
            Job.id.asc()
        )
    elif query:
        q = q.order_by(
            relevance_expr.desc(),
            Job.created_at.desc(),
            Job.id.asc()
        )
    else:
        q = q.order_by(
            Job.created_at.desc(),
            Job.id.asc()
        )

    q = q.limit(page_size)

    result = await db.execute(q)
    rows   = result.all()
    last_row  = None

    last_row = rows[-1] if rows else None

    jobs = [
    _job_summary_response(
        row.Job,
        bool(row.is_bookmarked) if user_id else False,
        distance=float(row.distance) if has_loc else None
    )
    for row in rows]

   
    return _paginate_jobs(
        jobs,
        getattr(last_row, "Job", None),
        getattr(last_row, "distance", None) if has_loc else None,
        getattr(last_row, "total_relevance", None) if query else None,
        page_size,
        next_token if payload else None,
    )

async def guest_get_job_listings(request: Request, schema: GuestGetJobsSchema, db: AsyncSession):
    try:
        s = schema.s
        page_size = schema.page_size or 20
        next_token = schema.next_token

        industries = schema.industries or []

        if not s and not industries:
            return send_error_response(request, 400, "Industries cannot be empty", error_code= "EMPTY_JOB_INDUSTRIES")

        work_modes = [
            m.strip().lower() for m in (schema.work_modes or [])
            if m.strip().lower() in VALID_WORK_MODES
        ]

        data = await _query_jobs(
            db=db,
            page_size=page_size,
            industries=industries,
            query=s,
            work_modes=work_modes,
            salary_min=schema.salary_min,
            salary_max=schema.salary_max,
            user_lat=schema.latitude,
            user_lon=schema.longitude,
            next_token=next_token
        )

        return send_json_response(200, "Jobs retrieved", data=data)

    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def guest_get_job_by_job_id(request: Request, schema: JobIdSchema, db: AsyncSession):
    try:
        job = await db.scalar(
            select(Job)
            .where(
                Job.job_id == schema.job_id,
                Job.approval_status == "active"
            )
            .options(
                selectinload(Job.industry),
                selectinload(Job.education),
                selectinload(Job.department),
                selectinload(Job.role),
                selectinload(Job.organization),
                selectinload(Job.posted_by),
                selectinload(Job.must_have_skills),
                selectinload(Job.good_to_have_skills)
            )
        )

        if not job:
            return send_error_response(request, 404, "Job not exist")


        data = _job_detail_response(job)

        return send_json_response(
            200,
            "Job fetched successfully",
            data=data
        )

    except Exception:
        return send_error_response(request, 500, "Internal server error")
    
async def get_job_listings(request: Request, schema: GetJobsSchema, db: AsyncSession):
    try:
        user_id = request.state.user.user_id

        s = schema.s
        page_size = schema.page_size or 20
        next_token = schema.next_token

        result = await db.execute(
            select(UserJobIndustry.industry_code)
            .where(UserJobIndustry.external_user_id == user_id)
        )
        industries = result.scalars().all()

        if not s and not industries:
            return send_error_response(request, 400, "Industries cannot be empty", error_code = "NO_USER_JOB_INDUSTRIES")

        work_modes = [
            m.strip().lower() for m in (schema.work_modes or [])
            if m.strip().lower() in VALID_WORK_MODES
        ]

        loc = await db.scalar(select(UserLocation).where(UserLocation.user_id == user_id))
        lat, lon = (float(loc.latitude), float(loc.longitude)) if loc else (None, None)

        data = await _query_jobs(
            db=db,
            user_id=user_id,
            page_size=page_size,
            industries=industries,
            query=s,
            work_modes=work_modes,
            salary_min=schema.salary_min,
            salary_max=schema.salary_max,
            user_lat=lat,
            user_lon=lon,
            next_token=next_token
        )

        return send_json_response(200, "Jobs retrieved", data=data)
    except Exception:
        return send_error_response(request, 500, "Internal server error")
    
async def get_job_by_job_id(request: Request, schema: JobIdSchema, db: AsyncSession):
    try:
        external_user_id = request.state.user.user_id

        is_bookmarked = (
            select(exists().where(
                UserBookmarkJob.external_user_id == external_user_id,
                UserBookmarkJob.job_id == Job.job_id
            ))
        ).label("is_bookmarked")

        is_applied = (
            select(exists().where(
                Application.job_id == Job.job_id
            ).where(
                ApplicantProfile.external_user_id == external_user_id
            ).where(
                ApplicantProfile.applicant_profile_id == Application.applicant_profile_id
            ))
        ).label("is_applied")

        result = await db.execute(
            select(Job, is_bookmarked, is_applied)
            .where(
                Job.job_id == schema.job_id,
                Job.approval_status == "active"
            )
            .options(
                selectinload(Job.industry),
                selectinload(Job.education),
                selectinload(Job.department),
                selectinload(Job.role),
                selectinload(Job.organization),
                selectinload(Job.posted_by),
                selectinload(Job.must_have_skills),
                selectinload(Job.good_to_have_skills)
            )
        )

        row = result.first()

        if not row:
            return send_error_response(request, 404, "Job not exist")

        job, is_bookmarked, is_applied = row

        data = _job_detail_response(job, is_bookmarked, is_applied)
  
        return send_json_response(
            200,
            "Job fetched successfully",
            data=data
        )

    except Exception:
        import traceback
        import sys
        traceback.print_exc(file=sys.stderr)
        sys.stderr.flush()
        return send_error_response(request, 500, "Internal server error")
    
#Apply & Bookmark 
async def apply_job(request: Request, schema: JobIdSchema, db: AsyncSession):
    try:
        external_user_id = request.state.user.user_id
        applicant_profile = await _fetch_full_profile(db, external_user_id)
        is_profile_completed = applicant_profile.is_completed()

        if not applicant_profile or not is_profile_completed:
                        return send_error_response(request, 400, "Applicant profile not completed",  data={
                "is_profile_completed": False,
                "is_applied":           False
            })
        
        job = await db.scalar(
            select(Job).where(Job.job_id == schema.job_id)
        )
        if not job:
            return send_error_response(request, 400, "Job not exist")

        existing = await db.scalar(
            select(Application)
            .where(
                Application.applicant_profile_id == applicant_profile.applicant_profile_id,
                Application.job_id == job.job_id,
            )
        )

        if existing:
            return send_error_response(request, 400, "Job alredy applied",  data={
                "is_profile_completed": True,
                "is_applied":           True
            })
        
        db.add(Application(
                applicant_profile_id=applicant_profile.applicant_profile_id,
                job_id=              job.job_id,
        ))
        await db.flush()

        return send_json_response(
            200,
            "Job applied successfully",
            data={
                "is_profile_completed": True,
                "is_applied":           True
            }
        )
    except Exception:
        return send_error_response(request, 500, "Internal server error")
    
async def bookmark_job(request: Request, schema: JobIdSchema, db: AsyncSession):
    try:
        external_user_id = request.state.user.user_id
        db.add(UserBookmarkJob(
                external_user_id=external_user_id,
                job_id=schema.job_id
            ))
        await db.flush()
        return send_json_response(200, "Bookmarked successfully")
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def unbookmark_job(request: Request, schema: JobIdSchema, db: AsyncSession):
    try:
        external_user_id = request.state.user.user_id
        bookmark = await db.scalar(
            select(UserBookmarkJob)
            .where(
                UserBookmarkJob.external_user_id == external_user_id,
                UserBookmarkJob.job_id == schema.job_id
            )
        )

        if not bookmark:
            return send_error_response(request, 400, "Failed to remove bookmark")
        
        await db.execute(
            delete(UserBookmarkJob)
            .where(
                UserBookmarkJob.external_user_id == external_user_id,
                UserBookmarkJob.job_id == schema.job_id
            )
        )

        return send_json_response(200, "Bookmark removed successfully")
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def get_saved_jobs(request: Request, schema:GetSavedJobsSchema, db: AsyncSession):
    try:
        user_id = request.state.user.user_id
        page_size = schema.page_size
        next_token = schema.next_token

        payload = decode_cursor(next_token) if next_token else None

        loc = await db.scalar(select(UserLocation).where(UserLocation.user_id == user_id))
        lat, lon = (float(loc.latitude), float(loc.longitude)) if loc else (None, None)
        has_loc = lat is not None and lon is not None

        cols = [UserBookmarkJob, Job]

        if has_loc:
            cols.append( _haversine(lat, lon))

        q = (
            select(*cols)
            .where(UserBookmarkJob.external_user_id == user_id)
            .join(UserBookmarkJob.job)       
            .join(Job.city)  
            .order_by(UserBookmarkJob.created_at.desc(), UserBookmarkJob.job_id.asc())
            .limit(page_size)
        )

        if payload:
              q = q.where(or_(
                    UserBookmarkJob.created_at < payload["created_at"],
                    and_(UserBookmarkJob.created_at == payload["created_at"], UserBookmarkJob.id > payload["id"]),
                ))

        result = await db.execute(q)
        bookmarks = result.all()
       
        items = [_job_summary_response(job, is_bookmarked=True, distance= distance) for b, job, distance in bookmarks]

        last_row = items[-1] if items else None

        return send_json_response(
            200,
            "Saved jobs retrieved successfully",
            data=_paginate_jobs_by_job(items, getattr(last_row, "Job", None), page_size, next_token if payload else None)
        )
    except Exception:
        import traceback
        import sys
        traceback.print_exc(file=sys.stderr)
        sys.stderr.flush()
        return send_error_response(request, 500, "Internal server error")

#Applicant Profile
async def get_profile(request: Request, schema:ApplicantProfileSchema, db: AsyncSession):
    try:
        external_user_id = request.state.user.user_id
        profile = await _fetch_full_profile(db, external_user_id)
        data = _applicant_profile_response(profile, schema.supported_steps)
        return send_json_response(200, "Profile retrieved successfully", data=data)
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def update_profile(
    request: Request,
    schema: UpdateProfessionalInfoSchema,
    db: AsyncSession
):
    try:
        external_user_id = request.state.user.user_id
        profile_pic_url = None

        if schema.profile_pic and schema.profile_pic.filename:
            contents = await schema.profile_pic.read()
            img = Image.open(io.BytesIO(contents))
            img = img.convert("RGB")
            img_512x512 = img.resize((512, 512), Image.LANCZOS)
            key = f"jobs/applicants/{external_user_id}/profile/{uuid.uuid4()}.jpg"
            await upload_to_s3(img_512x512, key, "image/jpeg")
            profile_pic_url = key

        applicant_profile = _fetch_full_profile(external_user_id)

        if applicant_profile:
            applicant_profile.first_name = schema.first_name
            applicant_profile.last_name  = schema.last_name
            applicant_profile.email      = schema.email
            applicant_profile.gender     = schema.gender
            applicant_profile.intro      = schema.intro
            if profile_pic_url:                       
                applicant_profile.profile_pic_url = profile_pic_url
        else:
            applicant_profile = ApplicantProfile(
                external_user_id=external_user_id,
                first_name=      schema.first_name,
                last_name=       schema.last_name,
                email=           schema.email,
                gender=          schema.gender,
                intro=           schema.intro,
                profile_pic_url= profile_pic_url,     
            )
            db.add(applicant_profile)

        await db.flush()
        await db.refresh(applicant_profile, attribute_names=[ "educations", "experiences", "skills", "languages",  "resume", "certificates"])

        return send_json_response(200, "Professional information updated successfully", data=  _applicant_profile_response(applicant_profile, schema.supported_steps))
    except Exception:
        db.rollback()
        return send_error_response(request, 500, "Internal server error")
   
async def update_educations(request: Request, schema: UpdateEducationSchema, db: AsyncSession):
    try:
        external_user_id = request.state.user.user_id

        applicant_profile = await _fetch_full_profile(db, external_user_id)
        if not applicant_profile:
            return send_error_response(request, 400, "Applicant profile not exist")

        await db.execute(
            delete(ApplicantProfileEducation)
            .where(ApplicantProfileEducation.applicant_profile_id == applicant_profile.applicant_profile_id)
        )

        for e in schema.educations:
            db.add(ApplicantProfileEducation(
                applicant_profile_id=applicant_profile.applicant_profile_id,
                organization_name=    e.organization_name,
                field_of_study=       e.field_of_study,
                start_date=           e.start_date,
                end_date=             e.end_date,
                grade=                e.grade,
                is_currently_studying= e.is_currently_studying,
            ))

        await db.flush()
        await db.refresh(
            applicant_profile,
            attribute_names=["educations", "experiences", "skills", "languages", "resume", "certificates"]
        )

        return send_json_response(
            200,
            "Education info updated successfully",
            data=_applicant_profile_response(applicant_profile, schema.supported_steps)
        )
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def update_experiences(request: Request, schema: UpdateExperienceSchema, db: AsyncSession):
    try:
        external_user_id = request.state.user.user_id

        applicant_profile = await _fetch_full_profile(db, external_user_id)
        if not applicant_profile:
            return send_error_response(request, 400, "Applicant profile does not exist")

        await db.execute(
            delete(ApplicantProfileExperience)
            .where(ApplicantProfileExperience.applicant_profile_id == applicant_profile.applicant_profile_id)
        )

        for e in schema.experiences:
            db.add(ApplicantProfileExperience(
                applicant_profile_id= applicant_profile.applicant_profile_id,
                job_title=            e.job_title,
                employment_type=      e.employment_type,
                organization_name=         e.organization_name,
                current_working_here= e.is_currently_working,
                experienced=          e.is_experienced,
                start_date=           e.start_date,
                end_date=             e.end_date,
                location=             e.location,
            ))

        await db.flush()

        await db.refresh(
            applicant_profile,
            attribute_names=["educations", "experiences", "skills", "languages", "resume", "certificates"]
        )

        return send_json_response(
            200,
            "Experience info updated successfully",
            data=_applicant_profile_response(applicant_profile, schema.supported_steps)
        )
    except Exception:
        return send_error_response(request, 500, "Internal server error")       

async def update_no_experience(request: Request, schema: UpdateNoExperienceSchema, db: AsyncSession):
    try:
        external_user_id = request.state.user.user_id

        applicant_profile = await _fetch_full_profile(db, external_user_id)
        if not applicant_profile:
            return send_error_response(request, 400, "Applicant profile not exist")

        await db.execute(
            delete(ApplicantProfileExperience)
            .where(ApplicantProfileExperience.applicant_profile_id == applicant_profile.applicant_profile_id)
        )

        db.add(ApplicantProfileExperience(
            applicant_profile_id=applicant_profile.applicant_profile_id,
            experienced=False,
        ))

        await db.flush()

        await db.refresh(
            applicant_profile,
            attribute_names=["educations", "experiences", "skills", "languages", "resume", "certificates"]
        )

        return send_json_response(
            200,
            "No experience updated successfully",
            data=_applicant_profile_response(applicant_profile, schema.supported_steps)
        )
    except Exception:
        return send_error_response(request, 500, "Internal server error")
    
async def update_skills(request: Request, schema: UpdateSkillsSchema, db: AsyncSession):
    try:
        external_user_id = request.state.user.user_id

        applicant_profile = await _fetch_full_profile(db, external_user_id)
        if not applicant_profile:
            return send_error_response(request, 400, "Applicant profile not exist")

        await db.execute(
            delete(ApplicantProfileSkill)
            .where(ApplicantProfileSkill.applicant_profile_id == applicant_profile.applicant_profile_id)
        )

        for s in schema.skills:
            db.add(ApplicantProfileSkill(
                applicant_profile_id=applicant_profile.applicant_profile_id,
                name=      s.name,
                code= s.code,
            ))

        await db.flush()

        await db.refresh(
            applicant_profile,
            attribute_names=["educations", "experiences", "skills", "languages", "resume", "certificates"]
        )

        return send_json_response(
            200,
            "Skills updated successfully",
            data=_applicant_profile_response(applicant_profile, schema.supported_steps)
        )
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def update_languages(request: Request, schema: UpdateLanguagesSchema, db: AsyncSession):
    try:
        external_user_id = request.state.user.user_id

        applicant_profile = await _fetch_full_profile(db, external_user_id)
        if not applicant_profile:
            return send_error_response(request, 400, "Applicant profile does not exist")

        await db.execute(
            delete(ApplicantProfileLanguage)
            .where(ApplicantProfileLanguage.applicant_profile_id == applicant_profile.applicant_profile_id)
        )

        for lang in schema.languages:
            db.add(ApplicantProfileLanguage(
                applicant_profile_id=applicant_profile.applicant_profile_id,
                language=         lang.language.name,
                language_code=    lang.language.code,
                proficiency=      lang.proficiency.name,
                proficiency_value= lang.proficiency.value,
            ))

        await db.flush()

        await db.refresh(
            applicant_profile,
            attribute_names=["educations", "experiences", "skills", "languages", "resume", "certificates"]
        )

        return send_json_response(
            200,
            "Language info updated successfully",
            data=_applicant_profile_response(applicant_profile, schema.supported_steps)
        )
    except Exception:
        return send_error_response(request, 500, "Internal server error")
    
async def update_resume(request: Request, schema: UpdateResumeSchema, db: AsyncSession):
    try:
        external_user_id = request.state.user.user_id

        applicant_profile = await _fetch_full_profile(db, external_user_id)
        if not applicant_profile:
            return send_error_response(request, 400, "Applicant profile does not exist")

        contents = await schema.resume.read()
        key = f"jobs/applicants/{external_user_id}/resume/{uuid.uuid4()}{Path(schema.resume.filename).suffix}"

        await upload_to_s3(contents, key, schema.resume.content_type)

        existing = await db.scalar(
            select(ApplicantProfileResume)
            .where(ApplicantProfileResume.applicant_profile_id == applicant_profile.applicant_profile_id)
        )

        if existing:
            existing.resume_download_url = key
            existing.resume_file_name    = schema.resume.filename or ""
            existing.resume_size         = str(len(contents))
            existing.resume_type         = schema.resume.content_type or ""
        else:
            db.add(ApplicantProfileResume(
                applicant_profile_id=applicant_profile.applicant_profile_id,
                resume_download_url= key,
                resume_file_name=    schema.resume.filename or "",
                resume_size=         str(len(contents)),
                resume_type=         schema.resume.content_type or "",
            ))

        await db.flush()

        await db.refresh(
            applicant_profile,
            attribute_names=["educations", "experiences", "skills", "languages", "resume", "certificates"]
        )

        return send_json_response(
            200,
            "Resume updated successfully",
            data=_applicant_profile_response(applicant_profile, schema.supported_steps)
        )
    except Exception:
        db.rollback()
        return send_error_response(request, 500, "Internal server error")
    
async def update_certificates(
    request: Request,
    schema: UpdateCertificatesSchema,
    db: AsyncSession
):
    uploaded_keys = []
    try:
        external_user_id = request.state.user.user_id

        applicant_profile = await _fetch_full_profile(db, external_user_id)
       
        if not applicant_profile:
            return send_error_response(request, 400, "Applicant profile not exist")

        result = await db.execute(
            select(ApplicantProfileCertificate)
            .where(ApplicantProfileCertificate.applicant_profile_id == applicant_profile.applicant_profile_id)
        )

        existing_certs_map = {c.id: c for c in result.scalars().all()}  

        incoming_ids = set()

        for cert in schema.certificates_info:
            image = schema.images.get(f"certificate_{cert.key}")  
            if cert.certificate_id is None:
                contents = await image.read()
                
                img = Image.open(io.BytesIO(contents))
                buffer = io.BytesIO()
                img.convert("RGB").save(buffer, format="JPEG", quality=85)
                contents = buffer.getvalue()

                s3_key = f"jobs/applicants/{external_user_id}/certificates/{uuid.uuid4()}.jpg"
                image_url = await upload_to_s3(contents, s3_key, image.content_type)
                uploaded_keys.append(s3_key)

                db.add(ApplicantProfileCertificate(
                    applicant_profile_id=     applicant_profile.applicant_profile_id,
                    issued_by=                cert.issued_by,
                    certificate_url= s3_key,
                    name=    image.filename or "",
                    size=         str(len(contents)),
                    type=         image.content_type or "",
                ))
            else:
                existing_cert = existing_certs_map.get(cert.certificate_id)
                if not existing_cert:
                    return send_error_response(request, 400, f"Certificate {cert.certificate_id} not exist")

                incoming_ids.add(cert.certificate_id)
                existing_cert.issued_by = cert.issued_by

                if image:
                    contents = await image.read()

                    img = Image.open(io.BytesIO(contents))
                    buffer = io.BytesIO()
                    img.convert("RGB").save(buffer, format="JPEG", quality=85)
                    contents = buffer.getvalue()

                    s3_key = f"jobs/applicants/{external_user_id}/certificates/{uuid.uuid4()}.jpg"
                    image_url = await upload_to_s3(contents, s3_key, image.content_type)
                    uploaded_keys.append(s3_key)

                    existing_cert.certificate_url = image_url
                    existing_cert.name    = image.filename or ""
                    existing_cert.size         = str(len(contents))
                    existing_cert.type         = image.content_type or ""

        to_delete_ids = set(existing_certs_map.keys()) - incoming_ids
        for cert_id in to_delete_ids:
            await db.delete(existing_certs_map[cert_id])

        deleted_keys = [existing_certs_map[cert_id].certificate_url for cert_id in to_delete_ids]
        
        await db.flush()

        for key in deleted_keys:
            await delete_from_s3(key)

        await db.refresh(
            applicant_profile,
            attribute_names=["educations", "experiences", "skills", "languages", "resume", "certificates"]
        )

        return send_json_response(
            200,
            "Certificates updated successfully",
            data=_applicant_profile_response(applicant_profile, schema.supported_steps)
        )

    except Exception:
        for key in uploaded_keys:
                await delete_from_s3(key)
        return send_error_response(request, 500, "Internal server error")
    
#Utils
async def location_search_suggestions(request: Request, schema: LocationSearchSuggestionsSchema, db: AsyncSession):
    try:
        result = await db.execute(
            select(City)
            .where(City.name.ilike(f"%{schema.query}%"))
            .limit(10)
        )
        cities = result.scalars().all()
        return send_json_response(
            200,
            "Location search suggestions retrieved successfully",
            data=[
            {
                "city_id":    c.id,
                "name":       c.name,
                "latitude":   float(c.latitude),
                "longitude":  float(c.longitude),
            }
            for c in cities
        ])
    except Exception:
        return send_error_response(request, 500, "Internal server error")
    
async def role_search_suggestions(request: Request, schema: RoleSearchSuggestionsSchema, db: AsyncSession):
    try:
        result = await db.execute(
            select(Role)
            .where(Role.name.ilike(f"%{schema.query}%")) 
            .order_by(Role.popularity.desc())
            .limit(10)
        )
        roles = result.scalars().all()
        return send_json_response(
            200,
            "Role search suggestions retrieved successfully",
            data=[{"code": r.code, "name": r.name} for r in roles]
        )
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def skill_search_suggestions(request: Request, schema: SkillSearchSuggestionsSchema, db: AsyncSession):
    try:
        result = await db.execute(
            select(Skill)
            .where(Skill.name.ilike(f"%{schema.query}%"))
            .order_by(Skill.popularity.desc())
            .limit(10)
        )
        skills = result.scalars().all()
        return send_json_response(
            200,
            "Skill search suggestions retrieved successfully",
            data=[{"code": s.code, "name": s.name} for s in skills]
        )
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def guest_get_industries(request: Request, db: AsyncSession):
    try:
        result = await db.execute(
            select(JobIndustry).order_by(JobIndustry.name.asc())
        )
        all_industries = result.scalars().all()

        return send_json_response(
            200,
            "Industries retrieved successfully",
            data=[
                {
                    "code":        i.code,
                    "name":        i.name,
                    "description": i.description,
                    "is_selected": False
                }
                for i in all_industries
            ]
        )
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def get_industries(request: Request, db: AsyncSession):
    try:
        external_user_id = request.state.user.user_id

        all_industries = (await db.scalars(
            select(JobIndustry).order_by(JobIndustry.name.asc())
        )).all()

        selected_codes = set((await db.scalars(
            select(UserJobIndustry.industry_code)
            .where(UserJobIndustry.external_user_id == external_user_id)
        )).all())

        return send_json_response(
            200,
            "Industries retrieved successfully",
            data=[
                {
                    "code":        i.code,
                    "name":        i.name,
                    "description": i.description,
                    "is_selected": i.code in selected_codes,
                }
                for i in all_industries
            ]
        )
    except Exception:
        return send_error_response(request, 500, "Internal server error")
    
async def update_industries(request: Request, schema: UpdateIndustriesSchema, db: AsyncSession):
    try:
        external_user_id = request.state.user.user_id

        await db.execute(
            delete(UserJobIndustry)
            .where(UserJobIndustry.external_user_id == external_user_id)
        )

        for ind in schema.industries:
            if ind.is_selected:
                db.add(UserJobIndustry(
                    external_user_id=external_user_id,
                    industry_code=   ind.code,
                ))

        await db.flush()

        return await get_industries(request, db)  
    except Exception:
        return send_error_response(request, 500, "Internal server error")