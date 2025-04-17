import logging
from datetime import datetime
def validate_job_post(job: dict):
    """
    Validate the structure of a job post dictionary.
    """
    required_fields = [
        "job_id", "employer_id", "job_title", "employment_type", "gender", "quantity",
        "level", "description", "qualification", "skills", "salary", "benefits",
        "deadline", "status", "source"
    ]

    missing_fields = [field for field in required_fields if field not in job]
    if missing_fields:
        raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")

    # Ensure status is valid
    valid_statuses = {"pending", "approved", "rejected", "closed", "open", "filled"}
    job_status = job.get("status", "").strip().lower()  # Normalize input
    if not job_status:
        raise ValueError("Missing or empty status field in job post.")

    if job_status not in valid_statuses:
        raise ValueError(f"Invalid status: {job_status}. Expected one of {', '.join(valid_statuses)}.")

    # Ensure source is valid
    valid_sources = {"job_post", "vacancy"}
    job_source = job.get("source", None)  # Default to None
    if job_source not in valid_sources:
        raise ValueError(f"Invalid source: {job_source}. Expected 'job_post' or 'vacancy'.")

    return job


def validate_job_post_data(job_post: dict):
    """
    Validate the job post data dictionary.
    """
    required_fields = [
        "job_id" , "source" ,"employer_id", "job_title", "employment_type", "gender", "quantity",
        "level", "description", "qualification", "skills", "salary",
        "benefits", "deadline"
    ]

    valid_genders = {"Male", "Female", "Any"}
    # Detect missing or empty fields
    missing_fields = [field for field in required_fields if field not in job_post or job_post[field] is None]

    if missing_fields:
        print(f"Missing fields: {missing_fields}")  # Debugging line
        raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")

        # Validate gender
        # Case-insensitive validation for gender
    gender_value = job_post.get("gender", "").capitalize()  # Normalize to title case
    if gender_value not in valid_genders:
        raise ValueError(f"Invalid gender value: {job_post.get('gender')}. Must be one of {valid_genders}.")

        # Debugging log
    logging.debug(f"Validating gender: {job_post.get('gender')}, normalized to: {gender_value}")

    # Validate deadline
    deadline = job_post.get("deadline")
    try:
        deadline_date = datetime.strptime(deadline, "%Y-%m-%d").date()
        if deadline_date < datetime.now().date():
            raise ValueError(f"Invalid deadline: {deadline}. Deadline must be today or later.")
    except ValueError:
        raise ValueError(f"Invalid date format for deadline: {deadline}. Expected format: YYYY-MM-DD.")

    # Ensure status is valid
    valid_statuses = {"pending", "approved", "rejected", "closed", "open", "filled"}
    status = job_post.get("status", "pending")  # Default to 'pending'
    if status not in valid_statuses:
        raise ValueError(f"Invalid status: {status}. Expected one of {', '.join(valid_statuses)}.")

    return job_post



def validate_job_post_data_for_job_preview(job_post: dict):
    """
    Validate the job post data dictionary.
    """
    required_fields = [
        "employer_id", "job_title", "employment_type", "gender", "quantity",
        "level", "description", "qualification", "skills", "salary",
        "benefits", "deadline"
    ]

    valid_genders = {"Male", "Female", "Any"}
    # Detect missing or empty fields
    missing_fields = [field for field in required_fields if field not in job_post or job_post[field] is None]

    if missing_fields:
        print(f"Missing fields: {missing_fields}")  # Debugging line
        raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")

        # Validate gender
        # Case-insensitive validation for gender
    gender_value = job_post.get("gender", "").capitalize()  # Normalize to title case
    if gender_value not in valid_genders:
        raise ValueError(f"Invalid gender value: {job_post.get('gender')}. Must be one of {valid_genders}.")

        # Debugging log
    logging.debug(f"Validating gender: {job_post.get('gender')}, normalized to: {gender_value}")

    # Validate deadline
    deadline = job_post.get("deadline")
    try:
        deadline_date = datetime.strptime(deadline, "%Y-%m-%d").date()
        if deadline_date < datetime.now().date():
            raise ValueError(f"Invalid deadline: {deadline}. Deadline must be today or later.")
    except ValueError:
        raise ValueError(f"Invalid date format for deadline: {deadline}. Expected format: YYYY-MM-DD.")

    # Ensure status is valid
    valid_statuses = {"pending", "approved", "rejected", "closed", "open", "filled"}
    status = job_post.get("status", "pending")  # Default to 'pending'
    if status not in valid_statuses:
        raise ValueError(f"Invalid status: {status}. Expected one of {', '.join(valid_statuses)}.")

    return job_post