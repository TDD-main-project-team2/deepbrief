from backend.repositories import organization_repository
from backend.app.dependencies import ensure_organization_member

def get_organization_by_user_id(user_id):
    organization = organization_repository.find_organization_by_user_id(user_id)
    ensure_organization_member(organization.id, user_id)

def get_organization_article_template_for_user(user_id, template_id):
    org = get_organization_by_user_id(user_id)
    return organization_repository.find_article_template_by_id(org.id, template_id)

def get_organization_evaluation_guideline_for_user(user_id, guideline_id):
    org = get_organization_by_user_id(user_id)
    return organization_repository.find_org_guideline_by_id(org.id, guideline_id)

def get_all_organization_article_templates(user_id):
    org = get_organization_by_user_id(user_id)
    return organization_repository.find_all_article_templates(org.id)