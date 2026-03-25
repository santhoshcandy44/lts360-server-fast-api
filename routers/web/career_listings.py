from fastapi import APIRouter, Depends, File, Query, Request, UploadFile
from typing import Optional
from schemas.app_schemas import SearchChatsSchema
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from routers.middleware.web.auth_middleware import authenticate_token
from controllers.web import career_listings_controller
from schemas.web.career_listing_schemas import (
    ApplicationsByJobSchema,
    DashboardSchema,
    GoogleLoginSchema,
    EmailLoginSchema,
    JobCreateSchema,
    JobIdSchema,
    JobListingsFilterSchema,
    LocationsSearchSchema,
    ManageApplicationSchema,
    PageSchema,
    SearchQuerySchema,
    StatesSearchSchema,
    StatusSchema,
    ExtendSchema,
    UpdateStatusSchema,
    OrganizationProfileSchema,
    RecruiterProfileSchema,
    RecruiterSettingsSchema,
    EmailOtpSchema,
    EmailOtpVerifySchema,
    PhoneOtpSchema,
    PhoneOtpVerifySchema,
    create_organization_profile_form,
    create_recruiter_profile_form,
)

router = APIRouter(prefix="/career-listings", tags=["Career Listings"])

@router.post("/auth/signin/google/lts360")
async def google_login(request: Request, schema: GoogleLoginSchema, db: AsyncSession = Depends(get_db)):
    return await career_listings_controller.google_signin(request, schema, db)

@router.post("/auth/signin/lts360")
async def email_login(request: Request, schema: EmailLoginSchema, db: AsyncSession = Depends(get_db)):
    return await career_listings_controller.email_signin(request, schema, db)

@router.get("/dashboard")
async def dashboard(
    request: Request,
    schema: DashboardSchema = Depends(),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(authenticate_token),
):
    return await career_listings_controller.dashboard(request, schema, db)

@router.get("/countries/search")
async def search_countries(
    request: Request,
    schema: SearchQuerySchema = Depends(),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(authenticate_token),
):
    return await career_listings_controller.search_countries(request, schema, db)

@router.get("/states/search")
async def search_states(
    request: Request,
    schema: StatesSearchSchema = Depends(),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(authenticate_token),
):
    return await career_listings_controller.search_states(request, schema, db)

@router.get("/locations/search")
async def search_cities(
    request: Request,
    schema: LocationsSearchSchema = Depends(),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(authenticate_token),
):
    return await career_listings_controller.search_cities(request, schema, db)

@router.get("/employment-types/search")
async def search_employment_types(
    request: Request,
    schema: SearchQuerySchema = Depends(),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(authenticate_token),
):
    return await career_listings_controller.search_employment_types(request, schema, db)

@router.get("/educations/search")
async def search_education(
    request: Request,
    schema: SearchQuerySchema = Depends(),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(authenticate_token),
):
    return await career_listings_controller.search_education(request, schema, db)

@router.get("/industries/search")
async def search_industry(
    request: Request,
    schema: SearchQuerySchema = Depends(),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(authenticate_token),
):
    return await career_listings_controller.search_industry(request, schema, db)

@router.get("/departments/search")
async def search_department(
    request: Request,
    schema: SearchQuerySchema = Depends(),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(authenticate_token),
):
    return await career_listings_controller.search_department(request, schema, db)

@router.get("/roles/search")
async def search_role(
    request: Request,
    schema: SearchQuerySchema = Depends(),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(authenticate_token),
):
    return await career_listings_controller.search_role(request, schema, db)

@router.get("/skills/search")
async def search_skills(
    request: Request,
    schema: SearchQuerySchema = Depends(),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(authenticate_token),
):
    return await career_listings_controller.search_skills(request, schema, db)

@router.get("/job-listings/meta")
async def get_job_listings_meta(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(authenticate_token),
):
    return await career_listings_controller.get_job_listings_meta(request, db)

@router.get("/job-listings")
async def get_job_listings(
    request: Request,
    schema: JobListingsFilterSchema = Depends(),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(authenticate_token),
):
    return await career_listings_controller.get_job_listings(request, schema, db)

@router.post("/job-listings")
async def create_job_listing(
    request: Request,
    schema: JobCreateSchema = Depends(), 
    db: AsyncSession = Depends(get_db),
    _: None = Depends(authenticate_token),
):
    return await career_listings_controller.create_job_listing(request, schema, db)

@router.get("/job-listings/{job_id}")
async def get_job_listing(
    request: Request,
    schema: JobCreateSchema = Depends(), 
    db: AsyncSession = Depends(get_db),
    _: None = Depends(authenticate_token),
):
    return await career_listings_controller.get_job_listing(request, schema, db)

@router.put("/job-listings/{job_id}")
async def update_job_listing(
    request: Request,
    jobIdParamSchema: JobIdSchema = Depends(),
    schema: JobCreateSchema = Depends(), 
    db: AsyncSession = Depends(get_db),
    _: None = Depends(authenticate_token),
):
    return await career_listings_controller.update_job_listing(request, jobIdParamSchema.job_id, schema, db)

@router.delete("/job-listings/{job_id}")
async def delete_job_listing(
    request: Request,
    schema: JobIdSchema = Depends(),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(authenticate_token),
):
    return await career_listings_controller.delete_job_listing(request, schema, db)

@router.post("/job-listings/{job_id}/status")
async def update_job_status(
    request: Request,
    schema: StatusSchema = Depends(),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(authenticate_token),
):
    return await career_listings_controller.update_job_status(request, schema, db)

@router.post("/job-listings/{job_id}/extend-expiry")
async def extend_expiry(
    request: Request,
    schema: ExtendSchema = Depends(),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(authenticate_token),
):
    return await career_listings_controller.extend_expiry(request, schema, db)

@router.get("/applications")
async def get_applications(
    request: Request,
    schema: PageSchema = Depends(),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(authenticate_token),
):
    return await career_listings_controller.get_applications(request, schema, db)

@router.get("/applications/{job_id}")
async def get_applications_by_job(
    request: Request,
    job_id: int,
    schema: ApplicationsByJobSchema = Depends(),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(authenticate_token),
):
    return await career_listings_controller.get_applications_by_job(request, schema, db)

@router.get("/applications/{job_id}/{application_id}/manage")
async def manage_application(
    request: Request,
    schema: ManageApplicationSchema = Depends(),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(authenticate_token),
):
    return await career_listings_controller.manage_application(request, schema, db)

@router.post("/applications/{job_id}/{application_id}/update-status")
async def update_application_status(
    request: Request,
    schema: UpdateStatusSchema = Depends(),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(authenticate_token),
):
    return await career_listings_controller.update_application_status(request, schema, db)

@router.post("/applications/{job_id}/{application_id}/reject")
async def reject_application(
    request: Request,
    schema: ManageApplicationSchema = Depends(),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(authenticate_token),
):
    return await career_listings_controller.reject_application(request, schema, db)

@router.post("/applications/{job_id}/{application_id}/toggle-top")
async def toggle_top_application(
    request: Request,
    schema: ManageApplicationSchema = Depends(),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(authenticate_token),
):
    return await career_listings_controller.toggle_top_application(request, schema, db)

@router.get("/organization-profile/meta")
async def organization_meta(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(authenticate_token),
):
    return await career_listings_controller.organization_meta(request, db)

@router.get("/organization-profile")
async def get_organization_profile(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(authenticate_token),
):
    return await career_listings_controller.get_organization_profile(request, db)

@router.put("/organization-profile")
async def update_organization_profile(
    request: Request,
    schema: OrganizationProfileSchema = Depends(),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(authenticate_token),
):
    return await career_listings_controller.update_organization_profile(request, schema, db)

@router.get("/recruiter-profile/meta")
async def recruiter_meta(request: Request, _: None = Depends(authenticate_token)):
    return await career_listings_controller.recruiter_meta(request)

@router.get("/recruiter-profile")
async def get_recruiter_profile(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(authenticate_token),
):
    return await career_listings_controller.get_recruiter_profile(request, db)

@router.put("/recruiter-profile")
async def update_recruiter_profile(
    request: Request,
    schema: RecruiterProfileSchema = Depends(),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(authenticate_token),
):
    return await career_listings_controller.update_recruiter_profile(request, schema, db)

@router.post("/profile-verification/send-otp")
async def send_email_otp(
    request: Request,
    schema: EmailOtpSchema,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(authenticate_token),
):
    return await career_listings_controller.send_email_otp(request, schema, db)

@router.post("/profile-verification/verify-otp")
async def verify_email_otp(
    request: Request,
    schema: EmailOtpVerifySchema,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(authenticate_token),
):
    return await career_listings_controller.verify_email_otp(request, schema, db)

@router.post("/phone-verification/send-otp")
async def send_phone_otp(
    request: Request,
    schema: PhoneOtpSchema,
    _: None = Depends(authenticate_token),
):
    return await career_listings_controller.send_phone_otp(request, schema)

@router.post("/phone-verification/verify-otp")
async def verify_phone_otp(
    request: Request,
    schema: PhoneOtpVerifySchema,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(authenticate_token),
):
    return await career_listings_controller.verify_phone_otp(request, schema, db)

@router.get("/recruiter-settings")
async def get_recruiter_settings(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(authenticate_token),
):
    return await career_listings_controller.get_recruiter_settings(request, db)

@router.post("/recruiter-settings")
async def update_recruiter_settings(
    request: Request,
    schema: RecruiterSettingsSchema,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(authenticate_token),
):
    return await career_listings_controller.update_recruiter_settings(request, schema, db)

@router.get("/account")
async def get_account(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(authenticate_token),
):
    return await career_listings_controller.get_account(request, db)

@router.post("/account/signout")
async def logout(request: Request):
    return await career_listings_controller.logout(request)

@router.get("/plans")
async def get_plans(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(authenticate_token),
):
    return await career_listings_controller.get_plans(request, db)