from datetime import date, datetime, time, timedelta, timezone
import random
import uuid
from typing import Optional

import httpx
from fastapi import Request
from fastapi.responses import JSONResponse
from models.user import User

from sqlalchemy import delete, select ,and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from config import (
    ACCESS_TOKEN_SECRET,
    REFRESH_TOKEN_SECRET,
    PROFILE_BASE_URL,
)

ALL_JOBS_PAGE_SIZE = 10

from utils.web.auth import cache_get, cache_set, cache_delete, generate_tokens, send_otp_email 
from helpers.response_helper import send_error_response, send_json_response
from models.job import (
    Application,
    City,
    Country,
    Department,
    Education,
    Job,
    JobGoodToHaveSkill,
    JobIndustry,
    JobMustHaveSkill,
    Organization,
    Plan,
    RecruiterProfile,
    RecruiterSettings,
    Role,
    SalaryMarket,
    Skill,
    State,
)
from schemas.web.career_listing_schemas import (
    STATUS_WORKFLOW,
    ApplicationsByJobSchema,
    DashboardSchema,
    EmailLoginSchema,
    EmailOtpSchema,
    EmailOtpVerifySchema,
    ExtendSchema,
    GoogleLoginSchema,
    JobCreateSchema,
    JobIdSchema,
    JobListingsFilterSchema,
    LocationsSearchSchema,
    ManageApplicationSchema,
    OrganizationProfileSchema,
    PageSchema,
    PhoneOtpSchema,
    PhoneOtpVerifySchema,
    RecruiterProfileSchema,
    RecruiterSettingsSchema,
    SearchQuerySchema,
    StatesSearchSchema,
    StatusSchema,
    UpdateStatusSchema,
)
from utils.aws_s3 import upload_to_s3

CURRENCY_SYMBOLS = {"INR": "₹", "USD": "$", "EUR": "€", "GBP": "£"}

def _format_salary(salary: float, currency_type: str) -> str:
    symbol = CURRENCY_SYMBOLS.get(currency_type, "₹")
    if currency_type == "INR":
        if salary >= 1_00_00_000:
            return f"{symbol}{salary / 1_00_00_000:.2f} Cr"
        if salary >= 1_00_000:
            return f"{symbol}{salary / 1_00_000:.2f} Lakh"
        return f"{symbol}{int(salary)}"
    else:
        if salary >= 1_000_000:
            return f"{symbol}{salary / 1_000_000:.2f}M"
        if salary >= 1_000:
            return f"{symbol}{salary / 1_000:.2f}K"
        return f"{symbol}{int(salary)}"


def _paginate(page_obj_items: list, count: int, num_pages: int, current_page: int, has_next: bool, has_previous: bool) -> dict:
    return {
        "count": count,
        "num_pages": num_pages,
        "current_page": current_page,
        "has_next": has_next,
        "has_previous": has_previous,
    }

async def _get_recruiter_profile(request: Request, db: AsyncSession) -> Optional[RecruiterProfile]:
    user_id = request.state.user.external_user_id
    return await db.scalar(
        select(RecruiterProfile)
        .where(RecruiterProfile.external_user_id == user_id)
        .options(selectinload(RecruiterProfile.settings), selectinload(RecruiterProfile.organizations))
    )

async def _get_currency(profile: RecruiterProfile, db: AsyncSession) -> str:
    if profile and profile.settings:
        return profile.settings.currency_type
    return "INR"

async def _get_job_for_recruiter(job_id: int, profile: RecruiterProfile, db: AsyncSession) -> Optional[Job]:
    return await db.scalar(
        select(Job)
        .where(Job.job_id == job_id, Job.posted_by_id == profile.id)
        .options(
            selectinload(Job.city),
            selectinload(Job.industry),
            selectinload(Job.education),
            selectinload(Job.department),
            selectinload(Job.role),
            selectinload(Job.organization),
            selectinload(Job.must_have_skills).selectinload(JobMustHaveSkill.skill),
            selectinload(Job.good_to_have_skills).selectinload(JobGoodToHaveSkill.skill),
        )
    )

def _job_list_response(job: Job, currency_type: str) -> dict:
    return {
        "id": job.job_id,
        "title": job.title,
        "description": job.description,
        "location": job.city.name if job.city else "",
        "work_mode": job.work_mode,
        "salary_not_disclosed": job.is_salary_not_disclosed,
        "formatted_salary_min": _format_salary(float(job.salary_min), currency_type),
        "formatted_salary_max": _format_salary(float(job.salary_max), currency_type),
        "posted_at": str(job.posted_at),
        "status": job.status,
        "approval_status": job.approval_status,
    }

def _job_detail_resposne(job: Job) -> dict:
    return {
        "job_id": job.job_id,
        "title": job.title,
        "work_mode": job.work_mode,
        "location": {"id": job.city.id, "name": job.city.name} if job.city else None,
        "description": job.description,
        "experience_type": job.experience_type,
        "experience_range_min": job.experience_range_min,
        "experience_range_max": job.experience_range_max,
        "experience_fixed": job.experience_fixed,
        "salary_min": float(job.salary_min),
        "salary_max": float(job.salary_max),
        "salary_not_disclosed": job.is_salary_not_disclosed,
        "employment_type": job.employment_type,
        "education": {"value": job.education.code, "name": job.education.name} if job.education else None,
        "industry": {"value": job.industry.code, "name": job.industry.name} if job.industry else None,
        "department": {"value": job.department.code, "name": job.department.name} if job.department else None,
        "role": {"value": job.role.code, "name": job.role.name} if job.role else None,
        "must_have_skills": [{"value": s.skill.code, "name": s.skill.name} for s in (job.must_have_skills or []) if s.skill],
        "good_to_have_skills": [{"value": s.skill.code, "name": s.skill.name} for s in (job.good_to_have_skills or []) if s.skill],
        "vacancies": job.vacancies,
        "highlights": job.highlights,
        "status": job.status,
        "approval_status": job.approval_status
    }

async def _handle_signin_success(request, user_id, email, sign_up_method, first_name, last_name, db: AsyncSession):

    recruiterProfile = await db.scalar(select(RecruiterProfile).where(RecruiterProfile.external_user_id == user_id))
    if not recruiterProfile:
        recruiterProfile = RecruiterProfile(
            external_user_id=user_id,
            first_name=first_name,
            last_name=last_name,
            email=email,
            is_verified=True,
            organization_name="",
            bio="",
        )
        db.add(recruiterProfile) 


    last_sign_in = datetime.now(timezone.utc)
    recruiterProfile.last_sign_in = last_sign_in     
    await db.flush()
    await db.refresh(recruiterProfile)

    access_token, refresh_token = generate_tokens(user_id, email, sign_up_method, recruiterProfile.last_sign_in, "User")

    response = JSONResponse(
        status_code=200,
        content={"isSuccessful": True, "message": "Login successful"}
    )

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False,      
        samesite="lax",
        max_age=60 * 60,   
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False,       # set True in production
        samesite="lax",
        max_age=90 * 24 * 60 * 60,  # 90 days
    )

    return response

async def email_signin(request: Request, schema: EmailLoginSchema, db: AsyncSession):
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "http://localhost:8000/api/v1/auth/signin/lts360",
                  json={"email": schema.email, "password": schema.password},
            )
        if resp.status_code not in (200, 201):
            return send_error_response(request, 400, resp.json().get("message", "Something went wrong"))

        api_resp = resp.json()
        if not api_resp.get("isSuccessful"):
            return send_error_response(request, 401, api_resp.get("message", "Authentication failed"))

        ud = api_resp["data"]["user"]
        return await _handle_signin_success(request, ud["user_id"], ud["email"], "leagcy_email", ud["first_name"], ud["last_name"], db)

    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def signout(request: Request):
    response = JSONResponse(content={"message": "Logged out successfully"}, status_code=200)
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return response

async def google_signin(request: Request, schema: GoogleLoginSchema, db: AsyncSession):
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "http://localhost:3000/api/auth/partner/google-sign-in/",
                data={"id_token": schema.id_token, "sign_in_method": "google"},
            )
        if resp.status_code not in (200, 201):
            return send_error_response(request, 400, resp.json().get("message", "Something went wrong"))

        api_resp = resp.json()
        if not api_resp.get("isSuccessful"):
            return send_error_response(request, 401, api_resp.get("message", "Authentication failed"))

        ud = api_resp["data"]["user_details"]
        return await _handle_signin_success(request, ud["user_id"], ud["email"], "google", ud["first_name"], ud["last_name"], db)

    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def dashboard(request: Request, schema: DashboardSchema, db: AsyncSession):
    try:
        profile = await _get_recruiter_profile(request, db)
        if not profile:
            return send_error_response(request, 404, "Recruiter profile not exist")

        today = date.today()
        end_date = today

        if schema.duration == "custom":
            try:
                start_date = date.fromisoformat(schema.start_date)
                end_date = date.fromisoformat(schema.end_date)
            except Exception:
                start_date = end_date - timedelta(days=7)
        elif schema.duration == "1":
            start_date = today
        elif schema.duration == "30":
            start_date = today - timedelta(days=30)
        elif schema.duration == "90":
            start_date = today - timedelta(days=89)
        else:  # default 7
            start_date = today - timedelta(days=7)

        jobs_result = await db.scalars(
            select(Job)
            .where(Job.posted_by_id == profile.id)
            .where(Job.posted_at >= datetime.combine(start_date, time.min))
            .where(Job.posted_at <= datetime.combine(end_date, time.max))
            .options(selectinload(Job.applications))
        )
        jobs = jobs_result.all()
        job_ids = [j.job_id for j in jobs]

        # applications in range
        apps_result = await db.scalars(
            select(Application)
            .where(Application.job_id.in_(job_ids))
            .where(Application.applied_at >= datetime.combine(start_date, time.min))
            .where(Application.applied_at <= datetime.combine(end_date, time.max))
        )
        applications = apps_result.all()

        total_jobs = len(jobs)
        total_applications = len(applications)
        hired = [a for a in applications if a.status == "hired"]
        rejected = [a for a in applications if a.is_rejected]
        hired_pct = round((len(hired) / total_applications * 100) if total_applications > 0 else 0, 1)

        # top job by application count
        job_app_counts = {j.job_id: 0 for j in jobs}
        for a in applications:
            if a.job_id in job_app_counts:
                job_app_counts[a.job_id] += 1
        top_job = max(jobs, key=lambda j: job_app_counts.get(j.job_id, 0)) if jobs else None

        # timeline
        timeline = {"labels": [], "data": []}
        delta = (end_date - start_date).days + 1
        if delta == 1:
            timeline["labels"].append(start_date.strftime("%b %d"))
            timeline["data"].append(total_applications)
        elif delta > 30:
            cur = start_date
            while cur <= end_date:
                week_end = min(cur + timedelta(days=6), end_date)
                label = f"{cur.strftime('%b %d')} - {week_end.strftime('%b %d')}"
                count = sum(
                    1 for a in applications
                    if datetime.combine(cur, time.min) <= a.applied_at <= datetime.combine(week_end, time.max)
                )
                timeline["labels"].append(label)
                timeline["data"].append(count)
                cur = week_end + timedelta(days=1)
        else:
            for i in range(delta):
                d = start_date + timedelta(days=i)
                count = sum(1 for a in applications if a.applied_at.date() == d)
                timeline["labels"].append(d.strftime("%b %d"))
                timeline["data"].append(count)

        # recent activities
        activities = []
        for j in jobs:
            activities.append({"activity": "New Job Posted", "date": j.posted_at.isoformat(), "details": f"Job '{j.title}' posted.", "type": "job"})
        for a in applications:
            activities.append({"activity": "New Application", "date": a.applied_at.isoformat(), "details": f"Application for job {a.job_id}.", "type": "application"})
        activities.sort(key=lambda x: x["date"], reverse=True)

        return send_json_response(200, "Dashboard retrieved", data={
            "duration": schema.duration,
            "start_date": str(start_date),
            "end_date": str(end_date),
            "total_jobs": total_jobs,
            "total_applications": total_applications,
            "hired_applications": len(hired),
            "hired_percentage": hired_pct,
            "top_job": {"title": top_job.title if top_job else "No jobs", "applications_count": job_app_counts.get(top_job.job_id, 0) if top_job else 0},
            "applications_timeline": timeline,
            "status_distribution": {
                "labels": ["Applied", "Viewed", "Interview", "Hired", "Rejected"],
                "data": [
                    sum(1 for a in applications if a.status == s)
                    for s in ["applied", "viewed", "interview", "hired"]
                ] + [len(rejected)],
            },
            "recent_activities": activities[:10],
        })
    except Exception:

        return send_error_response(request, 500, "Internal server error")

async def search_countries(request: Request, schema: SearchQuerySchema, db: AsyncSession):
    try:
        if not schema.q:
            return send_json_response(200, "OK", data=[])
        rows = (await db.scalars(select(Country).where(Country.name.ilike(f"%{schema.q}%")).limit(20))).all()
        return send_json_response(200, "OK", data=[{"id": c.id, "name": c.name} for c in rows])
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def search_states(request: Request, schema: StatesSearchSchema, db: AsyncSession):
    try:
        if not schema.q:
            return send_json_response(200, "OK", data=[])
        stmt = select(State).where(State.name.ilike(f"%{schema.q}%"))
        if schema.country_id:
            stmt = stmt.where(State.country_id == schema.country_id)
        rows = (await db.scalars(stmt.limit(20))).all()
        return send_json_response(200, "OK", data=[{"id": s.id, "name": s.name} for s in rows])
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def search_cities(request: Request, schema: LocationsSearchSchema, db: AsyncSession):
    try:
        if not schema.q or len(schema.q) < 2:
            return send_json_response(200, "OK", data=[])
        stmt = select(City).where(City.name.ilike(f"%{schema.q}%"))
        if schema.state_id:
            stmt = stmt.where(City.state_id == schema.state_id)
        if schema.country_id:
            stmt = stmt.where(City.country_id == schema.country_id)
        rows = (await db.scalars(stmt.limit(20))).all()
        return send_json_response(200, "OK", data=[{"id": c.id, "name": c.name} for c in rows])
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def search_job_locations(request: Request,schema: SearchQuerySchema, db: AsyncSession):
    try:
        if not schema.q or len(schema.q.strip()) < 2:
            return send_json_response(200, "OK", data=[])
        profile = await _get_recruiter_profile(request, db)
        stmt = select(City).where(City.name.ilike(f"%{schema.q}%"))
        if profile and profile.settings and profile.settings.country_id:
            stmt = stmt.where(City.country_id == profile.settings.country_id)
        rows = (await db.scalars(stmt.order_by(City.name).limit(20))).all()
        return send_json_response(200, "OK", data=[{"id": c.id, "name": c.name} for c in rows])
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def search_employment_types(request: Request, schema: SearchQuerySchema):
    choices = ["full_time", "part_time", "contract", "internship"]
    filtered = [c for c in choices if schema.q.lower() in c.lower()]
    return send_json_response(200, "OK", data=[{"value": c, "label": c.replace("_", " ").title()} for c in filtered])

async def search_education(request: Request, schema: SearchQuerySchema, db: AsyncSession):
    try:
        stmt = select(Education)
        if schema.q:
            stmt = stmt.where(Education.name.ilike(f"%{schema.q}%"))
        rows = (await db.scalars(stmt.limit(20))).all()
        return send_json_response(200, "OK", data=[{"value": e.code, "label": e.name} for e in rows])
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def search_industry(request: Request, schema: SearchQuerySchema, db: AsyncSession):
    try:
        if not schema.q:
            return send_json_response(200, "OK", data=[])
        rows = (await db.scalars(select(JobIndustry).where(JobIndustry.name.ilike(f"%{schema.q}%")).limit(20))).all()
        return send_json_response(200, "OK", data=[{"value": i.code, "label": i.name} for i in rows])
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def search_department(request: Request, schema: SearchQuerySchema, db: AsyncSession):
    try:
        if not schema.q:
            return send_json_response(200, "OK", data=[])
        from models.job import Department
        rows = (await db.scalars(select(Department).where(Department.name.ilike(f"%{schema.q}%")).limit(20))).all()
        return send_json_response(200, "OK", data=[{"value": r.code, "label": r.name} for r in rows])
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def search_role(request: Request, schema: SearchQuerySchema, db: AsyncSession):
    try:
        if not schema.q:
            return send_json_response(200, "OK", data=[])
        rows = (await db.scalars(select(Role).where(Role.name.ilike(f"%{schema.q}%")).limit(20))).all()
        return send_json_response(200, "OK", data=[{"value": r.code, "label": r.name} for r in rows])
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def search_skills(request: Request, schema: SearchQuerySchema, db: AsyncSession):
    try:
        if not schema.q:
            return send_json_response(200, "OK", data=[])
        rows = (await db.scalars(select(Skill).where(Skill.name.ilike(f"%{schema.q}%")).limit(30))).all()
        return send_json_response(200, "OK", data=[{"value": s.code, "name": s.name} for s in rows])
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def get_job_listings_meta(request: Request, db: AsyncSession):
    try:
        profile = await _get_recruiter_profile(request, db)
        if not profile:
            return send_error_response(request, 404, "Profile not found")

        org = await db.scalar(select(Organization).where(Organization.user_id == profile.id))
        currency_type = await _get_currency(profile, db)
        salary_market = await db.scalar(select(SalaryMarket).where(SalaryMarket.currency_type == currency_type))

        return send_json_response(200, "Meta retrieved", data={
            "can_post_job": bool(org) and bool(profile.first_name),
            "is_recruiter_profile_complete": bool(profile.first_name and profile.bio),
            "is_company_profile_complete": bool(org),
            "work_modes": [{"value": v, "label": v.replace("_", " ").title()} for v in ["remote", "office", "hybrid", "flexible"]],
            "experience_types": [{"value": v, "label": v.replace("_", " ").title()} for v in ["fresher", "min_max", "fixed"]],
            "employment_types": [{"value": v, "label": v.replace("_", " ").title()} for v in ["full_time", "part_time", "contract", "internship"]],
            "salary_markers": {
                "start": salary_market.salary_start if salary_market else 0,
                "middle": salary_market.salary_middle if salary_market else 500000,
                "end": salary_market.salary_end if salary_market else 1000000,
                "currency_symbol": CURRENCY_SYMBOLS.get(currency_type, "₹"),
                "min": salary_market.salary_start if salary_market else 0,
                "max": salary_market.salary_end if salary_market else 1000000,
                "step": (salary_market.salary_middle // 100) if salary_market else 5000,
            },
        })
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def get_job_listings(
    request: Request,
    schema: JobListingsFilterSchema,
    db: AsyncSession,
):
    try:
        profile = await _get_recruiter_profile(request, db)
        if not profile:
            return send_error_response(request, 404, "Profile not found")

        currency_type = await _get_currency(profile, db)

        q = (
            select(Job)
            .where(Job.posted_by_id == profile.id)
            .options(selectinload(Job.city))
            .order_by(Job.posted_at.desc())
        )

        if schema.experience == "Entry Level":
            q = q.where(or_(and_(Job.experience_range_min >= 0, Job.experience_range_max <= 2), Job.experience_fixed <= 2))
        elif schema.experience == "Mid Level":
            q = q.where(or_(and_(Job.experience_range_min >= 2, Job.experience_range_max <= 5), and_(Job.experience_fixed >= 2, Job.experience_fixed <= 5)))
        elif schema.experience == "Senior Level":
            q = q.where(or_(Job.experience_range_min >= 5, Job.experience_fixed >= 5))
        elif schema.experience == "Executive":
            q = q.where(or_(Job.experience_range_min >= 10, Job.experience_fixed >= 10))

        if schema.work_mode:
            q = q.where(Job.work_mode == schema.work_mode)

        if schema.date_from and schema.date_to:
            try:
                df = date.fromisoformat(schema.date_from)
                dt = date.fromisoformat(schema.date_to)
                q = q.where(Job.posted_at >= datetime.combine(df, time.min))
                q = q.where(Job.posted_at <= datetime.combine(dt, time.max))
            except ValueError:
                pass

        all_jobs = (await db.scalars(q)).all()
        total = len(all_jobs)
        per_page = ALL_JOBS_PAGE_SIZE
        num_pages = max(1, (total + per_page - 1) // per_page)
        start = (schema.page - 1) * per_page
        page_jobs = all_jobs[start: start + per_page]

        return send_json_response(200, "Jobs retrieved", data={
            "results": [_job_list_response(j, currency_type) for j in page_jobs],
            "count": total,
            "num_pages": num_pages,
            "current_page": schema.page,
            "has_next": schema.page < num_pages,
            "has_previous": schema.page > 1,
            "is_filters_applied": any([schema.experience, schema.work_mode, schema.date_from, schema.date_to]),
        })
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def create_job_listing(request: Request, schema: JobCreateSchema, db: AsyncSession):
    try:
        profile = await _get_recruiter_profile(request, db)
        if not profile:
            return send_error_response(request, 404, "Profile not found")

        org = await db.scalar(select(Organization).where(Organization.user_id == profile.id))
        if not org:
            return send_error_response(request, 400, "Organization not found")

        import random as _random
        job_id = _random.randint(10_000_000, 99_999_999)
        slug = f"{schema.title.lower().replace(' ', '-')}-{job_id}"

        job = Job(
            job_id=job_id,
            title=schema.title,
            work_mode=schema.work_mode,
            location_id=schema.location,
            description=schema.description,
            experience_type=schema.experience_type,
            experience_range_min=schema.experience_range_min,
            experience_range_max=schema.experience_range_max,
            experience_fixed=schema.experience_fixed,
            salary_min=schema.salary_min,
            salary_max=schema.salary_max,
            is_salary_not_disclosed=schema.salary_not_disclosed,
            employment_type=schema.employment_type,
            education_code=schema.education,
            industry_code=schema.industry,
            department_code=schema.department,
            role_code=schema.role,
            vacancies=schema.vacancies,
            highlights=schema.highlights,
            expiry_date=schema.expiry_date,
            posted_by_id=profile.id,
            organization_id=org.organization_id,
            slug=slug,
        )
        db.add(job)
        await db.flush()

        for code in schema.must_have_skills:
            db.add(JobMustHaveSkill(job_id=job.id, code=code))
        for code in schema.good_to_have_skills:
            db.add(JobGoodToHaveSkill(job_id=job.id, code=code))

        await db.flush()
        return send_json_response(201, "Job created", data={"job_id": job.job_id})
    except Exception:
        import traceback, sys; traceback.print_exc(file=sys.stderr)
        return send_error_response(request, 500, "Internal server error")

async def get_job_listing(request: Request, schema: JobIdSchema, db: AsyncSession):
    try:
        profile = await _get_recruiter_profile(request, db)
        if not profile:
            return send_error_response(request, 404, "Profile not found")
        job = await _get_job_for_recruiter(schema.job_id, profile, db)
        if not job:
            return send_error_response(request, 404, "Job not found")
        job_response = _job_detail_resposne(job)
        job_response["days_remaining"] = job.days_remaining
        job_response["is_published"]   = job.is_published
        job_response["is_draft"]       = job.is_draft
        job_response["expiry_date"]     = job.expiry_date.isoformat() if job.expiry_date else None

        return send_json_response(200, "Job retrieved", data=job_response)
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def update_job_listing(request: Request, job_id: int, schema: JobCreateSchema, db: AsyncSession):
    try:
        profile = await _get_recruiter_profile(request, db)
        if not profile:
            return send_error_response(request, 404, "Profile not found")
        job = await _get_job_for_recruiter(job_id, profile, db)
        if not job:
            return send_error_response(request, 404, "Job not found")

        job.title = schema.title
        job.work_mode = schema.work_mode
        job.location_id = schema.location
        job.description = schema.description
        job.experience_type = schema.experience_type
        job.experience_range_min = schema.experience_range_min
        job.experience_range_max = schema.experience_range_max
        job.experience_fixed = schema.experience_fixed
        job.salary_min = schema.salary_min
        job.salary_max = schema.salary_max
        job.is_salary_not_disclosed = schema.salary_not_disclosed
        job.employment_type = schema.employment_type
        job.education_code = schema.education
        job.industry_code = schema.industry
        job.department_code = schema.department
        job.role_code = schema.role
        job.vacancies = schema.vacancies
        job.highlights = schema.highlights

        # replace skills
        await db.execute(delete(JobMustHaveSkill).where(JobMustHaveSkill.job_id == job.id))
        await db.execute(delete(JobGoodToHaveSkill).where(JobGoodToHaveSkill.job_id == job.id))
        for code in schema.must_have_skills:
            db.add(JobMustHaveSkill(job_id=job.id, code=code))
        for code in schema.good_to_have_skills:
            db.add(JobGoodToHaveSkill(job_id=job.id, code=code))

        await db.flush()
        return send_json_response(200, "Job updated successfully")
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def delete_job_listing(request: Request, schema: JobIdSchema, db: AsyncSession):
    try:
        profile = await _get_recruiter_profile(request, db)
        if not profile:
            return send_error_response(request, 404, "Profile not found")
        job = await db.scalar(select(Job).where(Job.job_id == schema.job_id, Job.posted_by_id == profile.id))
        if not job:
            return send_error_response(request, 404, "Job not found")
        await db.delete(job)
        await db.flush()
        return send_json_response(200, "Job deleted successfully")
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def update_job_status(request: Request, schema: StatusSchema, db: AsyncSession):
    try:
        profile = await _get_recruiter_profile(request, db)
        if not profile:
            return send_error_response(request, 404, "Profile not found")
        job = await db.scalar(select(Job).where(Job.job_id == schema.job_id, Job.posted_by_id == profile.id))
        if not job:
            return send_error_response(request, 404, "Job not found")
        job.status = "published" if schema.action == "publish" else "draft"
        await db.flush()
        return send_json_response(200, "Status updated")
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def extend_expiry(request: Request, schema: ExtendSchema, db: AsyncSession):
    try:
        profile = await _get_recruiter_profile(request, db)
        if not profile:
            return send_error_response(request, 404, "Profile not found")
        job = await db.scalar(select(Job).where(Job.job_id == schema.job_id, Job.posted_by_id == profile.id))
        if not job:
            return send_error_response(request, 404, "Job not found")
        job.expiry_date = schema.new_expiry_date
        await db.flush()
        return send_json_response(200, "Deadline extended")
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def get_applications(request: Request, schema : PageSchema, db: AsyncSession):
    try:
        profile = await _get_recruiter_profile(request, db)
        if not profile:
            return send_error_response(request, 404, "Profile not found")

        currency_type = await _get_currency(profile, db)

        all_jobs = (await db.scalars(
            select(Job)
            .where(Job.posted_by_id == profile.id)
            .options(selectinload(Job.city), selectinload(Job.applications).selectinload(Application.applicant_profile))
            .order_by(Job.posted_at.desc())
        )).all()

        total = len(all_jobs)
        per_page = ALL_JOBS_PAGE_SIZE
        num_pages = max(1, (total + per_page - 1) // per_page)
        start = (schema.page - 1) * per_page
        page_jobs = all_jobs[start: start + per_page]

        results = []
        for job in page_jobs:
            apps = sorted(job.applications or [], key=lambda a: a.applied_at, reverse=True)
            num_apps = len(apps)
            top3 = apps[:3]
            results.append({
                "job_id": job.job_id,
                "title": job.title,
                "work_mode": job.work_mode,
                "location": job.city.name if job.city else "",
                "status": job.status,
                "approval_status": job.approval_status,
                "posted_at": str(job.posted_at),
                "expiry_date": str(job.expiry_date) if job.expiry_date else None,
                "salary_not_disclosed": job.is_salary_not_disclosed,
                "formatted_salary_min": _format_salary(float(job.salary_min), currency_type),
                "formatted_salary_max": _format_salary(float(job.salary_max), currency_type),
                "num_applications": num_apps,
                "extra_applications": max(0, num_apps - 3),
                "applications": [
                    {
                        "application_id": str(a.application_id),
                        "applied_at": str(a.applied_at),
                        "status": a.status,
                        "is_rejected": a.is_rejected,
                        "is_top_application": a.is_top_application,
                    }
                    for a in top3
                ],
            })

        return send_json_response(200, "Applications retrieved", data={
            "results": results,
            "count": total,
            "num_pages": num_pages,
            "current_page": schema.page,
            "has_next": schema.page < num_pages,
            "has_previous": schema.page > 1,
        })
    except Exception:
        import traceback, sys; traceback.print_exc(file=sys.stderr)
        return send_error_response(request, 500, "Internal server error")

async def get_applications_by_job(request: Request, schema: ApplicationsByJobSchema, db: AsyncSession):
    try:
        profile = await _get_recruiter_profile(request, db)
        if not profile:
            return send_error_response(request, 404, "Profile not found")

        job = await db.scalar(
            select(Job)
            .where(Job.job_id == schema.job_id, Job.posted_by_id == profile.id)
            .options(selectinload(Job.city))
        )
        if not job:
            return send_error_response(request, 404, "Job not found")

        all_apps = (await db.scalars(
            select(Application)
            .where(Application.job_id == job.job_id)
            .options(selectinload(Application.applicant_profile).selectinload(lambda ap: ap.resume))
            .order_by(Application.applied_at.desc())
        )).all()

        total = len(all_apps)
        per_page = ALL_JOBS_PAGE_SIZE
        num_pages = max(1, (total + per_page - 1) // per_page)
        start = (schema.page - 1) * per_page
        page_apps = all_apps[start: start + per_page]

        return send_json_response(200, "Applications retrieved", data={
            "job": {
                "job_id": job.job_id,
                "title": job.title,
                "location": job.city.name if job.city else "",
                "posted_at": str(job.posted_at),
                "salary_min": float(job.salary_min),
                "salary_max": float(job.salary_max),
                "description": job.description,
            },
            "results": [
                {
                    "application_id": a.application_id,
                    "first_name": a.applicant_profile.first_name,
                    "last_name": a.applicant_profile.last_name,
                    "email": a.applicant_profile.email,
                    "phone": a.applicant_profile.phone,
                    "resume_url": f"{PROFILE_BASE_URL}/{a.applicant_profile.resume.resume_url}" if a.applicant_profile.resume else None,
                    "applied_at": str(a.applied_at),
                    "status": a.status,
                    "is_rejected": a.is_rejected,
                }
                for a in page_apps
            ],
            "count": total,
            "num_pages": num_pages,
            "current_page": schema.page,
            "has_next": schema.page < num_pages,
            "has_previous":  schema.page > 1,
        })
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def manage_application(request: Request, schema: ManageApplicationSchema, db: AsyncSession):
    try:
        profile = await _get_recruiter_profile(request, db)
        if not profile:
            return send_error_response(request, 404, "Profile not found")

        job = await db.scalar(select(Job).where(Job.job_id == schema.job_id, Job.posted_by_id == profile.id))
        if not job:
            return send_error_response(request, 404, "Job not found")

        app = await db.scalar(
            select(Application)
            .where(Application.application_id == schema.application_id, Application.job_id == job.job_id)
            .options(selectinload(Application.applicant_profile).selectinload(lambda ap: ap.resume))
        )
        if not app:
            return send_error_response(request, 404, "Application not found")

        ap = app.applicant_profile
        current_status = next((s for s in STATUS_WORKFLOW if s["id"] == app.status), STATUS_WORKFLOW[0])
        total_steps = len(STATUS_WORKFLOW)
        progress = 100 if app.is_rejected else (current_status["order"] / total_steps) * 100
        available = [] if app.is_rejected else [s for s in STATUS_WORKFLOW if s["order"] > current_status["order"]]

        resume_url = None
        if ap.resume:
            resume_url = f"{PROFILE_BASE_URL}/{ap.resume.resume_url}"

        return send_json_response(200, "Application retrieved", data={
            "job": {"job_id": job.job_id, "title": job.title, "location": job.city.name if job.city else ""},
            "application": {
                "application_id": app.application_id,
                "first_name": ap.first_name,
                "last_name": ap.last_name,
                "email": ap.email,
                "phone": ap.phone,
                "resume_url": resume_url,
                "applied_at": str(app.applied_at),
                "status": app.status,
                "is_rejected": app.is_rejected,
                "is_top_application": app.is_top_application,
            },
            "status_workflow": STATUS_WORKFLOW,
            "current_status": current_status,
            "current_step": current_status["order"],
            "total_steps": total_steps,
            "progress_percentage": progress,
            "available_statuses": available,
        })
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def update_application_status(request: Request, job_id: int, application_id: int, schema: UpdateStatusSchema, db: AsyncSession):
    try:
        profile = await _get_recruiter_profile(request, db)
        if not profile:
            return send_error_response(request, 404, "Profile not found")

        job = await db.scalar(select(Job).where(Job.job_id == job_id, Job.posted_by_id == profile.id))
        if not job:
            return send_error_response(request, 404, "Job not found")

        app = await db.scalar(select(Application).where(Application.application_id == application_id, Application.job_id == job.job_id))
        if not app:
            return send_error_response(request, 404, "Application not found")

        if app.is_rejected:
            return send_error_response(request, 400, "Cannot update status of a rejected application")

        current = next((s for s in STATUS_WORKFLOW if s["id"] == app.status), None)
        new = next((s for s in STATUS_WORKFLOW if s["id"] == schema.status), None)

        if not current or not new:
            return send_error_response(request, 400, "Invalid status")
        if new["order"] <= current["order"]:
            return send_error_response(request, 400, "Cannot move status backward")

        app.status = schema.status
        app.reviewed_at = datetime.datetime.now(datetime.timezone.utc)
        await db.flush()
        return send_json_response(200, "Status updated successfully", data={"status": schema.status})
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def reject_application(request: Request, schema: ManageApplicationSchema, db: AsyncSession):
    try:
        profile = await _get_recruiter_profile(request, db)
        if not profile:
            return send_error_response(request, 404, "Profile not found")

        job = await db.scalar(select(Job).where(Job.job_id == schema.job_id, Job.posted_by_id == profile.id))
        if not job:
            return send_error_response(request, 404, "Job not found")

        app = await db.scalar(select(Application).where(Application.application_id == schema.application_id, Application.job_id == job.job_id))
        if not app:
            return send_error_response(request, 404, "Application not found")

        if app.is_rejected:
            return send_error_response(request, 400, "Application already rejected")

        app.is_rejected = True
        await db.flush()
        return send_json_response(200, "Application rejected successfully")
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def toggle_top_application(request: Request, schema: ManageApplicationSchema, db: AsyncSession):
    try:
        profile = await _get_recruiter_profile(request, db)
        if not profile:
            return send_error_response(request, 404, "Profile not exist")

        job = await db.scalar(select(Job).where(Job.job_id == schema.job_id, Job.posted_by_id == profile.id))
        if not job:
            return send_error_response(request, 404, "Job not exist")

        application = await db.scalar(select(Application).where(Application.application_id == schema.application_id, Application.job_id == job.job_id))
        if not application:
            return send_error_response(request, 404, "Application not exist")

        application.is_top_application = not application.is_top_application
        await db.flush()
        return send_json_response(200, "Top application updated", data={"is_top_application": app.is_top_application})
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def organization_meta(request: Request, db: AsyncSession):
    try:
        countries = (await db.scalars(select(Country))).all()
        return send_json_response(200, "OK", data={"country_choices": [{"id": c.id, "name": c.name} for c in countries]})
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def get_organization_profile(request: Request, db: AsyncSession):
    try:
        profile = await _get_recruiter_profile(request, db)
        if not profile:
            return send_json_response(200, "OK", data={
                "is_recruiter_profile_complete": False,
            })

        org = await db.scalar(
            select(Organization)
            .where(Organization.user_id == profile.id)
            .options(selectinload(Organization.country), selectinload(Organization.state), selectinload(Organization.city))
        )

        if not org:
            return send_json_response(200, "OK", data={
                "is_recruiter_profile_complete": True,
                "organization_name": "", 
                "email": "", 
                "website": "",
                "organization_address": "", 
                "country": None,
                "state": None,
                "location": None,
                "postal_code": "",
                "logo": None,
            })

        return send_json_response(200, "OK", data={
            "is_recruiter_profile_complete": True,
            "organization_name": org.name,
            "email": org.email,
            "website": org.website,
            "organization_address": org.address,
            "country": {"id": org.country.id, "name": org.country.name} if org.country else None,
            "state": {"id": org.state.id, "name": org.state.name} if org.state else None,
            "location": {"id": org.city.id, "name": org.city.name} if org.city else None,
            "postal_code": org.postal_code,
            "logo": org.logo,
        })
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def update_organization_profile(request: Request, schema: OrganizationProfileSchema, db: AsyncSession):
    try:
        if schema.logo:
            contents = await schema.logo.read()
            if len(contents) > 2 * 1024 * 1024:
                return send_error_response(request, 422, "Logo must be smaller than 2MB")
            logo_key = f"jobs/organizations/{uuid.uuid4()}{schema.logo.filename[-4:]}"
            await upload_to_s3(contents, logo_key, schema.logo.content_type)
        else:
            logo_key = None

        profile = await _get_recruiter_profile(request, db)
        if not profile:
            return send_error_response(request, 404, "Profile not found")

        org = await db.scalar(select(Organization).where(Organization.user_id == profile.id))
        if org:
            org.name = schema.organization_name
            org.email = schema.email
            org.website = schema.website
            org.address = schema.organization_address
            org.country_id = schema.country
            org.state_id = schema.state
            org.location_id = schema.location
            org.postal_code = schema.postal_code
            if logo_key:
                org.logo = logo_key
        else:
            import random as _r
            org = Organization(
                organization_id=_r.randint(10_000_000, 99_999_999),
                user_id=profile.id,
                name=schema.organization_name,
                email=schema.email,
                website=schema.website,
                address=schema.organization_address,
                country_id=schema.country,
                state_id=schema.state,
                location_id=schema.location,
                postal_code=schema.postal_code,
                logo=logo_key,
            )
            db.add(org)

        await db.flush()
        return send_json_response(200, "Organization profile saved successfully")
    except Exception:
        import traceback, sys; traceback.print_exc(file=sys.stderr)
        return send_error_response(request, 500, "Internal server error")

async def recruiter_meta(request: Request):
    roles = ["RECRUITER", "HIRING_MANAGER", "TALENT_ACQUISITION", "HR"]
    return send_json_response(200, "OK", data={
        "role_choices": [{"value": r, "label": r.replace("_", " ").title()} for r in roles]
    })

async def get_recruiter_profile(request: Request, db: AsyncSession):
    try:
        profile = await _get_recruiter_profile(request, db)
        if not profile:
            return send_json_response(200, "OK", data={
                "is_profile_complete": False,
            })
        return send_json_response(200, "OK", data={
            "is_profile_complete": True,
            "first_name": profile.first_name,
            "last_name": profile.last_name or "",
            "email": profile.email,
            "phone": profile.phone or "",
            "company": profile.organization_name,
            "role": profile.role,
            "years_of_experience": profile.years_of_experience,
            "bio": profile.bio,
            "profile_pic_url": profile.profile_pic_url,
            "is_verified": profile.is_verified,
        })
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def update_recruiter_profile(request: Request, schema: RecruiterProfileSchema, db: AsyncSession):
    try:
        if schema.profile_pic:
            allowed = ["image/jpeg", "image/jpg", "image/png"]
            if schema.profile_pic.content_type not in allowed:
                return send_error_response(request, 422, "Only JPG, JPEG, or PNG allowed")
            contents = await schema.profile_pic.read()
            if len(contents) > 2 * 1024 * 1024:
                return send_error_response(request, 422, "Image must be smaller than 2MB")
            pic_key = f"jobs/recruiters/{request.state.user.user_id}/profile/{uuid.uuid4()}.jpg"
            await upload_to_s3(contents, pic_key, schema.profile_pic.content_type)
        else:
            pic_key = None

        profile = await _get_recruiter_profile(request, db)
        if not profile:
            return send_error_response(request, 404, "Profile not exist")

        profile.first_name = schema.first_name
        profile.last_name = schema.last_name
        profile.organization_name = schema.company
        profile.role = schema.role
        profile.years_of_experience = schema.years_of_experience
        profile.bio = schema.bio
        if pic_key:
            profile.profile_pic_url = pic_key

        await db.flush()
        return send_json_response(200, "Profile updated successfully")
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def send_email_otp(request: Request, schema: EmailOtpSchema, db: AsyncSession):
    try:
        existing = await db.scalar(select(RecruiterProfile).where(RecruiterProfile.email == schema.new_email))
        profile = await _get_recruiter_profile(request, db)
        if existing and existing.id != (profile.id if profile else None):
            return send_error_response(request, 400, "Email already in use")

        otp = str(random.randint(100000, 999999))
        user_id = request.state.user.user_id
        await cache_set(f"email_otp_{user_id}", {"otp": otp, "new_email": schema.new_email}, ttl=300)
        await send_mail_async(
            subject="Your Email Verification Code",
            body=f"Your verification code is: {otp}",
            to=[schema.new_email],
        )
        return send_json_response(200, "OTP sent successfully")
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def verify_email_otp(request: Request, schema: EmailOtpVerifySchema, db: AsyncSession):
    try:
        user_id = request.state.user.user_id
        cached = await cache_get(f"email_otp_{user_id}")
        if not cached:
            return send_error_response(request, 400, "OTP expired. Please request a new one.")
        if cached["otp"] != schema.otp:
            return send_error_response(request, 400, "Invalid OTP. Please try again.")
        if cached["new_email"] != schema.new_email:
            return send_error_response(request, 400, "Email mismatch.")

        profile = await _get_recruiter_profile(request, db)
        if profile:
            profile.email = schema.new_email
            await db.flush()
        await cache_delete(f"email_otp_{user_id}")
        return send_json_response(200, "Email updated successfully")
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def send_phone_otp(request: Request, schema: PhoneOtpSchema):
    try:
        user_id = request.state.user.user_id
        otp = str(random.randint(100000, 999999))
        await cache_set(f"phone_otp_{user_id}", {"otp": otp, "phone": schema.phone}, ttl=300)
        # TODO: integrate SMS provider
        return send_json_response(200, "OTP sent successfully")
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def verify_phone_otp(request: Request, schema: PhoneOtpVerifySchema, db: AsyncSession):
    try:
        user_id = request.state.user.user_id
        cached = await cache_get(f"phone_otp_{user_id}")
        if not cached:
            return send_error_response(request, 400, "OTP expired. Please request a new one.")
        if cached["otp"] != schema.otp:
            return send_error_response(request, 400, "Invalid OTP. Please try again.")
        if cached["phone"] != schema.phone:
            return send_error_response(request, 400, "Phone number mismatch.")

        profile = await _get_recruiter_profile(request, db)
        if profile:
            profile.phone = schema.phone
            await db.flush()
        await cache_delete(f"phone_otp_{user_id}")
        return send_json_response(200, "Phone verified successfully")
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def get_recruiter_settings(request: Request, db: AsyncSession):
    try:
        profile = await _get_recruiter_profile(request, db)
        if not profile:
            return send_json_response(200, "OK", data={
                "is_recruiter_profile_complete": False,
            })
        
        settings = await db.scalar(select(RecruiterSettings).options(selectinload(
            RecruiterSettings.country
        )).where(RecruiterSettings.user_id == profile.id))
        countries = (await db.scalars(select(Country))).all()

        return send_json_response(200, "OK", data={
            "is_recruiter_profile_complete": True,
            "countries": [{"iso2": c.iso2, "name": c.name} for c in countries],
            "country": settings.country.iso2 if settings.country else "IN",
            "currencies": [
                {"code": "INR", "name": "Indian Rupee"},
                {"code": "USD", "name": "US Dollar"},
                {"code": "EUR", "name": "Euro"},
                {"code": "GBP", "name": "British Pound"},
            ],
            "currency_type": settings.currency_type if settings else "INR",
        })
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def update_recruiter_settings(request: Request, schema: RecruiterSettingsSchema, db: AsyncSession):
    try:
        profile = await _get_recruiter_profile(request, db)
        if not profile:
            return send_error_response(request, 404, "Profile not found")

        settings = await db.scalar(select(RecruiterSettings).where(RecruiterSettings.user_id == profile.id))

        country_id = None
        if schema.country:
            country = await db.scalar(select(Country).where(Country.iso2 == schema.country))
            if not country:
                return send_error_response(request, 400, "Invalid country selected")
            country_id = country.id

        if settings:
            settings.country_id = country_id
            settings.currency_type = schema.currency_type
        else:
            db.add(RecruiterSettings(user_id=profile.id, country_id=country_id, currency_type=schema.currency_type))

        await db.flush()
        return send_json_response(200, "Settings updated successfully")
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def get_account(request: Request, db: AsyncSession):
    try:
        external_user_id = request.state.user.external_user_id

        user = await db.scalar(
            select(
                User
            )
            .options(
                selectinload(User.location)
            )
            .where(User.user_id == external_user_id)
        )
        if not user:
            return send_error_response(request, 400, "User not exist")
    
        return send_json_response(200, "OK", data={
            "user_id": user.user_id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "profile_pic_url_small": f"{PROFILE_BASE_URL}/{user.profile_pic_url_96x96}",
            "updated_at": user.updated_at.isoformat() if user.updated_at else None,
            "about": user.about,
            "is_email_verified": user.is_email_verified,
            "account_type": user.account_type,
            "location": {
                "geo": user.location.geo,
                "latitude": str(user.location.latitude),
                "longitude": str(user.location.longitude),
                "location_type": user.location.location_type,
            } if user.location else None,
            "created_at": int(user.created_at.timestamp()) if user.created_at else None
        })
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def get_plans(request: Request, db: AsyncSession):
    try:
        profile = await _get_recruiter_profile(request, db)
        if not profile:
            return send_error_response(request, 404, "Profile not exist")

        plans = (await db.scalars(select(Plan).where(Plan.is_free == False))).all() 
        now = datetime.datetime.now(datetime.timezone.utc)

        return send_json_response(200, "OK", data={
            "current_plan": {"id": profile.plan_id, "name": profile.plan.name} if profile.plan_id else None,
            "is_trial_active": profile.is_trial_active,
            "trial_end_date": str(profile.trial_end_date) if profile.trial_end_date else None,
            "trial_ended": (not profile.is_trial_active and profile.trial_end_date and profile.trial_end_date.replace(tzinfo=datetime.timezone.utc) < now),
            "available_plans": [
                {"id": p.id, "name": p.name, "price": float(p.price), "features": p.features}
                for p in plans
            ],
        })
    except Exception:
        return send_error_response(request, 500, "Internal server error")