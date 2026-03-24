from fastapi import APIRouter, Depends, Query, Path, Request
from routers.middleware.auth_middleware import authenticate_token
from database import get_db

from schemas.job_schemas import (
    GuestGetJobsSchema,

    LocationSearchSuggestionsSchema,
    RoleSearchSuggestionsSchema,
    GetJobsSchema,
    JobIdSchema,
    GetSavedJobsSchema,

    SkillSearchSuggestionsSchema,
    ApplicantProfileSchema,

    UpdateProfessionalInfoSchema,
    UpdateResumeSchema,
    UpdateEducationSchema,
    UpdateExperienceSchema,
    UpdateSkillsSchema,
    UpdateLanguagesSchema,
    UpdateCertificatesSchema,
    UpdateNoExperienceSchema,

    UpdateIndustriesSchema,

    application_profile_schema_params,
    create_get_jobs_params,
    create_guest_get_jobs_params,
    create_update_professional_info_form,
    create_update_resume_form,
    create_update_certificates_form
)

from controllers import job_controller
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/jobs", tags=["Jobs"])

@router.get("/guest")
async def guest_get_job_listings(
    request:      Request,
    schema: GuestGetJobsSchema = Depends(create_guest_get_jobs_params),
    db:           AsyncSession = Depends(get_db)
):
    return await job_controller.guest_get_job_listings(request, schema, db)

@router.get("/guest/locations/search-suggestions")
async def guest_search_location_suggestions(
    request:      Request,
    schema: LocationSearchSuggestionsSchema = Depends(),
    db:           AsyncSession = Depends(get_db)
):
    return await job_controller.location_search_suggestions(request, schema, db)

@router.get("/guest/roles/search-suggestions")
async def guest_search_role_suggestions(
    request:      Request,
    schema: RoleSearchSuggestionsSchema = Depends(),
    db:           AsyncSession = Depends(get_db)
):
    return await job_controller.role_search_suggestions(request, schema, db)

@router.get("/guest/industries")
async def guest_get_industries(
    request:      Request,
    db:           AsyncSession = Depends(get_db)
):
    return await job_controller.guest_get_industries(request, db)

@router.get("/guest/{job_id}")
async def guest_get_job_by_job_id(
    request:      Request,
    schema: JobIdSchema = Depends(),
    db:           AsyncSession = Depends(get_db)
):
    return await job_controller.get_job_by_job_id(request, schema, db)

@router.get("")
async def get_job_listings(
    request:      Request,
    schema: GetJobsSchema = Depends(create_get_jobs_params),
    db:           AsyncSession = Depends(get_db),
    _: None =Depends(authenticate_token)
):
    return await job_controller.get_job_listings(request, schema, db)

@router.get("/bookmarks")
async def get_saved_jobs(
    request:      Request,
    schema: GetSavedJobsSchema = Depends(),
    db:           AsyncSession = Depends(get_db),
    _: None =Depends(authenticate_token)
):
    return await job_controller.get_saved_jobs(request, schema, db)

@router.get("/industries")
async def get_industries(
    request:      Request,
    db:           AsyncSession = Depends(get_db),
    _: None =Depends(authenticate_token)
    ):
    return await job_controller.get_industries(request, db)


@router.put("/industries")
async def update_industries(
    request:      Request,
    schema: UpdateIndustriesSchema,
    db:           AsyncSession = Depends(get_db),
    _: None =Depends(authenticate_token)

):
    return await job_controller.update_industries(request, schema, db)
    
@router.get("/{job_id}")
async def get_job_by_id(
    request:      Request,
    schema: JobIdSchema = Depends(),
    db:           AsyncSession = Depends(get_db),
    _: None =Depends(authenticate_token)
):
    return await job_controller.get_job_by_job_id(request, schema, db)

@router.post("/{job_id}/apply")
async def apply_job(
    request:      Request,
    schema: JobIdSchema = Depends(),
    db:           AsyncSession = Depends(get_db),
    _: None =Depends(authenticate_token)
):
    return await job_controller.apply_job(request, schema, db)

@router.post("/{job_id}/bookmark")
async def bookmark_job(
    request:      Request,
    schema: JobIdSchema = Depends(),
    db:           AsyncSession = Depends(get_db),
    _: None =Depends(authenticate_token)
):
    return await job_controller.bookmark_job(request, schema, db)

@router.delete("/{job_id}/bookmark")
async def unbookmark_job(
    request:      Request,
    schema: JobIdSchema = Depends(),
    db:           AsyncSession = Depends(get_db),
    _: None =Depends(authenticate_token)
):
    return await job_controller.unbookmark_job(request, schema, db)

@router.get("/locations/search-suggestions")
async def search_location_suggestions(
    request:      Request,
    schema: LocationSearchSuggestionsSchema = Depends(),
    db:           AsyncSession = Depends(get_db),
    _: None =Depends(authenticate_token)
):
    return await job_controller.location_search_suggestions(request, schema, db)

@router.get("/roles/search-suggestions")
async def search_role_suggestions(
    request:      Request,
    schema: RoleSearchSuggestionsSchema = Depends(),
    db:           AsyncSession = Depends(get_db),
    _: None =Depends(authenticate_token)
):
    return await job_controller.role_search_suggestions(request, schema, db)

#Applicant Profile
@router.get("/applicant/profile")
async def get_applicant_profile(
    request:      Request,
    schema: ApplicantProfileSchema = Depends(application_profile_schema_params),
    db:           AsyncSession = Depends(get_db),
    _: None =Depends(authenticate_token)
):
    return await job_controller.get_profile(request, schema, db)

@router.put("/applicant/professional-info")
async def update_professional_info(
    request:      Request,
    schema: UpdateProfessionalInfoSchema = Depends(create_update_professional_info_form),
    db:           AsyncSession = Depends(get_db),
    _: None =Depends(authenticate_token)
):
    return await job_controller.update_profile(request, schema, db)

@router.put("/applicant/educations")
async def update_education(
    request:      Request,
    schema: UpdateEducationSchema = Depends(),
    db:           AsyncSession = Depends(get_db),
    _: None =Depends(authenticate_token)
):
    return await job_controller.update_educations(request, schema, db)

@router.put("/applicant/experiences")
async def update_experience(
    request:      Request,
    schema: UpdateExperienceSchema,
    db:           AsyncSession = Depends(get_db),
    _: None =Depends(authenticate_token)
):
    return await job_controller.update_experiences(request, schema, db)

@router.put("/applicant/experiences/no-experience")
async def update_no_experience(
    request:      Request,
    schema: UpdateNoExperienceSchema,
    db:           AsyncSession = Depends(get_db),
    _: None =Depends(authenticate_token)
):
    return await job_controller.update_no_experience(request, schema, db)

@router.get("/applicant/profile/skills/search-suggestions")
async def search_skills_suggestions(
    request:      Request,
    schema: SkillSearchSuggestionsSchema = Depends(),
    db:           AsyncSession = Depends(get_db),
    _: None =Depends(authenticate_token)
):
    return await job_controller.skill_search_suggestions(request, schema, db)

@router.put("/applicant/skills")
async def update_skills(
    request:      Request,
    schema: UpdateSkillsSchema = Depends(),
    db:           AsyncSession = Depends(get_db),
    _: None =Depends(authenticate_token)
):
    return await job_controller.update_skills(request, schema, db)

@router.put("/applicant/languages")
async def update_languages(
    request:      Request,
    schema: UpdateLanguagesSchema = Depends(),
    db:           AsyncSession = Depends(get_db),
    _: None =Depends(authenticate_token)
):
    return await job_controller.update_languages(request, schema, db)

@router.put("/applicant/resume")
async def update_resume(
    request:      Request,
    schema: UpdateResumeSchema = Depends(create_update_resume_form),
    db:           AsyncSession = Depends(get_db),
    _: None =Depends(authenticate_token)
):
    return await job_controller.update_resume(request, schema, db)

@router.put("/applicant/certificates")
async def update_certificates(
    request: Request,
    schema: UpdateCertificatesSchema = Depends(create_update_certificates_form),
    db:           AsyncSession = Depends(get_db),
    _: None =Depends(authenticate_token)
):
    return await job_controller.update_certificates(request, schema, db)