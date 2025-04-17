import asyncio
import io
import json
import tempfile

from fpdf import FPDF
import matplotlib.pyplot as plt
import xlsxwriter
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
    Update, ForceReply,
)
from telegram.error import BadRequest
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    ContextTypes,
)
from ..db.database import Database
from utils.validation import validate_job_post_data
from utils.validation import validate_job_post
from utils.validation import validate_job_post_data_for_job_preview

# Get the directory where main.py is located
current_dir = os.path.dirname(os.path.abspath(__file__))
translations_path = os.path.join(current_dir, "translations.json")

# Load translations
with open(translations_path, "r", encoding="utf-8") as file:
    translations = json.load(file)

# Initialize Database
db = Database()

# Enable logging
import logging
import os

# Ensure the user_documents directory exists
if not os.path.exists("user_documents"):
    os.makedirs("user_documents")

logging.basicConfig(level=logging.WARNING)
# Define states
(LANGUAGE, MOBILE, REGISTRATION_TYPE, JOB_SEEKER, JOB_SEEKER_DOB,JOB_SEEKER_GENDER, JOB_SEEKER_CONTACT_NUMBERS, JOB_SEEKER_LANGUAGES, JOB_SEEKER_QUALIFICATION, JOB_SEEKER_FIELD_OF_STUDY,
 JOB_SEEKER_CGPA, JOB_SEEKER_SKILLS, JOB_SEEKER_PROFILE_SUMMARY, JOB_SEEKER_SUPPORTING_DOCUMENTS, JOB_SEEKER_PORTFOLIO_LINK, MAIN_MENU, EDIT_PROFILE, EDIT_FIELD_VALUE,
 EMPLOYER_NAME, EMPLOYER_LOCATION,EMPLOYER_TYPE, ABOUT_COMPANY, EMPLOYER_DOCUMENTS,EMPLOYER_MAIN_MENU, EDIT_EMPLOYER_PROFILE, EDIT_EMPLOYER_FIELD_VALUE, VERIFICATION_DOCUMENTS,
 ADMIN_LOGIN, ADMIN_MAIN_MENU,BROADCAST_TYPE, BROADCAST_MESSAGE, CONFIRM_BROADCAST,
 POST_JOB_TITLE, POST_EMPLOYMENT_TYPE, POST_GENDER, POST_QUANTITY, POST_LEVEL, POST_DESCRIPTION, POST_QUALIFICATION, POST_SKILLS, POST_SALARY, POST_BENEFITS,
 POST_DEADLINE, JOB_PREVIEW, CONFIRM_POST,REJECT_JOB_REASON , CONFIRM_SUBMISSION, VIEW_APPLICATIONS, SELECT_JOB_POSTS_TO_SHARE,SELECT_JOB_TO_MANAGE,HANDLE_JOB_ACTIONS,
 CONFIRM_CLOSE, RESUBMIT_CONFIRMATION, DISPLAY_VACANCIES,SELECT_VACANCY,CONFIRM_SELECTION, WRITE_COVER_LETTER,
 MANAGE_USERS,REMOVE_JOB_SEEKERS, REMOVE_EMPLOYERS, REMOVE_APPLICATIONS, CLEAR_ALL_DATA, CONFIRM_REMOVAL, CLEAR_CONFIRMATION,
 DATABASE_MANAGEMENT, MANAGE_JOBS, AD_MANAGE_VACANCIES, LIST_JOBS, SEARCH_JOB_SEEKERS, REMOVE_JOB_SEEKERS_PAGINATED,
 SEARCH_EMPLOYERS, REMOVE_EMPLOYERS_PAGINATED, SEARCH_APPLICATIONS, REMOVE_APPLICATIONS_PAGINATED, EXPORT_DATA, SEARCH_JOBS, REMOVE_JOBS_PAGINATED,
 LIST_VACANCIES_PAGINATED, REMOVE_VACANCIES_PAGINATED, SEARCH_VACANCIES,  MANAGE_APPLICATIONS, LIST_APPLICATIONS_PAGINATED, SAVE_EDITED_FIELD,
 PROFILE_MENU, CONFIRM_DELETE_ACCOUNT, CONFIRM_CHANGE_LANGUAGE, SELECT_LANGUAGE, VIEW_PROFILE, EMPLOYER_PROFILE_MENU, CONFIRM_DELETE_MY_ACCOUNT, SELECT_EMPLOYER_LANGUAGE, CONFIRM_CHANGE_EMPLOYER_LANGUAGE,
 ACCEPT_REJECT_CONFIRMATION, REJECTION_REASON_INPUT, EMPLOYER_MESSAGE_INPUT,BAN_JOB_SEEKERS, BAN_EMPLOYERS, UNBAN_USERS, VIEW_BANNED_USERS,
 REASON_FOR_BAN, APPEAL_SUBMIT, REVIEW_APPEALS, HANDLE_APPEAL, BAN_JOB_SEEKERS_PAGINATED, SUBMIT_APPEAL, BAN_EMPLOYERS_PAGINATED,
 SEARCH_JOB_SEEKERS_FOR_BAN, REASON_FOR_BAN_JOB_SEEKER,  SEARCH_EMPLOYERS_FOR_BAN, REASON_FOR_BAN_EMPLOYER, UNBAN_USERS_MENU, UNBAN_SELECTION, UNBAN_ALL_CONFIRMATION, APPEAL_START, APPEAL_INPUT, APPEAL_REVIEW, BANNED_STATE,
 SEARCH_OPTIONS, ADVANCED_FILTERS, FILTER_JOB_TYPE, SEARCH_RESULTS, KEYWORD_SEARCH , FILTER_SALARY, FILTER_EXPERIENCE , VIEW_JOB_DETAILS, VIEWING_APPLICATIONS, APPLICATION_DETAILS, EXPORTING_APPLICATIONS, RENEW_VACANCY,  CONFIRM_RENEWAL,
 ANALYTICS_VIEW , ANALYTICS_TRENDS , ANALYTICS_DEMOGRAPHICS , ANALYTICS_RESPONSE , ANALYTICS_BENCHMARK , ANALYTICS_EXPORT,
 HELP_MENU, FAQ_SECTION, FAQ_CATEGORY, FAQ_QUESTION, JS_FAQ_SECTION,  JS_FAQ_CATEGORY, JS_FAQ_QUESTION, ADMIN_FAQ_SECTION, ADMIN_FAQ_CATEGORY, ADMIN_FAQ_QUESTION,
 RATE_OPTIONS, SEARCH_USER_FOR_RATING , RATE_DIMENSION, CONFIRM_REVIEW, SELECT_USER_FOR_RATING, ADD_COMMENT_OPTIONAL, REVIEW_SETTINGS,  MY_REVIEWS, REVIEW_DETAILS, SEARCH_REVIEWS, SUBMIT_COMMENT, PROMPT_FOR_COMMENT, POST_REVIEW,
 CONTACT_CATEGORY, CONTACT_PRIORITY, CONTACT_MESSAGE , ADMIN_REPLY_STATE, CONTACT_MANAGEMENT,  CONTACT_INBOX,  CONTACT_VIEW_MESSAGE, CONTACT_OUTBOX, CONTACT_PENDING, CONTACT_ANSWERED, CONTACT_STATS, CONTACT_CONFIRM_DELETE, VIEW_ERRORS,  ERROR_DETAIL ) = range(173)

# Helper function to fetch translations
def get_translation(user_id, key, **kwargs):
    # Retrieve the user's language preference from the database
    user_language = db.get_user_language(user_id)  # Assume this function returns 'en', 'am', 'om', etc.

    # Fetch the translations for the user's language or fall back to English
    language_translations = translations.get(user_language, translations.get("english", {}))

    # Get the translation, or return a detailed missing translation message
    translation = language_translations.get(key)
    if translation is None:
        return f"Translation not found for '{key}'"

    # If kwargs are provided, format the translation string using them
    return translation.format(**kwargs) if kwargs else translation


def is_profile_complete(user_profile, db):
    """Check if the user's profile is complete based on their registration type."""
    required_fields = ["registration_type", "full_name"]

    if user_profile.get("registration_type") == "employer":
        employer_profile = db.get_employer_profile(user_profile["user_id"])
        if not employer_profile:  # If no employer profile exists, it's incomplete
            return False
        # Ensure the employer profile has all required fields, including employer_id
        required_employer_fields = ["company_name", "city", "employer_type", "employer_id"]
        return all(employer_profile.get(field) for field in required_employer_fields)

    return all(user_profile.get(field) for field in required_fields)

#before
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the bot startup. Checks user registration and directs them accordingly."""
    user_id = get_user_id(update)
    user_profile = db.get_user_profile(user_id)

    # Check bans first
    is_banned = False
    ban_reason = ""

    # Check job seeker ban
    if db.is_user_banned(user_id=user_id, employer_id=None):
        is_banned = True
        ban_reason = db.get_ban_reason(user_id=user_id, employer_id=None)

    # Check employer ban
    employer_profile = db.get_employer_profile(user_id)
    if employer_profile and db.is_user_banned(user_id=None, employer_id=employer_profile.get("employer_id")):
        is_banned = True
        ban_reason = db.get_ban_reason(user_id=None, employer_id=employer_profile.get("employer_id"))

    if is_banned:
        # Send ban message with appeal button
        await context.bot.send_message(
            chat_id=user_id,
            text=f"🚫 You have been banned. Reason: {ban_reason}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📝 Appeal Ban", callback_data="appeal_start")]
            ])
        )
        return BANNED_STATE
    # Reset conversation state
    context.user_data.clear()

    # Check if the user started via an "apply" link
    start_param = update.effective_message.text.split(' ', 1)[-1] if update.effective_message.text else None
    if start_param and start_param.startswith("apply_"):
        job_id = start_param.split("_")[-1]
        context.user_data["job_id"] = job_id  # Store the job ID for later use

    # If user is new, start the registration process
    if not user_profile:
        await show_language_selection(update, context)
        return LANGUAGE

    try:
        # Ensure the profile is complete
        if not is_profile_complete(user_profile, db):
            await context.bot.send_message(
                chat_id=user_id,
                text="Your profile is incomplete. Please update missing information.",
                parse_mode="HTML"
            )
            # Redirect to the beginning of the registration process
            await show_language_selection(update, context)
            return LANGUAGE

        # Identify the user type (job seeker or employer)
        registration_type = user_profile.get("registration_type")
        full_name = user_profile.get("full_name")



        if registration_type == "employer":
            # Handle employer-specific logic
            employer_profile = db.get_employer_profile(user_id)
            if not employer_profile:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="Employer profile not found. Please complete registration.",
                    parse_mode="HTML"
                )
                return LANGUAGE  # Redirect to registration

            company_name = employer_profile.get("company_name") or full_name or "Employer"
            employer_id = employer_profile.get("employer_id")
            if not employer_id:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="Your employer ID is missing. Please contact support.",
                    parse_mode="HTML"
                )
                return ConversationHandler.END

            context.user_data["employer_id"] = employer_id

        else:  # Job seeker
            company_name = full_name or "Job Seeker"

        # Welcome message for returning users
        # await context.bot.send_message(
        #     chat_id=user_id,
        #     text=f"Welcome back, {company_name}!",
        #     parse_mode="HTML"
        # )

        # If the user started via an "apply" link, skip to writing the cover letter
        if "job_id" in context.user_data:
            job_id = context.user_data["job_id"]
            selected_job = db.get_job_by_id(job_id)

            if not selected_job:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="The job you are trying to apply for does not exist.",
                    parse_mode="HTML"
                )
                return MAIN_MENU

            context.user_data["selected_job"] = selected_job
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    f"You are applying for:\n\n"
                    f"<b>Job Title:</b> {escape_html(selected_job['job_title'])}\n"
                    f"<b>Employer:</b> {escape_html(selected_job.get('company_name', 'Not provided'))}\n"
                    f"<b>Deadline:</b> {escape_html(selected_job['application_deadline'])}"
                ),
                parse_mode="HTML"
            )
            await context.bot.send_message(
                chat_id=user_id,
                text=get_translation(user_id, "write_cover_letter_prompt"),
                reply_markup=ReplyKeyboardRemove(),
                parse_mode="HTML"
            )
            return WRITE_COVER_LETTER

        # Otherwise, redirect to the main menu
        if registration_type == "job_seeker":
            await main_menu(update, context)
            return MAIN_MENU
        elif registration_type == "employer":
            await employer_main_menu(update, context)
            return EMPLOYER_MAIN_MENU

    except Exception as e:
        logging.error(f"Error in start function: {e}")
        await context.bot.send_message(
            chat_id=user_id,
            text="An unexpected error occurred. Please try again.",
            parse_mode="HTML"
        )
        return ConversationHandler.END


def escape_html(text):
    """Escape special characters for Telegram HTML formatting."""
    escape_chars = {'&': '&amp;', '<': '<', '>': '>'}
    return ''.join(escape_chars.get(char, char) for char in text)

async def show_language_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)
    
    # Enhanced testing stage notification
    testing_notice = """
🚧 *Beta Testing Notification* 🚧

Thank you for helping us improve! Please be advised:

🔹 *Current Status*: 
This bot is in active development - core functions are operational but some features remain incomplete.

🔹 *What to Expect*:
• Non-functional buttons/options (marked as "This feature is not yet completed")
• Placeholder content in job posts and profiles
• Occasional error messages
• UI elements under refinement

🔹 *When Stuck*:
If the bot stops responding, type /start to reset your session.

🔹 *Reporting Issues*:
Your feedback is crucial! Please report any:
- Frozen screens
- Missing functionality 
- Unclear instructions
Via these channels:
📝 'Rate/Review' in main menu
🛟 'Help/Support' section
📩 Direct message to admin team

We're working around the clock to resolve these issues. Your patience and testing contributions are greatly appreciated!
"""
    
    await update.message.reply_text(testing_notice, parse_mode="Markdown")
    
    # Language selection keyboard
    keyboard = [
        [InlineKeyboardButton("English", callback_data="english")],
        [InlineKeyboardButton("አማርኛ", callback_data="amharic")],
        [InlineKeyboardButton("Afaan Oromoo", callback_data="oromia")],
        [InlineKeyboardButton("ትግርኛ", callback_data="tigrigna")],
        [InlineKeyboardButton("Qafar af", callback_data="afar")],
        [InlineKeyboardButton("Soomaali", callback_data="somalia")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        get_translation(user_id, "select_language"),
        reply_markup=reply_markup
    )
    return SELECT_LANGUAGE

async def handle_language_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = get_user_id(update)
    selected_language = query.data

    # Update the user's language in the database
    db.update_user_language(user_id, selected_language)

    # Notify the user about the language change
    await context.bot.send_message(
        chat_id=user_id,
        text=get_translation(user_id, "language_updated_message")
    )

    # Return to the main menu
    return await main_menu(update, context)

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    language = query.data
    user_id = get_user_id(update)  # Use get_user_id for consistency
    # Default to English if invalid choice
    language = language if language in ["amharic", "oromia", "english", "tigrigna", "somalia", "afar"] else "english"
    # Save language to database
    db.insert_user(user_id, language)
    # Fetch translation for the next prompt
    text = get_translation(user_id, "share_mobile")
    # Set the keyboard for contact sharing
    keyboard = [[KeyboardButton(get_translation(user_id, "share_contact_button"), request_contact=True)]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    # Update the original message with the new prompt and keyboard

    await query.message.reply_text(text, reply_markup=reply_markup)
    return MOBILE

async def save_mobile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.contact:
        contact = update.message.contact
        user_id = get_user_id(update)  # Use get_user_id for consistency
        phone_number = contact.phone_number
        # Save mobile number to database
        db.update_user_profile(user_id, contact_number=phone_number)
        # Fetch translation for registration prompt
        text = get_translation(user_id, "register_prompt")
        job_seeker = get_translation(user_id, "job_seeker")
        employer = get_translation(user_id, "employer")
        # Provide the registration options (job seeker or employer)
        keyboard = [
            [InlineKeyboardButton(job_seeker, callback_data="job_seeker")],
            [InlineKeyboardButton(employer, callback_data="employer")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        # Send registration prompt with options
        await update.message.reply_text(text, reply_markup=reply_markup)
        return REGISTRATION_TYPE
    else:
        # If the contact info is not shared, prompt the user again using the translated message
        keyboard = [
            [KeyboardButton(get_translation(get_user_id(update), "share_contact_button"), request_contact=True)]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        # Ask the user to share their mobile number using the translated message
        await update.message.reply_text(
            get_translation(get_user_id(update), "share_mobile"),
            reply_markup=reply_markup
        )
        return MOBILE

async def registration_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = get_user_id(update)  # Use get_user_id for consistency
    choice = query.data

    if choice == "job_seeker":
        # Save the registration type in the database
        db.update_user_profile(user_id, registration_type="job_seeker")
        # Record user creation in metadata table
        db.record_user_creation(user_id, 'job_seeker')
        context.user_data["registration"] = "job_seeker"
        await query.edit_message_text(get_translation(user_id, "job_seeker_start"))
        await update_job_seeker_flow(user_id, context)
        return JOB_SEEKER
    elif choice == "employer":
        # Save the registration type in the database
        db.update_user_profile(user_id, registration_type="employer")
        # Record user creation in metadata table
        db.record_user_creation(user_id, 'employer')
        context.user_data["registration"] = "employer"
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "employer_registration_start")
        )
        return EMPLOYER_NAME  # Transition to the first employer state
    else:
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "invalid_choice")
        )
        return REGISTRATION_TYPE

# Helper function to fetch the user's registration type from the database
def get_user_registration_type(user_id):
    try:
        user_profile = db.get_user_profile(user_id)
        if user_profile:
            return user_profile[12]  # Assuming registration_type is the 13th column in the user profile
        return None
    except Exception as e:
        print(f"Error fetching registration type: {e}")
        return None

async def update_job_seeker_flow(user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Initiate Job Seeker registration workflow."""
    await context.bot.send_message(
        chat_id=user_id, text=get_translation(user_id, "job_seeker_full_name_prompt")
    )

import re

async def job_seeker_full_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    full_name = update.message.text.strip()
    user_id = update.message.from_user.id

    # Check if the name has at least two words (name and father's name)
    if not full_name or len(full_name) < 3 or len(full_name.split()) < 2:
        await update.message.reply_text(get_translation(user_id, "invalid_full_name"))
        return JOB_SEEKER

    db.update_user_profile(user_id, full_name=full_name)
    await update.message.reply_text(get_translation(user_id, "job_seeker_dob_prompt"))
    return JOB_SEEKER_DOB



import re

async def job_seeker_dob(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    dob = update.message.text.strip()
    user_id = update.message.from_user.id

    if not re.match(r"^\d{4}[-/.]\d{1,2}[-/.]\d{1,2}$", dob):
        await update.message.reply_text(get_translation(user_id, "invalid_dob_format"))
        return JOB_SEEKER_DOB

    try:
        from datetime import datetime
        dob_normalized = dob.replace("/", "-").replace(".", "-")
        datetime.strptime(dob_normalized, "%Y-%m-%d")
    except ValueError:
        await update.message.reply_text(get_translation(user_id, "invalid_dob_format"))
        return JOB_SEEKER_DOB

    db.update_user_profile(user_id, dob=dob_normalized)

    # Ask gender
    keyboard = [
        [InlineKeyboardButton(get_translation(user_id, "male"), callback_data="male")],
        [InlineKeyboardButton(get_translation(user_id, "female"), callback_data="female")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        get_translation(user_id, "job_seeker_gender_prompt"), reply_markup=reply_markup
    )
    return JOB_SEEKER_GENDER

async def job_seeker_gender(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    gender = query.data

    # Save the gender in the database
    db.update_user_profile(user_id, gender=gender)
    # print(f"Gender updated for user {user_id}: {gender}")  # Logging

    # Prompt for contact numbers
    await query.edit_message_text(get_translation(user_id, "job_seeker_contact_numbers_prompt"))
    return JOB_SEEKER_CONTACT_NUMBERS

# async def job_seeker_contact_numbers_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     user_id = get_user_id(update)
#     await update.message.reply_text(get_translation(user_id, "job_seeker_contact_numbers_prompt"))
#     return JOB_SEEKER_CONTACT_NUMBERS

import re

async def job_seeker_contact_numbers(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)
    contact_numbers = update.message.text.strip()

    try:
        # Validate the input format
        numbers_list = [num.strip() for num in contact_numbers.split(",")]
        if len(numbers_list) > 3:
            await update.message.reply_text(get_translation(user_id, "contact_numbers_limit_exceeded"))
            return JOB_SEEKER_CONTACT_NUMBERS

        # Validate each number using a regex pattern (e.g., international phone number format)
        phone_pattern = re.compile(r"^\+?[0-9]{10,15}$")  # Adjust the regex as needed
        for num in numbers_list:
            if not phone_pattern.match(num):
                await update.message.reply_text(get_translation(user_id, "contact_numbers_invalid_format"))
                return JOB_SEEKER_CONTACT_NUMBERS

        # Save the contact numbers in the database
        db.update_user_profile(user_id, contact_number=", ".join(numbers_list))
        # print(f"Contact numbers saved for user {user_id}: {numbers_list}")  # Logging

        # Move to the next step (e.g., asking for languages)
        await update.message.reply_text(get_translation(user_id, "job_seeker_languages_prompt"))
        return JOB_SEEKER_LANGUAGES

    except Exception as e:
        print(f"Error saving contact numbers: {e}")
        await update.message.reply_text(get_translation(user_id, "contact_numbers_invalid"))
        return JOB_SEEKER_CONTACT_NUMBERS



async def job_seeker_languages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    languages = update.message.text.strip()
    user_id = update.message.from_user.id

    if not languages or len(languages) < 3:
        await update.message.reply_text(get_translation(user_id, "invalid_languages"))
        return JOB_SEEKER_LANGUAGES

    db.update_user_profile(user_id, languages=languages)

    # Ask for qualifications
    keyboard = [
        [InlineKeyboardButton(get_translation(user_id, "certificate"), callback_data="certificate")],
        [InlineKeyboardButton(get_translation(user_id, "diploma"), callback_data="diploma")],
        [InlineKeyboardButton(get_translation(user_id, "degree"), callback_data="degree")],
        [InlineKeyboardButton(get_translation(user_id, "ma"), callback_data="ma")],
        [InlineKeyboardButton(get_translation(user_id, "phd"), callback_data="phd")],
        [InlineKeyboardButton(get_translation(user_id, "other"), callback_data="other")],
        [InlineKeyboardButton(get_translation(user_id, "skip"), callback_data="skip")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        get_translation(user_id, "job_seeker_qualification_prompt"), reply_markup=reply_markup
    )
    return JOB_SEEKER_QUALIFICATION
#before
async def job_seeker_qualification(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    qualification = query.data

    if qualification == "skip":
        # Skip qualification and notify the user
        await query.edit_message_text(text=get_translation(user_id, "job_seeker_qualification_skipped"))
    else:
        # Update the user's profile in the database
        db.update_user_profile(user_id, qualification=qualification)
        await query.edit_message_text(text=get_translation(user_id, "job_seeker_qualification_selected"))

    # Ask for field of study
    keyboard = [[InlineKeyboardButton(get_translation(user_id, "skip"), callback_data="skip")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(
        chat_id=user_id,
        text=get_translation(user_id, "job_seeker_field_of_study_prompt"),
        reply_markup=reply_markup,
    )
    return JOB_SEEKER_FIELD_OF_STUDY

async def job_seeker_field_of_study(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)

    if update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(text=get_translation(user_id, "job_seeker_field_of_study_skipped"))
        return await job_seeker_cgpa_prompt(update, context)

    # Handle Message (e.g., user sends text)
    field_of_study = update.message.text.strip()

    if not field_of_study or len(field_of_study) < 3:
        await update.message.reply_text(get_translation(user_id, "invalid_field_of_study"))
        return JOB_SEEKER_FIELD_OF_STUDY

    db.update_user_profile(user_id, field_of_study=field_of_study)
    return await job_seeker_cgpa_prompt(update, context)

async def job_seeker_cgpa_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)
    keyboard = [[InlineKeyboardButton(get_translation(user_id, "skip"), callback_data="skip")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(
        chat_id=user_id,
        text=get_translation(user_id, "job_seeker_cgpa_prompt"),
        reply_markup=reply_markup,
    )
    return JOB_SEEKER_CGPA

async def job_seeker_cgpa(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)

    if update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(text=get_translation(user_id, "job_seeker_cgpa_skipped"))
        return await job_seeker_skills_prompt(update, context)

    # Handle Message (e.g., user sends text)
    cgpa = update.message.text.strip()

    try:
        cgpa_value = float(cgpa)
        if not (0 <= cgpa_value <= 4):  # Adjust range as needed
            raise ValueError
    except ValueError:
        await update.message.reply_text(get_translation(user_id, "invalid_cgpa"))
        return JOB_SEEKER_CGPA

    db.update_user_profile(user_id, cgpa=cgpa)
    return await job_seeker_skills_prompt(update, context)

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

# Helper function to get user_id safely
def get_user_id(update: Update) -> int:
    if update.callback_query:
        return update.callback_query.from_user.id
    return update.message.from_user.id

# Job Seeker Skills Prompt
async def job_seeker_skills_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)
    keyboard = [[InlineKeyboardButton(get_translation(user_id, "skip"), callback_data="skip")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(
        chat_id=user_id,
        text=get_translation(user_id, "job_seeker_skills_prompt"),
        reply_markup=reply_markup,
    )
    return JOB_SEEKER_SKILLS

# Job Seeker Skills
async def job_seeker_skills(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)

    if update.callback_query and update.callback_query.data == "skip":
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            text=get_translation(user_id, "job_seeker_skills_skipped")
        )
        return await job_seeker_profile_summary_prompt(update, context)

    skills = update.message.text.strip()

    if not skills or len(skills) < 3:
        await update.message.reply_text(get_translation(user_id, "invalid_skills"))
        return JOB_SEEKER_SKILLS

    db.update_user_profile(user_id, skills_experience=skills)
    return await job_seeker_profile_summary_prompt(update, context)

# Job Seeker Profile Summary Prompt
async def job_seeker_profile_summary_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)
    keyboard = [[InlineKeyboardButton(get_translation(user_id, "skip"), callback_data="skip")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(
        chat_id=user_id,
        text=get_translation(user_id, "job_seeker_profile_summary_prompt"),
        reply_markup=reply_markup,
    )
    return JOB_SEEKER_PROFILE_SUMMARY

# Job Seeker Profile Summary
async def job_seeker_profile_summary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)
    if update.callback_query and update.callback_query.data == "skip":
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            text=get_translation(user_id, "job_seeker_profile_summary_skipped")
        )
        return await job_seeker_supporting_documents_prompt(update, context)

    profile_summary = update.message.text.strip()

    if not profile_summary or len(profile_summary) < 10:
        await update.message.reply_text(get_translation(user_id, "invalid_profile_summary"))
        return JOB_SEEKER_PROFILE_SUMMARY

    db.update_user_profile(user_id, profile_summary=profile_summary)
    return await job_seeker_supporting_documents_prompt(update, context)

# Job Seeker Supporting Documents Prompt
async def job_seeker_supporting_documents_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)
    keyboard = [[InlineKeyboardButton(get_translation(user_id, "skip"), callback_data="skip")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(
        chat_id=user_id,
        text=get_translation(user_id, "job_seeker_supporting_documents_prompt"),
        reply_markup=reply_markup,
    )
    return JOB_SEEKER_SUPPORTING_DOCUMENTS

# Job Seeker Supporting Documents
import os

async def job_seeker_supporting_documents(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)

    if update.callback_query and update.callback_query.data == "skip":
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            text=get_translation(user_id, "job_seeker_supporting_documents_skipped")
        )
        return await job_seeker_portfolio_link_prompt(update, context)

    if update.message and update.message.document:
        document = update.message.document
        try:
            # Get the unique identifier (job_seeker_file_id) for the uploaded document
            job_seeker_file_id = document.file_id

            # Save the job_seeker_file_id in the database
            db.save_user_document(user_id, job_seeker_file_id)

            # Notify the user that the document was uploaded successfully
            await update.message.reply_text(get_translation(user_id, "document_uploaded_successfully"))
            return await job_seeker_portfolio_link_prompt(update, context)
        except Exception as e:
            # Log the error for debugging purposes
            print(f"Error uploading document: {e}")
            await update.message.reply_text(get_translation(user_id, "document_upload_failed"))
            return JOB_SEEKER_SUPPORTING_DOCUMENTS

    # If no document or skip, re-prompt
    await update.message.reply_text(get_translation(user_id, "please_upload_a_document_or_skip"))
    return JOB_SEEKER_SUPPORTING_DOCUMENTS

async def get_file_from_telegram(job_seeker_file_id, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Use the job_seeker_file_id to get the file object
        file = await context.bot.get_file(job_seeker_file_id)
        # Download the file to a specific path or process it as needed
        file_path = await file.download_to_drive("downloaded_file.pdf")
        return file_path
    except Exception as e:
        print(f"Error retrieving file: {e}")
        return None

# Job Seeker Portfolio Link Prompt
async def job_seeker_portfolio_link_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)
    keyboard = [[InlineKeyboardButton(get_translation(user_id, "skip"), callback_data="skip")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(
        chat_id=user_id,
        text=get_translation(user_id, "job_seeker_portfolio_link_prompt"),
        reply_markup=reply_markup,
    )
    return JOB_SEEKER_PORTFOLIO_LINK

# Job Seeker Portfolio Link
import re

import re
from urllib.parse import urlparse

async def job_seeker_portfolio_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)

    if update.callback_query and update.callback_query.data == "skip":
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            text=get_translation(user_id, "job_seeker_portfolio_link_skipped")
        )
        await finalize_registration(user_id, context)
        return MAIN_MENU  # Transition to MAIN_MENU state

    portfolio_link = update.message.text.strip()

    # Ensure the link starts with http:// or https://
    if not portfolio_link.startswith(("http://", "https://")):
        portfolio_link = "https://" + portfolio_link  # Prepend https:// if missing

    # Validate the portfolio link with a more flexible check
    parsed_url = urlparse(portfolio_link)
    if not parsed_url.netloc:  # Ensures there's a valid domain
        await update.message.reply_text(get_translation(user_id, "invalid_portfolio_link"))
        return JOB_SEEKER_PORTFOLIO_LINK

    db.update_user_profile(user_id, portfolio_link=portfolio_link)
    await finalize_registration(user_id, context)
    return MAIN_MENU  # Transition to MAIN_MENU state


async def finalize_registration(user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Finalize the registration process by notifying the user and displaying their profile."""
    await context.bot.send_message(
        chat_id=user_id,
        text=get_translation(user_id, "job_seeker_registration_complete"),
    )
    # Fetch and display the user's profile
    await display_user_profile(user_id, context)

from telegram import KeyboardButton, ReplyKeyboardMarkup


from telegram import KeyboardButton, ReplyKeyboardMarkup

async def display_user_profile(user_id, context):
    try:
        # Retrieve the user's profile as a dictionary
        user_profile = db.get_user_profile(user_id)
        if not user_profile:
            await context.bot.send_message(
                chat_id=user_id,
                text=get_translation(user_id, "profile_not_found")
            )
            return

        # Extract fields dynamically, using "Not Provided" as a fallback
        full_name = user_profile.get("full_name") or get_translation(user_id, "not_provided")
        contact_number = user_profile.get("contact_number") or get_translation(user_id, "not_provided")
        dob = user_profile.get("dob") or get_translation(user_id, "not_provided")
        gender = user_profile.get("gender") or get_translation(user_id, "not_provided")
        languages = user_profile.get("languages") or get_translation(user_id, "not_provided")
        qualification = user_profile.get("qualification") or get_translation(user_id, "not_provided")
        field_of_study = user_profile.get("field_of_study") or get_translation(user_id, "not_provided")
        cgpa = user_profile.get("cgpa") or get_translation(user_id, "not_provided")
        skills_experience = user_profile.get("skills_experience") or get_translation(user_id, "not_provided")
        profile_summary = user_profile.get("profile_summary") or get_translation(user_id, "not_provided")
        cv_path = user_profile.get("cv_path")  # This is the file_id of the CV
        portfolio_link = user_profile.get("portfolio_link")

        # Define a separator for better readability
        separator = "────────────────────"

        # Format the profile message with enhanced visuals
        profile_message = (
            f"📌 *{get_translation(user_id, 'profile_header')}*\n"
            f"{separator}\n"
            f"👤 *{get_translation(user_id, 'full_name')}:* `{full_name}`\n"
            f"📞 *{get_translation(user_id, 'contact_number')}:* `{contact_number}`\n"
            f"🎂 *{get_translation(user_id, 'dob')}:* `{dob}`\n"
            f"🚻 *{get_translation(user_id, 'gender')}:* `{gender}`\n"
            f"🗣️ *{get_translation(user_id, 'languages')}:* `{languages}`\n"
            f"{separator}\n"
            f"🎓 *{get_translation(user_id, 'qualification')}:* `{qualification}`\n"
            f"📚 *{get_translation(user_id, 'field_of_study')}:* `{field_of_study}`\n"
            f"📊 *{get_translation(user_id, 'cgpa')}:* `{cgpa}`\n"
            f"{separator}\n"
            f"💼 *{get_translation(user_id, 'skills_experience')}:*\n `{skills_experience}`\n"
            f"{separator}\n"
            f"📝 *{get_translation(user_id, 'profile_summary')}:*\n"
            f"```{profile_summary}```\n"
            f"{separator}\n"
        )

        # Add portfolio link if available
        if portfolio_link:
            profile_message += (
                f"🌐 *{get_translation(user_id, 'portfolio_link')}:* "
                f"[{get_translation(user_id, 'view_portfolio')}]({portfolio_link})\n"
            )

        # Fallback message if all fields are "Not Provided"
        if all(value == get_translation(user_id, "not_provided") for value in [
            full_name, contact_number, dob, gender, languages,
            qualification, field_of_study, cgpa, skills_experience, profile_summary
        ]):
            profile_message = (
                f"📌 *{get_translation(user_id, 'profile_header')}*\n"
                f"{separator}\n"
                f"⚠️ {get_translation(user_id, 'no_profile_info_available')}\n"
                f"{separator}\n"
            )

        # Send the profile message
        await context.bot.send_message(
            chat_id=user_id,
            text=profile_message,
            parse_mode="Markdown",
            disable_web_page_preview=True
        )

        # Send the CV file if available
        if cv_path:
            try:
                # Send the CV file using the file_id
                await context.bot.send_document(
                    chat_id=user_id,
                    document=cv_path,
                    caption=get_translation(user_id, "your_cv_file")
                )
            except Exception as e:
                print(f"Error sending CV file: {e}")
                await context.bot.send_message(
                    chat_id=user_id,
                    text=get_translation(user_id, "error_sending_cv")
                )
        else:
            # Inform the user if no CV is available
            await context.bot.send_message(
                chat_id=user_id,
                text=get_translation(user_id, "no_cv_available")
            )

        # Show the "Go to Main Menu" button
        keyboard = [[KeyboardButton(get_translation(user_id, "proceed_to_main_menu"))]]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "what_next"),
            reply_markup=reply_markup
        )

    except Exception as e:
        print(f"Error displaying user profile: {e}")
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "error_retrieving_profile")
        )




# Job Seeker Main Menu
async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)

    # Get user data for personalization
    user_data = db.get_user_profile(user_id)
    first_name = user_data.get('full_name', '').split()[0] if user_data else ''

    # Check for pending applications
    pending_apps = db.get_pending_applications_count(user_id)
    approved_apps = db.get_approved_applications_count(user_id)

    # Check profile completion status
    profile_completion = calculate_profile_completion(user_data)
    keyboard = [
        [KeyboardButton(f"👤 {get_translation(user_id, 'profile_button')} ({profile_completion}%)")],
        [KeyboardButton(f"✉️ {get_translation(user_id, 'applications_button')} ({pending_apps}) ({approved_apps})")],
        [KeyboardButton(f"✍️ {get_translation(user_id, 'apply_vacancy_button')}"),
         KeyboardButton(f"🔍 {get_translation(user_id, 'search_vacancies_button')}")],
        [KeyboardButton(f"ℹ️ {get_translation(user_id, 'help_button')}"),
         KeyboardButton(f"⭐ {get_translation(user_id, 'rate_button')}"),
         KeyboardButton(f"📝 {get_translation(user_id, 'report_button')}")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await context.bot.send_message(
        chat_id=user_id,
        text=get_translation(user_id, "main_menu_prompt"),
        reply_markup=reply_markup
    )

    # Create personalized welcome message
    welcome_msg = (
        f"🌟 <b>{get_translation(user_id, 'welcome_back')}, {first_name or get_translation(user_id, 'valued_user')}!</b>\n\n"
        f"📊 <i>{get_translation(user_id, 'profile_completion')}:</i> {profile_completion}%\n"
        f"📨 <i>{get_translation(user_id, 'pending_applications')}:</i> {pending_apps}\n"
        f"📨 <i>{get_translation(user_id, 'approved_applications')}:</i> {approved_apps}\n\n"

    )

    # Add tip of the day (optional)
    tip_of_day = get_tip_of_the_day(user_id)
    if tip_of_day:
        welcome_msg += f"\n💡 <b>{get_translation(user_id, 'tip_of_day')}:</b> {tip_of_day}"

    await context.bot.send_message(
        chat_id=user_id,
        text=welcome_msg,
        parse_mode="HTML",
        reply_markup=reply_markup
    )


    return MAIN_MENU


def calculate_profile_completion(user_data: dict) -> int:
    """Calculate profile completion percentage counting skips as incomplete."""
    all_fields = [
        'full_name', 'contact_number', 'dob', 'gender', 'languages',
        'qualification', 'field_of_study', 'cgpa',
        'skills_experience', 'profile_summary', 'cv_path', 'portfolio_link'
    ]

    if not user_data:
        return 0

    filled = 0
    for field in all_fields:
        value = user_data.get(field)

        # Field counts as filled ONLY if:
        # 1. It has a value AND
        # 2. The value is not "skip" or empty
        if value and str(value).lower() != "skip":
            filled += 1

    return min(100, (filled * 100) // len(all_fields))

import random

def get_tip_of_the_day(user_id: int) -> str:
    """Get a random career tip for the user with translations."""
    tips = [
        get_translation(user_id, "customize_resume"),
        get_translation(user_id, "follow_up_applications"),
        get_translation(user_id, "highlight_achievements"),
        get_translation(user_id, "network_with_professionals"),
        get_translation(user_id, "keep_skills_updated"),
        get_translation(user_id, "prepare_for_interviews"),
        get_translation(user_id, "set_clear_goals"),
        get_translation(user_id, "stay_positive"),
        get_translation(user_id, "seek_mentorship"),
        get_translation(user_id, "use_linkedin_effectively")
    ]
    return random.choice(tips)


async def view_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)
    profile_data = db.get_user_profile(user_id)
    completion = calculate_profile_completion(profile_data)

    # Enhanced keyboard with visual indicators
    keyboard = [
        [KeyboardButton(f"👤 {get_translation(user_id, 'view_profile_button')} ({completion}%)")],  # First row
        [KeyboardButton(f"✏️ {get_translation(user_id, 'edit_profile_button')}"),  # Second row
         KeyboardButton(f"📊 {get_translation(user_id, 'profile_stats')}")],
        [KeyboardButton(f"🗑️ {get_translation(user_id, 'delete_account_button')}"),  # Third row
         KeyboardButton(f"🌐 {get_translation(user_id, 'change_language_button')}")],
        [KeyboardButton(f"🔙 {get_translation(user_id, 'back_to_main_menu')}")]  # Fourth row
    ]

    # Create the ReplyKeyboardMarkup
    reply_markup = ReplyKeyboardMarkup(
        keyboard,
        one_time_keyboard=True,  # The keyboard will disappear after one use
        resize_keyboard=True  # Adjust the keyboard size to fit the buttons
    )

    # Send the message with the new keyboard
    await context.bot.send_message(
        chat_id=user_id,
        text=get_translation(user_id, "profile_menu_prompt"),
        reply_markup=reply_markup
    )

    return PROFILE_MENU



async def handle_profile_actions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)
    choice = update.message.text  # Get the text sent by the user (button press)

    # Dynamically construct button texts with emojis
    view_profile_button_text = f"👤 {get_translation(user_id, 'view_profile_button')} ({calculate_profile_completion(db.get_user_profile(user_id))}%)"
    edit_profile_button_text = f"✏️ {get_translation(user_id, 'edit_profile_button')}"
    profile_stats_button_text = f"📊 {get_translation(user_id, 'profile_stats')}"
    delete_account_button_text = f"🗑️ {get_translation(user_id, 'delete_account_button')}"
    change_language_button_text = f"🌐 {get_translation(user_id, 'change_language_button')}"
    back_to_main_menu_button_text = f"🔙 {get_translation(user_id, 'back_to_main_menu')}"

    if choice == view_profile_button_text:
        # Fetch and display the user's profile
        await display_user_profile(user_id, context)
        return await view_profile(update, context)

    elif choice == edit_profile_button_text:
        # Redirect to the edit profile menu
        return await display_edit_menu(update, context)

    elif choice == profile_stats_button_text:
        # Analyze and display profile stats
        profile_data = db.get_user_profile(user_id)
        strength = analyze_profile_strength(profile_data)

        # Build the stats message
        stats_message = (
            f"📊 <b>{get_translation(user_id, 'profile_stats')}:</b>\n\n"
            f"💪 <i>{get_translation(user_id, 'profile_strength')}:</i> {strength}\n\n"
            f"📝 <i>{get_translation(user_id, 'skills_experience')}:</i> {'✅' if profile_data.get('skills_experience') else '❌'}\n"
            f"📄 <i>{get_translation(user_id, 'profile_summary')}:</i> {'✅' if profile_data.get('profile_summary') else '❌'}\n"
            f"🔗 <i>{get_translation(user_id, 'portfolio_link')}:</i> {'✅' if profile_data.get('portfolio_link') else '❌'}\n"
            f"📂 <i>{get_translation(user_id, 'cv_path')}:</i> {'✅' if profile_data.get('cv_path') else '❌'}\n"
        )

        # Send the stats message
        await context.bot.send_message(
            chat_id=user_id,
            text=stats_message,
            parse_mode="HTML"
        )
        return await view_profile(update, context)

    elif choice == delete_account_button_text:
        return await confirm_delete_account(update, context)

    elif choice == change_language_button_text:
        # Show language selection menu
        return await show_language_selection(update, context)

    elif choice == back_to_main_menu_button_text:
        # Return to the main menu
        return await main_menu(update, context)
    else:
        # Check if the current state is CONFIRM_DELETE_ACCOUNT
        current_state = context.user_data.get('current_state')
        if current_state == CONFIRM_DELETE_ACCOUNT:
            # Delegate invalid input handling to handle_delete_confirmation
            return await handle_delete_confirmation(update, context)

        # Handle invalid input for other states
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "invalid_choice")
        )
        return PROFILE_MENU

def analyze_profile_strength(profile_data: dict) -> str:
    strength = 0
    if profile_data.get('skills_experience'): strength += 25
    if profile_data.get('profile_summary'): strength += 20
    if profile_data.get('portfolio_link'): strength += 20
    if profile_data.get('cv_path'): strength += 35
    return f"{min(100, strength)}% Strong"


async def confirm_delete_account(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)

    # Store the expected responses in context for validation
    context.user_data['expected_responses'] = {
        'delete': get_translation(user_id, 'confirm_delete_yes'),
        'keep': get_translation(user_id, 'confirm_delete_no')
    }

    # Set the current state to CONFIRM_DELETE_ACCOUNT
    context.user_data['current_state'] = CONFIRM_DELETE_ACCOUNT

    keyboard = [
        [KeyboardButton(f"❌ {context.user_data['expected_responses']['delete']}")],
        [KeyboardButton(f"✅ {context.user_data['expected_responses']['keep']}")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

    await context.bot.send_message(
        chat_id=user_id,
        text=get_translation(user_id, "delete_confirmation"),
        reply_markup=reply_markup
    )
    return CONFIRM_DELETE_ACCOUNT


async def handle_delete_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)
    choice = update.message.text.strip()

    # Get expected responses from context
    expected = context.user_data.get('expected_responses', {})
    delete_text = f"❌ {expected.get('delete', 'Delete my account')}"
    keep_text = f"✅ {expected.get('keep', 'Keep my account')}"

    # Check both button text and raw text (case insensitive)
    if choice.lower() in [delete_text.lower(), expected.get('delete', '').lower(), 'delete', 'del']:
        db.delete_user_account(user_id)
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "account_deleted_message")
        )
        return ConversationHandler.END

    elif choice.lower() in [keep_text.lower(), expected.get('keep', '').lower(), 'keep', 'no']:
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "delete_account_cancelled")
        )
        return await view_profile(update, context)

    else:
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "invalid_delete_choice")  # Correct invalid choice message
        )
        return CONFIRM_DELETE_ACCOUNT  # Keep the user in the same state


async def delete_account_confirmed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = get_user_id(update)

    # Delete the user's account from the database
    db.delete_user_account(user_id)

    # Notify the user and end the conversation
    await context.bot.send_message(
        chat_id=user_id,
        text=get_translation(user_id, "account_deleted_message")
    )
    return ConversationHandler.END  # End the conversation

async def cancel_delete_account(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = get_user_id(update)

    # Notify the user that the deletion was cancelled
    await query.edit_message_text(
        text=get_translation(user_id, "delete_account_cancelled")
    )
    return await view_profile(update, context)  # Return to the profile menu

async def confirm_change_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = get_user_id(update)

    # Show confirmation buttons
    keyboard = [
        [InlineKeyboardButton(get_translation(user_id, "yes_button"), callback_data="change_language_confirmed")],
        [InlineKeyboardButton(get_translation(user_id, "no_button"), callback_data="cancel_change_language")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text=get_translation(user_id, "confirm_change_language_prompt"),
        reply_markup=reply_markup
    )
    return CONFIRM_CHANGE_LANGUAGE

async def change_language_confirmed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = get_user_id(update)

    # Update the user's language preference
    selected_language = context.user_data.get("selected_language", "english")
    db.update_user_language(user_id, selected_language)

    # Notify the user about the language change
    await context.bot.send_message(
        chat_id=user_id,
        text=get_translation(user_id, "language_updated_message")
    )
    return await main_menu(update, context)

async def cancel_change_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = get_user_id(update)

    # Notify the user that the language change was cancelled
    await query.edit_message_text(
        text=get_translation(user_id, "change_language_cancelled")
    )
    return await view_profile(update, context)  # Return to the profile menu

async def edit_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)
    valid_fields = [
        "full_name", "contact_number", "dob", "gender", "languages",
        "qualification", "field_of_study", "cgpa", "skills_experience",
        "profile_summary", "cv_path", "portfolio_link"
    ]

    # Create an inline keyboard for editing profile fields
    keyboard = [
        [InlineKeyboardButton(get_translation(user_id, f"edit_{field}"), callback_data=f"edit_{field}")]
        for field in valid_fields
    ] + [
        [InlineKeyboardButton(get_translation(user_id, "back_to_main_menu"), callback_data="back_to_main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(
        chat_id=user_id,
        text=get_translation(user_id, "edit_profile_prompt"),
        reply_markup=reply_markup
    )
    return EDIT_PROFILE

async def handle_edit_profile_field(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    field_to_edit = query.data

    if field_to_edit == "back_to_main_menu":
        await query.edit_message_text(text=get_translation(user_id, "returning_to_main_menu"))
        return await main_menu(update, context)

    # Define valid callback data explicitly
    valid_fields = [
        "full_name", "contact_number", "dob", "gender", "languages",
        "qualification", "field_of_study", "cgpa", "skills_experience",
        "profile_summary", "cv_path", "portfolio_link"
    ]
    valid_callback_data = {f"edit_{field}" for field in valid_fields}

    # Validate the field to edit
    if field_to_edit not in valid_callback_data:
        await query.edit_message_text(text=get_translation(user_id, "invalid_field_selected"))
        return EDIT_PROFILE

    # Store the field to edit in context.user_data
    context.user_data["field_to_edit"] = field_to_edit.replace("edit_", "")
    await context.bot.send_message(
        chat_id=user_id,
        text=get_translation(user_id, "enter_new_value_prompt").format(field=context.user_data["field_to_edit"].replace("_", " "))
    )
    return EDIT_PROFILE

# Save Edited Field
async def save_edited_field(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)
    new_value = update.message.text.strip()
    field_to_edit = context.user_data.get("field_to_edit")

    if not field_to_edit:
        await update.message.reply_text(get_translation(user_id, "field_not_found"))
        return EDIT_PROFILE

    # Define valid fields
    valid_fields = [
        "full_name", "contact_number", "dob", "gender", "languages",
        "qualification", "field_of_study", "cgpa", "skills_experience",
        "profile_summary", "cv_path", "portfolio_link"
    ]

    # Validate the field to edit
    if field_to_edit not in valid_fields:
        await update.message.reply_text(get_translation(user_id, "invalid_field_selected"))
        return EDIT_PROFILE

    try:

        # Update the field in the database
        db.update_user_profile(user_id, **{field_to_edit: new_value})

        # Confirm the update to the user
        await update.message.reply_text(
            get_translation(user_id, "field_updated_successfully").format(field=field_to_edit.replace("_", " "))
        )
    except Exception as e:
        print(f"Error updating field {field_to_edit} for user {user_id}: {e}")
        await update.message.reply_text(get_translation(user_id, "error_updating_field"))

    # Return to the edit menu
    return await display_edit_menu(update, context)

async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)
    choice = update.message.text

    # Get user data for personalization
    user_data = db.get_user_profile(user_id)

    # Check for pending applications
    pending_apps = db.get_pending_applications_count(user_id)
    approved_apps = db.get_approved_applications_count(user_id)

    # Check profile completion status
    profile_completion = calculate_profile_completion(user_data)

    # Define button texts dynamically
    profile_button_text = f"👤 {get_translation(user_id, 'profile_button')} ({profile_completion}%)"
    applications_button_text = f"✉️ {get_translation(user_id, 'applications_button')} ({pending_apps}) ({approved_apps})"
    apply_vacancy_button_text = f"✍️ {get_translation(user_id, 'apply_vacancy_button')}"
    search_vacancies_button_text = f"🔍 {get_translation(user_id, 'search_vacancies_button')}"
    help_button_text = f"ℹ️ {get_translation(user_id, 'help_button')}"
    rate_button_text = f"⭐ {get_translation(user_id, 'rate_button')}"
    report_button_text = f"📝 {get_translation(user_id, 'report_button')}"

    # Ensure text matching is correct
    proceed_button_text = get_translation(user_id, "proceed_to_main_menu")

    if choice == proceed_button_text:  # Handling "Go to Main Menu" button
        return await main_menu(update, context)

    if choice == profile_button_text:
        return await view_profile(update, context)
    elif choice == applications_button_text:
        return await view_my_applications(update, context)
    elif choice == apply_vacancy_button_text:
        return await display_vacancies(update, context)
    elif choice == search_vacancies_button_text:
        return await start_job_search(update, context)
    elif choice == help_button_text:
        return await show_help(update, context)
    elif choice == rate_button_text:
        return await show_rate_options(update, context)
    elif choice == report_button_text:
        user_id = get_user_id(update)
        await context.bot.send_message(
            chat_id=user_id,
            text="🚧 This feature is not yet completed. Please check back later!"
        )
        # return await show_report_options(update, context)

    else:
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "invalid_choice")
        )
        return MAIN_MENU


async def handle_proceed_to_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)
    # Call the main_menu function directly to show the main menu options
    return await main_menu(update, context)
import os


async def view_my_applications(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)
    applications = db.get_user_applications(user_id)

    if not applications:
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "no_applications_found"),
            parse_mode="HTML"
        )
        return await view_profile(update, context)

    # Group by status
    status_groups = {}
    for app in applications:
        status_groups.setdefault(app['status'], []).append(app)

    # Create message with tabs
    message = f"📬 <b>{get_translation(user_id, 'your_applications')}</b>\n\n"
    keyboard = []
    for status, apps in status_groups.items():
        message += f"📌 <b>{status.capitalize()}</b> ({len(apps)})\n"
        for app in apps[:3]:  # Show max 3 per status
            message += (
                f"├─ 🏢 {app['company_name']}\n"
                f"├─ 💼 {app['job_title']}\n"
                f"├─ 📅 Applied: {app['application_date'].split()[0]}\n"
                f"└─ 🔍 View Details\n\n"
            )
            # Add InlineKeyboardButton for each application
            keyboard.append([InlineKeyboardButton(
                f"View Details: {app['job_title']}",
                callback_data=f"app_{app['application_id']}"
            )])

    # Add navigation buttons
    keyboard.append([InlineKeyboardButton("🔄 Refresh", callback_data="refresh_applications")])
    keyboard.append([InlineKeyboardButton("📥 Export All", callback_data="export_applications")])
    keyboard.append([InlineKeyboardButton("🔙 Back to Profile", callback_data="back_to_profile")])

    await context.bot.send_message(
        chat_id=user_id,
        text=message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
        disable_web_page_preview=True
    )
    return VIEWING_APPLICATIONS


async def show_application_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)
    query = update.callback_query
    await query.answer()

    app_id = int(query.data.split('_')[1])
    application = db.get_application_details(app_id)

    # Status emoji mapping
    status_emoji = {
        'pending': '🕒',
        'reviewed': '🔍',
        'approved': '✅',
        'rejected': '❌'
    }

    message = (
        f"{status_emoji.get(application['status'], '📄')} <b>Application Details</b>\n\n"
        f"🏢 <b>Company:</b> {application['company_name']}\n"
        f"💼 <b>Position:</b> {application['job_title']}\n"
        f"📅 <b>Applied:</b> {application['application_date']}\n"
        f"📌 <b>Status:</b> {application['status'].capitalize()}\n\n"
        f"📝 <b>Cover Letter:</b>\n{application['cover_letter'][:300]}...\n\n"
        f"📋 <b>Job Description:</b>\n{application['description'][:200]}..."
    )

    keyboard = [
        [InlineKeyboardButton("📤 Withdraw Application", callback_data=f"withdraw_{app_id}")],
        [InlineKeyboardButton("🔙 Back to List", callback_data="back_to_applications")]
    ]

    await query.edit_message_text(
        text=message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )
    return APPLICATION_DETAILS


async def handle_application_actions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = get_user_id(update)
    action = query.data

    if action == "refresh_applications":
        return await view_my_applications(update, context)

    elif action == "export_applications":
        try:
            # Generate the Excel file and get the filename
            filename = await export_applications_csv(user_id)

            # Send the file with a custom caption
            await context.bot.send_document(
                chat_id=user_id,
                document=open(filename, 'rb'),
                caption=get_translation(user_id, "applications_exported"),
                filename=f"Job_Applications_Report_{datetime.now().strftime('%Y%m%d')}.xlsx"
            )

            # Clean up the file after sending
            os.remove(filename)

        except Exception as e:
            logging.error(f"Export failed: {e}")
            await query.edit_message_text(
                text=get_translation(user_id, "export_failed_error"),
                parse_mode="HTML"
            )
        return VIEWING_APPLICATIONS

    elif action.startswith("app_"):
        return await show_application_details(update, context)

    elif action.startswith("withdraw_"):
        app_id = int(action.split('_')[1])
        db.update_application_status(app_id, "withdrawn")
        await query.edit_message_text(
            text=get_translation(user_id, "application_withdrawn"),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to List", callback_data="back_to_applications")]
            ])
        )
        return VIEWING_APPLICATIONS

    elif action == "back_to_applications":
        return await view_my_applications(update, context)

    elif action == "back_to_profile":
        return await view_profile(update, context)


import csv
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
from datetime import datetime, timedelta


async def export_applications_csv(user_id: int):
    """Generate professional Excel report with formatting"""
    applications = db.get_user_applications(user_id)
    filename = f"job_applications_{user_id}_{datetime.now().strftime('%Y%m%d')}.xlsx"

    # Create workbook and worksheet
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Job Applications"

    # Define styles
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="4F81BD", end_color="4F81BD", fill_type="solid")
    status_colors = {
        'pending': 'FFF2CC',
        'approved': 'C6EFCE',
        'rejected': 'FFC7CE',
        'withdrawn': 'D9D9D9'
    }
    thin_border = Border(left=Side(style='thin'),
                         right=Side(style='thin'),
                         top=Side(style='thin'),
                         bottom=Side(style='thin'))

    # Headers
    headers = [
        "Application ID", "Company", "Job Title",
        "Position Type", "Applied Date", "Status",
        "Cover Letter Excerpt", "Job Description Excerpt"
    ]
    ws.append(headers)

    # Apply header styles
    for col in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center')
        cell.border = thin_border

    # Add data rows
    for app in applications:
        ws.append([
            app['application_id'],
            app['company_name'],
            app['job_title'],
            app['employment_type'],
            app['application_date'].split()[0],  # Just the date part
            app['status'].capitalize(),
            app['cover_letter'][:100] + "..." if app['cover_letter'] else "",
            app['description'][:100] + "..." if app.get('description') else ""
        ])

        # Apply row styling
        row = ws.max_row
        for col in range(1, len(headers) + 1):
            cell = ws.cell(row=row, column=col)
            cell.border = thin_border

            # Status-based coloring
            if col == 6:  # Status column
                cell.fill = PatternFill(
                    start_color=status_colors.get(app['status'], 'FFFFFF'),
                    end_color=status_colors.get(app['status'], 'FFFFFF'),
                    fill_type="solid"
                )

    # Add auto-filter
    ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{len(applications) + 1}"

    # Adjust column widths
    column_widths = [12, 20, 25, 15, 12, 12, 40, 40]
    for i, width in enumerate(column_widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = width

    # Add freeze panes and conditional formatting
    ws.freeze_panes = "A2"

    # Add summary sheet
    summary_sheet = wb.create_sheet("Summary")
    summary_sheet.append(["Application Status", "Count"])

    status_counts = {}
    for app in applications:
        status_counts[app['status']] = status_counts.get(app['status'], 0) + 1

    for status, count in status_counts.items():
        summary_sheet.append([status.capitalize(), count])

    # Add chart to summary sheet
    from openpyxl.chart import PieChart, Reference
    chart = PieChart()
    labels = Reference(summary_sheet, min_col=1, min_row=2, max_row=len(status_counts) + 1)
    data = Reference(summary_sheet, min_col=2, min_row=1, max_row=len(status_counts) + 1)
    chart.add_data(data, titles_from_data=True)
    chart.set_categories(labels)
    chart.title = "Application Status Distribution"
    summary_sheet.add_chart(chart, "D2")

    # Save the file
    wb.save(filename)
    return filename

async def handle_export_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = get_user_id(update)
    query = update.callback_query
    await query.answer()

    try:
        # Generate the Excel file and get the filename
        filename = await export_applications_csv(user_id)

        # Send the file with a custom caption
        await context.bot.send_document(
            chat_id=user_id,
            document=open(filename, 'rb'),
            caption=(
                f"📊 <b>Your Job Applications Report</b>\n\n"
                f"📅 Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
                f"📝 Contains: {db.get_pending_applications_count(user_id)} active applications\n"
                f"💼 Export includes:\n"
                f"- Application details\n"
                f"- Status overview\n"
                f"- Interactive filters\n\n"
                f"🔍 Open in Excel for full features"
            ),
            parse_mode="HTML",
            filename=f"Job_Applications_Report_{datetime.now().strftime('%Y%m%d')}.xlsx"
        )

        # Clean up the file after sending
        os.remove(filename)

    except Exception as e:
        logging.error(f"Export failed: {e}")
        await query.edit_message_text(
            text=get_translation(user_id, "export_failed_error"),
            parse_mode="HTML"
        )



# Ensure the employer_documents directory exists
if not os.path.exists("employer_documents"):
    os.makedirs("employer_documents")

async def employer_name_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)
    await update.callback_query.answer()

    await context.bot.send_message(
        chat_id=user_id,
        text=get_translation(user_id, "employer_name_prompt")
    )
    return EMPLOYER_NAME


async def save_employer_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)
    company_name = update.message.text.strip()

    if not company_name or len(company_name) < 3:
        await update.message.reply_text(get_translation(user_id, "invalid_company_name"))
        return EMPLOYER_NAME

    # Save company name to context.user_data
    context.user_data["company_name"] = company_name

    # Save employer profile to the database (after checking user_id)
    db.cursor.execute("""
        INSERT INTO employers (employer_id, company_name) 
        VALUES (?, ?)
    """, (user_id, company_name))
    db.connection.commit()

    await context.bot.send_message(
        chat_id=user_id,
        text=get_translation(user_id, "employer_location_prompt")
    )
    return EMPLOYER_LOCATION


async def save_employer_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)
    location = update.message.text.strip()

    if not location or len(location) < 3:
        await update.message.reply_text(get_translation(user_id, "invalid_location"))
        return EMPLOYER_LOCATION

    # Save location to context.user_data
    context.user_data["location"] = location

    # Update employer profile in the database
    db.cursor.execute("""
        UPDATE employers
        SET city = ?
        WHERE employer_id = ?
    """, (location, user_id))
    db.connection.commit()

    # Create an inline keyboard for employer type
    keyboard = [
        [InlineKeyboardButton("Company", callback_data="company")],
        [InlineKeyboardButton("Private Client", callback_data="private_client")],
        [InlineKeyboardButton("Individual", callback_data="individual")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(
        chat_id=user_id,
        text=get_translation(user_id, "employer_type_prompt"),
        reply_markup=reply_markup
    )
    return EMPLOYER_TYPE


async def save_employer_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    employer_type = query.data

    # Validate the employer type
    valid_types = ["company", "private_client", "individual"]
    if employer_type not in valid_types:
        await query.edit_message_text(text=get_translation(user_id, "invalid_employer_type"))
        return EMPLOYER_TYPE

    # Save employer type to context.user_data
    context.user_data["employer_type"] = employer_type

    # Ask about the company (skipable)
    keyboard = [[InlineKeyboardButton(get_translation(user_id, "skip"), callback_data="skip")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(
        chat_id=user_id,
        text=get_translation(user_id, "about_company_prompt"),
        reply_markup=reply_markup
    )
    return ABOUT_COMPANY

async def save_about_company(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)

    if update.callback_query and update.callback_query.data == "skip":
        await update.callback_query.answer()
        context.user_data["about_company"] = None
        await update.callback_query.edit_message_text(text=get_translation(user_id, "about_company_skipped"))
    else:
        about_company = update.message.text.strip()
        if not about_company or len(about_company) < 10:
            await update.message.reply_text(get_translation(user_id, "invalid_about_company"))
            return ABOUT_COMPANY
        context.user_data["about_company"] = about_company

    # Prompt for verification documents with a Skip option
    keyboard = [
        [InlineKeyboardButton(get_translation(user_id, "skip"), callback_data="skip")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(
        chat_id=user_id,
        text=get_translation(user_id, "verification_documents_prompt"),
        reply_markup=reply_markup
    )
    return VERIFICATION_DOCUMENTS

async def upload_verification_documents(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)

    # Handle skipping verification documents
    if update.callback_query and update.callback_query.data == "skip":
        await update.callback_query.answer()
        context.user_data["verification_docs"] = None
        await update.callback_query.edit_message_text(text=get_translation(user_id, "verification_documents_skipped"))
        return await finalize_employer_registration(update, context)

    # Handle document upload
    elif update.message and update.message.document:
        document = update.message.document
        try:
            # Get the unique identifier (employer_file_id) for the uploaded document
            employer_file_id = document.file_id

            # Save the employer_file_id in context.user_data
            context.user_data["verification_docs"] = employer_file_id

            # Notify the user that the document was uploaded successfully
            await update.message.reply_text(get_translation(user_id, "document_uploaded_successfully"))

            # Proceed to finalize registration
            return await finalize_employer_registration(update, context)
        except Exception as e:
            # Log the error for debugging purposes
            print(f"Error uploading verification document: {e}")
            await update.message.reply_text(get_translation(user_id, "document_upload_failed"))
            return VERIFICATION_DOCUMENTS

    # If no document or skip action taken, prompt the user again
    else:
        # Display the Skip button explicitly
        keyboard = [
            [InlineKeyboardButton(get_translation(user_id, "skip"), callback_data="skip")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "verification_documents_prompt"),
            reply_markup=reply_markup
        )
        return VERIFICATION_DOCUMENTS

async def get_employer_file_from_telegram(employer_file_id, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Use the employer_file_id to get the file object
        file = await context.bot.get_file(employer_file_id)
        # Download the file to a specific path or process it as needed
        file_path = await file.download_to_drive("downloaded_employer_file.pdf")
        return file_path
    except Exception as e:
        print(f"Error retrieving employer file: {e}")
        return None

async def finalize_employer_registration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)

    # Extract data from context.user_data
    company_name = context.user_data.get("company_name")
    location = context.user_data.get("location")
    employer_type = context.user_data.get("employer_type")
    about_company = context.user_data.get("about_company")
    employer_file_id = context.user_data.get("verification_docs")  # Use employer_file_id instead of local path

    try:
        # Save the employer profile to the database
        employer_id = db.save_employer_profile(
            user_id=user_id,
            company_name=company_name,
            location=location,
            employer_type=employer_type,
            about_company=about_company,
            verification_docs=employer_file_id
        )

        # Store the employer_id in context.user_data for future use
        context.user_data["employer_id"] = employer_id

        # Notify the user that registration is complete
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "employer_registration_complete")
        )

        # Provide the "Proceed to Employer Main Menu" button
        keyboard = [[KeyboardButton(get_translation(user_id, "proceed_to_employer_main_menu"))]]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "proceed_to_employer_main_menu"),
            reply_markup=reply_markup
        )

        return EMPLOYER_MAIN_MENU

    except Exception as e:

        print(f"Error finalizing employer registration: {e}")
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "registration_failed")  # Inform the user of the failure
        )
        return ConversationHandler.END
# async def save_employer_documents(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     user_id = get_user_id(update)
#
#     if update.callback_query and update.callback_query.data == "skip":
#         await update.callback_query.answer()
#         await update.callback_query.edit_message_text(
#             text=get_translation(user_id, "employer_documents_skipped")
#         )
#     else:
#         document = update.message.document
#
#         # Ensure the employer_documents directory exists
#         if not os.path.exists("employer_documents"):
#             os.makedirs("employer_documents")
#
#         # Save the document to the server
#         file = await document.get_file()
#         file_path = f"employer_documents/{user_id}_{document.file_name}"
#         await file.download_to_drive(file_path)
#
#         # Save document path to context.user_data
#         context.user_data["verification_docs"] = file_path
#
#     try:
#         # Save or update employer data in the database
#         db.save_employer_profile(
#             user_id=user_id,
#             company_name=context.user_data.get("company_name"),
#             location=context.user_data.get("location"),
#             employer_type=context.user_data.get("employer_type"),
#             about_company=context.user_data.get("about_company", ""),
#             verification_docs=context.user_data.get("verification_docs", "")
#         )
#
#         await context.bot.send_message(
#             chat_id=user_id,
#             text=get_translation(user_id, "employer_registration_complete")
#         )
#
#         # Display the employer profile
#         await display_employer_profile(user_id, context)
#     except ValueError as e:
#         await context.bot.send_message(
#             chat_id=user_id,
#             text=get_translation(user_id, "contact_number_not_found")
#         )
#         return REGISTRATION_TYPE  # Return to the registration type selection
#
#     return EMPLOYER_MAIN_MENU  # Transition to the employer main menu

import logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)


def escape_markdown(text):
    if text is None:
        return ""
    text = str(text)
    # Fixed regex pattern (handles =, -, and other reserved chars)
    markdown_reserved_chars = r"([_*[\]()~`>#+=|!.\\-])"
    return re.sub(markdown_reserved_chars, r"\\\1", text)


async def display_employer_profile(user_id, context):
    try:
        # First try to get employer profile directly by user_id
        employer_profile = db.get_employer_profile_by_user_id(user_id)
        if not employer_profile:
            logging.error(f"No employer profile found for user_id={user_id}")
            await context.bot.send_message(
                chat_id=user_id,
                text=get_translation(user_id, "employer_not_found_error")
            )
            return

        employer_id = employer_profile.get("employer_id")
        context.user_data["employer_id"] = employer_id

        logging.debug(f"Retrieved employer_id={employer_id} for user_id={user_id}")
        # Get employer profile from database
        employer_profile = db.get_employer_profile(employer_id)
        if not employer_profile:
            logging.error(f"No employer profile found in DB for employer_id={employer_id}")
            await context.bot.send_message(
                chat_id=user_id,
                text=get_translation(user_id, "employer_profile_not_found")
            )
            return

        logging.debug(f"Retrieved employer_profile={employer_profile} for employer_id={employer_id}")

        # Extract fields with fallbacks and escape Markdown special characters
        company_name = escape_markdown(employer_profile.get("company_name")) or get_translation(user_id, "not_provided")
        city = escape_markdown(employer_profile.get("city")) or get_translation(user_id, "not_provided")
        contact_number = escape_markdown(employer_profile.get("contact_number")) or get_translation(user_id, "not_provided")
        employer_type = escape_markdown(employer_profile.get("employer_type")) or get_translation(user_id, "not_provided")
        about_company = escape_markdown(employer_profile.get("about_company")) or get_translation(user_id, "not_provided")
        verification_docs = employer_profile.get("verification_docs")  # File ID

        separator = "────────────────────"

        # Format profile message with professional style
        profile_message = (
            f" *{escape_markdown(get_translation(user_id, 'employer_profile_header'))}*\n"
            f"{separator}\n"
            f"📛 *{escape_markdown(get_translation(user_id, 'company_name'))}:* `{company_name}`\n"
            f"📍 *{escape_markdown(get_translation(user_id, 'location'))}:* `{city}`\n"
            f"📞 *{escape_markdown(get_translation(user_id, 'contact_number'))}:* `{contact_number}`\n"
            f"💼 *{escape_markdown(get_translation(user_id, 'employer_type'))}:* `{employer_type}`\n"
            f"{separator}\n"
            f"📝 *{escape_markdown(get_translation(user_id, 'about_company'))}:*\n"
            f"```{about_company}```\n"
            f"{separator}\n"
        )

        # Add verification document status
        if verification_docs:
            profile_message += (
                f"📄 *{escape_markdown(get_translation(user_id, 'verification_documents'))}:* "
                f"{escape_markdown(get_translation(user_id, 'document_available'))}\n"
            )
        else:
            profile_message += (
                f"⚠️ *{escape_markdown(get_translation(user_id, 'verification_documents'))}:* "
                f"{escape_markdown(get_translation(user_id, 'not_provided'))}\n"
            )
        profile_message += separator

        # Fallback for empty profiles
        if all(value == get_translation(user_id, "not_provided") for value in
               [company_name, city, contact_number, employer_type, about_company]):
            profile_message = (
                f"🏢 *{escape_markdown(get_translation(user_id, 'employer_profile_header'))}*\n"
                f"{separator}\n"
                f"⚠️ {escape_markdown(get_translation(user_id, 'no_employer_info_available'))}\n"
                f"{separator}\n"
            )

        # Send profile message
        await context.bot.send_message(
            chat_id=user_id,
            text=profile_message,
            parse_mode="MarkdownV2",  # Use MarkdownV2 for stricter parsing
            disable_web_page_preview=True
        )

        # Send verification document if available
        if verification_docs:
            try:
                await context.bot.send_document(
                    chat_id=user_id,
                    document=verification_docs,
                    caption=get_translation(user_id, "verification_document_caption")
                )
            except Exception as e:
                logging.error(f"Error sending verification document for employer_id={employer_id}: {e}")
                await context.bot.send_message(
                    chat_id=user_id,
                    text=get_translation(user_id, "document_send_error")
                )
        else:
            await context.bot.send_message(
                chat_id=user_id,
                text=get_translation(user_id, "no_verification_document")
            )

        # Show main menu button
        keyboard = [[KeyboardButton(get_translation(user_id, "employer_main_menu"))]]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "what_next"),
            reply_markup=reply_markup
        )

    except KeyError as ke:
        logging.error(f"KeyError in display_employer_profile: {ke}")
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "internal_error")
        )
    except Exception as e:
        logging.error(f"Unexpected error in display_employer_profile: {e}")
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "profile_retrieval_error")
        )
# In the employer flow
async def view_employer_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)
    # Fetch and display the employer's profile
    await display_employer_profile(user_id, context)
    return EMPLOYER_MAIN_MENU

# Employer Main Menu
async def employer_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)

    # Get employer data for personalization
    employer_data = db.get_employer_profile(user_id)
    company_name = employer_data.get('company_name', '') if employer_data else ''

    # Check for active vacancies and applications
    counts = db.get_active_vacancies_with_applications(user_id)
    active_vacancies = counts['active_vacancies']
    new_applications = counts['new_applications']

    # Check profile completion status
    profile_completion = calculate_employer_profile_completion(employer_data)

    # Modified keyboard layout as requested
    keyboard = [
        [KeyboardButton(f"🏢 {get_translation(user_id, 'employer_profile_button')} ({profile_completion}%)")],
        # Profile in its own row
        [KeyboardButton(f"📢 {get_translation(user_id, 'post_vacancy_button')}"),  # Post and manage vacancies together
         KeyboardButton(f"📊 {get_translation(user_id, 'manage_vacancies_button')} ({active_vacancies})")],
        [KeyboardButton(f"📈 {get_translation(user_id, 'view_analytics_button')}")],  # Analytics in its own row
        [KeyboardButton(f"ℹ️ {get_translation(user_id, 'help_button')}"),
         KeyboardButton(f"⭐ {get_translation(user_id, 'rate_button')}"),
         KeyboardButton(f"📝 {get_translation(user_id, 'report_button')}")]
    ]

    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

    # Create personalized welcome message (keeping all enhancements)
    welcome_msg = (
        f"👔 <b>{get_translation(user_id, 'welcome_employer')}, {company_name or get_translation(user_id, 'valued_employer')}!</b>\n\n"
        f"📊 <i>{get_translation(user_id, 'profile_completion')}:</i> {profile_completion}%\n"
        f"📢 <i>{get_translation(user_id, 'active_vacancies')}:</i> {active_vacancies} {'✨' if active_vacancies > 0 else '➡️ Post new vacancies to attract candidates'}\n"
        f"📨 <i>{get_translation(user_id, 'new_applications')}:</i> {new_applications} {'🔥' if new_applications > 5 else '💤' if new_applications == 0 else '👀'}\n\n"
    )

    # Add quick action suggestions based on current stats
    if new_applications > 0:
        welcome_msg += f"💼 <b>Quick Action:</b> {get_translation(user_id, 'review_new_applications_prompt')}\n"
    elif active_vacancies == 0:
        welcome_msg += f"💼 <b>Quick Action:</b> {get_translation(user_id, 'post_first_vacancy_prompt')}\n"

    # Add employer-specific tip of the day
    employer_tip = get_employer_tip_of_the_day(user_id)
    if employer_tip:
        welcome_msg += f"\n💼 <b>{get_translation(user_id, 'employer_tip_of_day')}:</b> {employer_tip}"

    await context.bot.send_message(
        chat_id=user_id,
        text=welcome_msg,
        parse_mode="HTML",
        reply_markup=reply_markup
    )

    return EMPLOYER_MAIN_MENU

def get_employer_tip_of_the_day(user_id: int) -> str:
    """Get a random employer tip for the user with translations."""
    tips = [
        get_translation(user_id, "employer_tip_write_effective_job_descriptions"),
        get_translation(user_id, "employer_tip_improve_employer_brand"),
        get_translation(user_id, "employer_tip_streamline_hire_process"),
        get_translation(user_id, "employer_tip_diversity_hiring"),
        get_translation(user_id, "employer_tip_candidate_experience"),
        get_translation(user_id, "employer_tip_effective_interview_techniques"),
        get_translation(user_id, "employer_tip_retention_strategies"),
        get_translation(user_id, "employer_tip_market_trends"),
        get_translation(user_id, "employer_tip_ai_in_recruiting"),
        get_translation(user_id, "employer_tip_employee_referral_programs")
    ]
    return random.choice(tips)


def calculate_employer_profile_completion(employer_data: dict) -> int:
    """Calculate employer profile completion percentage."""
    required_fields = [
        'company_name', 'city', 'contact_number',
        'employer_type', 'about_company', 'verification_docs'
    ]

    if not employer_data:
        return 0

    filled = 0
    for field in required_fields:
        value = employer_data.get(field)
        if value and str(value).lower() != "skip":
            filled += 1

    return min(100, (filled * 100) // len(required_fields))


async def display_employer_profile_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)
    employer_data = db.get_employer_profile(user_id)
    profile_completion = calculate_employer_profile_completion(employer_data)


    keyboard = [
        [KeyboardButton(f"🏢 {get_translation(user_id, 'employer_view_profile_button')} ({profile_completion}%)")],
        [KeyboardButton(f"✏️ {get_translation(user_id, 'employer_edit_profile_button')}"),
         KeyboardButton(f"📈 {get_translation(user_id, 'employer_profile_stats_button')}")],
        [KeyboardButton(f"🔒 {get_translation(user_id, 'verification_status_button')}"),
         KeyboardButton(f"🌐 {get_translation(user_id, 'employer_change_language_button')}")],
        [KeyboardButton(f"🗑️ {get_translation(user_id, 'delete_my_account_button')}")],
        [KeyboardButton(f"🔙 {get_translation(user_id, 'back_to_employer_main_menu')}")]
    ]

    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

    await context.bot.send_message(
        chat_id=user_id,
        text=get_translation(user_id, "employer_profile_menu_prompt"),
        reply_markup=reply_markup
    )
    return EMPLOYER_PROFILE_MENU


async def handle_employer_profile_actions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)
    choice = update.message.text.strip()
    employer_data = db.get_employer_profile(user_id)

    # Button text templates
    view_profile_text = f"🏢 {get_translation(user_id, 'employer_view_profile_button')}"
    edit_profile_text = f"✏️ {get_translation(user_id, 'employer_edit_profile_button')}"
    profile_stats_text = f"📈 {get_translation(user_id, 'employer_profile_stats_button')}"
    verification_text = f"🔒 {get_translation(user_id, 'verification_status_button')}"
    delete_account_text = f"🗑️ {get_translation(user_id, 'delete_my_account_button')}"
    change_lang_text = f"🌐 {get_translation(user_id, 'employer_change_language_button')}"
    back_text = f"🔙 {get_translation(user_id, 'back_to_employer_main_menu')}"

    if view_profile_text in choice:
        await display_employer_profile(user_id, context)
        return await display_employer_profile_menu(update, context)

    elif edit_profile_text in choice:
        return await edit_employer_profile(update, context)

    elif profile_stats_text in choice:
        # Enhanced employer profile stats
        active_vacancies = db.get_active_vacancies_count(user_id)
        total_applications = db.get_total_applications_count(user_id)
        hire_rate = db.get_employer_hire_rate(user_id)
        avg_response_time = db.get_avg_response_time(user_id)

        verification_status = "✅ Verified" if employer_data.get('verification_docs') else "⚠️ Unverified"
        profile_completion = calculate_employer_profile_completion(employer_data)

        stats_msg = (
            f"📊 <b>Employer Performance Dashboard</b>\n\n"
            f"🏢 <b>Company:</b> {employer_data.get('company_name', 'Not provided')}\n"
            f"📅 <b>Member Since:</b> {db.get_member_since_date(user_id)}\n\n"

            f"🔍 <b>Profile Status:</b>\n"
            f"   • Completion: {profile_completion}%\n"
            f"   • Verification: {verification_status}\n\n"

            f"📈 <b>Recruitment Metrics:</b>\n"
            f"   • Active Vacancies: {active_vacancies}\n"
            f"   • Total Applications: {total_applications}\n"
            f"   • Hire Rate: {hire_rate}%\n"
            f"   • Avg Response Time: {avg_response_time} days\n\n"

            f"🏆 <b>Profile Strength:</b>\n"
            f"{generate_profile_strength_bar(profile_completion)}\n"
            f"{get_profile_strength_tip(profile_completion, user_id)}"
        )

        await context.bot.send_message(
            chat_id=user_id,
            text=stats_msg,
            parse_mode="HTML"
        )
        return EMPLOYER_PROFILE_MENU

    elif verification_text in choice:
        if employer_data.get('verification_docs'):
            await context.bot.send_message(
                chat_id=user_id,
                text="✅ Your account is already verified with documents on file."
            )
        else:
            await context.bot.send_message(
                chat_id=user_id,
                text="📄 Please upload your business verification documents"
            )


    elif delete_account_text in choice:
        return await confirm_delete_my_account(update, context)

    elif change_lang_text in choice:
        return await show_employer_language_selection(update, context)

    elif back_text in choice:
        return await employer_main_menu(update, context)

    else:
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "invalid_choice")
        )
        return EMPLOYER_PROFILE_MENU


def generate_profile_strength_bar(completion: int) -> str:
    """Generate visual progress bar for profile strength"""
    filled = '█' * (completion // 10)
    empty = '░' * (10 - (completion // 10))
    return f"{filled}{empty} {completion}%"


def get_profile_strength_tip(completion: int, user_id: int) -> str:
    """Get personalized tip based on profile completion"""
    if completion == 100:
        return get_translation(user_id, "profile_complete_tip")
    elif completion >= 75:
        return get_translation(user_id, "profile_almost_complete_tip")
    elif completion >= 50:
        return get_translation(user_id, "profile_half_complete_tip")
    else:
        return get_translation(user_id, "profile_beginner_tip")

async def confirm_delete_my_account(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)

    # Show confirmation buttons
    keyboard = [
        [KeyboardButton(get_translation(user_id, "yes_delete_my_account_button"))],
        [KeyboardButton(get_translation(user_id, "no_keep_my_account_button"))]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

    await context.bot.send_message(
        chat_id=user_id,
        text=get_translation(user_id, "confirm_delete_my_account_prompt"),
        reply_markup=reply_markup
    )
    return CONFIRM_DELETE_MY_ACCOUNT

async def delete_my_account_confirmed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)

    # Delete the account from the database
    db.delete_employer_account(user_id)

    # Notify the user that their account has been deleted
    await context.bot.send_message(
        chat_id=user_id,
        text=get_translation(user_id, "account_deleted_message")
    )
    return ConversationHandler.END  # End the conversation

async def cancel_delete_my_account(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)

    # Notify the user that the deletion was cancelled
    await context.bot.send_message(
        chat_id=user_id,
        text=get_translation(user_id, "delete_account_cancelled")
    )

    # Return to the profile menu
    return await display_employer_profile_menu(update, context)


async def handle_my_delete_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)
    choice = update.message.text.strip()

    if choice == get_translation(user_id, "yes_delete_my_account_button"):
        # Delete the employer's account
        db.delete_employer_account(user_id)  # Ensure this function exists in your database module
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "my_account_deleted_message")
        )
        return ConversationHandler.END  # End the conversation

    elif choice == get_translation(user_id, "no_keep_my_account_button"):
        # Notify the user that the deletion was cancelled
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "delete_my_account_cancelled")
        )
        return await display_employer_profile_menu(update, context)  # Return to the profile menu

    else:
        # Invalid choice
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "invalid_choice")
        )
        return CONFIRM_DELETE_MY_ACCOUNT

async def handle_employer_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)

    # Ensure update.message exists and has text
    if not update.message or not update.message.text:
        return await employer_main_menu(update, context)

    choice = update.message.text.strip()

    # Get employer data for personalization
    employer_data = db.get_employer_profile(user_id)
    company_name = employer_data.get('company_name', '') if employer_data else ''

    # Check for active vacancies and applications
    active_vacancies = db.get_active_vacancies_count(user_id)

    # Check profile completion status
    profile_completion = calculate_employer_profile_completion(employer_data)

    # Dynamically generate button texts
    profile_button_text = f"🏢 {get_translation(user_id, 'employer_profile_button')} ({profile_completion}%)"
    post_vacancy_button_text = f"📢 {get_translation(user_id, 'post_vacancy_button')}"
    manage_vacancies_button_text = f"📊 {get_translation(user_id, 'manage_vacancies_button')} ({active_vacancies})"
    view_analytics_button_text = f"📈 {get_translation(user_id, 'view_analytics_button')}"
    help_button_text = f"ℹ️ {get_translation(user_id, 'help_button')}"
    rate_button_text = f"⭐ {get_translation(user_id, 'rate_button')}"
    report_button_text = f"📝 {get_translation(user_id, 'report_button')}"

    # Handle user's choice
    if choice == profile_button_text:
        return await display_employer_profile_menu(update, context)
    elif choice == post_vacancy_button_text:
        return await post_vacancy_start(update, context)
    elif choice == manage_vacancies_button_text:
        return await manage_vacancies(update, context)
    elif choice == view_analytics_button_text:
        return await view_analytics(update, context)
    elif choice == help_button_text:
        return await show_help(update, context)
    else:
        # Redirect to the main menu for invalid choices
        return await employer_main_menu(update, context)

async def show_employer_language_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)

    # Define the inline keyboard for language selection
    keyboard = [
        [InlineKeyboardButton("English ", callback_data="english")],
        [InlineKeyboardButton("አማርኛ ", callback_data="amharic")],
        [InlineKeyboardButton("Afaan Oromoo ", callback_data="oromia")],
        [InlineKeyboardButton("ትግርኛ ", callback_data="tigrigna")],
        [InlineKeyboardButton("Qafar af ", callback_data="afar")],
        [InlineKeyboardButton("Soomaali", callback_data="somalia")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Send the language selection prompt
    await update.message.reply_text(
        get_translation(user_id, "employer_select_language_prompt"),
        reply_markup=reply_markup
    )
    return SELECT_EMPLOYER_LANGUAGE

async def handle_employer_language_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = get_user_id(update)
    selected_language = query.data

    # Update the employer's language in the database
    db.update_user_language(user_id, selected_language)

    # Notify the user about the language change
    await context.bot.send_message(
        chat_id=user_id,
        text=get_translation(user_id, "employer_language_updated_message")
    )

    # Return to the employer main menu
    return await employer_main_menu(update, context)

async def confirm_change_employer_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = get_user_id(update)

    # Store the selected language temporarily in context.user_data
    context.user_data["selected_language"] = query.data

    # Show confirmation buttons
    keyboard = [
        [InlineKeyboardButton(get_translation(user_id, "yes_button"), callback_data="confirm_change_employer_language")],
        [InlineKeyboardButton(get_translation(user_id, "no_button"), callback_data="cancel_change_employer_language")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text=get_translation(user_id, "confirm_change_employer_language_prompt"),
        reply_markup=reply_markup
    )
    return CONFIRM_CHANGE_EMPLOYER_LANGUAGE

async def change_employer_language_confirmed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = get_user_id(update)

    # Retrieve the selected language from context.user_data
    selected_language = context.user_data.get("selected_language", "english")

    # Update the employer's language in the database
    db.update_user_language(user_id, selected_language)

    # Notify the user about the language change
    await context.bot.send_message(
        chat_id=user_id,
        text=get_translation(user_id, "employer_language_updated_message")
    )

    # Return to the employer main menu
    return await employer_main_menu(update, context)

async def cancel_change_employer_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = get_user_id(update)

    # Notify the user that the language change was cancelled
    await query.edit_message_text(
        text=get_translation(user_id, "employer_change_language_cancelled")
    )

    # Return to the employer profile menu
    return await display_employer_profile_menu(update, context)

# Display Edit Menu
async def display_edit_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)

    # Define valid fields
    valid_fields = [
        "full_name", "contact_number", "dob", "gender", "languages",
        "qualification", "field_of_study", "cgpa", "skills_experience",
        "profile_summary", "cv_path", "portfolio_link"
    ]

    # Create an inline keyboard for editing profile fields
    keyboard = [
        [InlineKeyboardButton(get_translation(user_id, f"edit_{field}"), callback_data=f"edit_{field}")]
        for field in valid_fields
    ] + [
        [InlineKeyboardButton(get_translation(user_id, "back_to_main_menu"), callback_data="back_to_main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        text=get_translation(user_id, "edit_profile_prompt"),
        reply_markup=reply_markup
    )
    return EDIT_PROFILE
# Handle Field Selection
async def handle_field_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    field_to_edit = query.data

    if field_to_edit == "back_to_main_menu":
        await query.edit_message_text(text=get_translation(user_id, "returning_to_main_menu"))
        return await main_menu(update, context)

    # Define valid fields
    valid_fields = [
        "full_name", "contact_number", "dob", "gender", "languages",
        "qualification", "field_of_study", "cgpa", "skills_experience",
        "profile_summary", "cv_path", "portfolio_link"
    ]
    valid_callback_data = {f"edit_{field}" for field in valid_fields}

    # Validate the selected field
    if field_to_edit not in valid_callback_data:
        await query.edit_message_text(text=get_translation(user_id, "invalid_field_selected"))
        return EDIT_PROFILE

    # Extract the field name (remove "edit_" prefix)
    field_name = field_to_edit.replace("edit_", "")

    # Store the field name in context.user_data
    context.user_data["field_to_edit"] = field_name

    # Prompt the user to enter a new value
    try:
        translation = get_translation(user_id, "enter_new_value_prompt")
        text = translation.format(field=field_name.replace("_", " "))
        await context.bot.send_message(
            chat_id=user_id,
            text=text
        )
    except KeyError as e:
        print(f"Error formatting translation: {e}")
        await context.bot.send_message(
            chat_id=user_id,
            text="An error occurred while processing your request. Please try again later."
        )
        return EDIT_PROFILE

    return SAVE_EDITED_FIELD


async def edit_employer_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)
    keyboard = [
        [InlineKeyboardButton(get_translation(user_id, "edit_company_name"), callback_data="edit_company_name")],
        [InlineKeyboardButton(get_translation(user_id, "edit_location"), callback_data="edit_location")],
        [InlineKeyboardButton(get_translation(user_id, "edit_contact_number"), callback_data="edit_contact_number")],
        [InlineKeyboardButton(get_translation(user_id, "edit_employer_type"), callback_data="edit_employer_type")],
        [InlineKeyboardButton(get_translation(user_id, "edit_about_company"), callback_data="edit_about_company")],
        [InlineKeyboardButton(get_translation(user_id, "edit_verification_docs"), callback_data="edit_verification_docs")],
        [InlineKeyboardButton(get_translation(user_id, "back_to_main_menu"), callback_data="back_to_employer_main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(
        chat_id=user_id,
        text=get_translation(user_id, "edit_employer_profile_prompt"),
        reply_markup=reply_markup
    )
    return EDIT_EMPLOYER_PROFILE

async def handle_edit_employer_field(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    field_to_edit = query.data

    if field_to_edit == "back_to_employer_main_menu":
        await query.edit_message_text(text=get_translation(user_id, "returning_to_main_menu"))
        return EMPLOYER_MAIN_MENU


    valid_fields = ["edit_company_name", "edit_location", "edit_contact_number", "edit_employer_type", "edit_about_company", "edit_verification_docs"]
    if field_to_edit not in valid_fields:
        await query.edit_message_text(text=get_translation(user_id, "invalid_field_selected"))
        return EDIT_EMPLOYER_PROFILE

    # Store the field to edit in context.user_data
    context.user_data["field_to_edit"] = field_to_edit.replace("edit_", "")
    await query.edit_message_text(
        text=get_translation(user_id, "enter_new_value_prompt", field=context.user_data["field_to_edit"].replace("_", " "))
    )
    return EDIT_EMPLOYER_FIELD_VALUE

async def save_updated_employer_field(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)
    field_to_edit = context.user_data.get("field_to_edit")

    if not field_to_edit:
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "field_not_found")
        )
        return EDIT_EMPLOYER_PROFILE

    try:
        if field_to_edit == "verification_docs":
            # Handle document upload
            if update.message and update.message.document:
                document = update.message.document
                # Validate document size (e.g., limit to 5 MB)
                if document.file_size > 10 * 1024 * 1024:  # 5 MB limit
                    await update.message.reply_text(get_translation(user_id, "document_too_large"))
                    return EDIT_EMPLOYER_FIELD_VALUE

                # Ensure the employer_documents directory exists
                if not os.path.exists("employer_documents"):
                    os.makedirs("employer_documents")

                # Save the document to the server
                file = await document.get_file()
                file_path = f"employer_documents/{user_id}_{document.file_name}"
                await file.download_to_drive(file_path)
                new_value = file_path
            else:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=get_translation(user_id, "no_document_uploaded")
                )
                return EDIT_EMPLOYER_FIELD_VALUE
        else:
            # Handle text input for other fields
            new_value = update.message.text.strip()
            if not new_value or len(new_value) < 3:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=get_translation(user_id, "invalid_input")
                )
                return EDIT_EMPLOYER_FIELD_VALUE

        # Fetch the current employer profile from the database
        employer_profile = db.get_employer_profile(user_id)
        if not employer_profile:
            raise ValueError(f"Employer profile not found for user ID {user_id}")

        # Extract current values from the employer profile
        employer_id, company_name, location, contact_number, employer_type, about_company, verification_docs = employer_profile

        # Update the specific field based on the field_to_edit value
        updated_fields = {
            "company_name": company_name,
            "location": location,
            "contact_number": contact_number,
            "employer_type": employer_type,
            "about_company": about_company,
            "verification_docs": verification_docs,
        }
        updated_fields[field_to_edit] = new_value

        # Save the updated fields back to the database
        db.save_employer_profile(
            user_id=user_id,
            company_name=updated_fields["company_name"],
            location=updated_fields["location"],
            employer_type=updated_fields["employer_type"],
            about_company=updated_fields["about_company"],
            verification_docs=updated_fields["verification_docs"]
        )

        # Notify the user that the field was updated successfully
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "field_updated_successfully", field=field_to_edit.replace("_", " "))
        )

        # Return to the edit employer profile menu
        return await edit_employer_profile(update, context)

    except Exception as e:
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "error_updating_field")
        )
        return EDIT_EMPLOYER_PROFILE
# Admin flow
# Admin credentials
ADMIN_USERNAME = "Arefat"
ADMIN_PASSWORD = "1234"



# (global variable)
active_admins = set()

# Admin login process
async def admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    await context.bot.send_message(
        chat_id=user_id,
        text="Welcome to the Admin Panel. Please enter your username:"
    )
    return ADMIN_LOGIN



# Then modify your admin login function
async def check_admin_credentials(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    message_text = update.message.text

    if "username" not in context.user_data:
        context.user_data["username"] = message_text
        await context.bot.send_message(
            chat_id=user_id,
            text="Please enter your password:"
        )
        return ADMIN_LOGIN
    else:
        username = context.user_data["username"]
        password = message_text

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            # Add user to active admins
            active_admins.add(user_id)
            await show_admin_menu(update, context)
            return ADMIN_MAIN_MENU
        else:
            await context.bot.send_message(
                chat_id=user_id,
                text="Invalid username or password. Please try again. Enter your username:"
            )
            context.user_data.clear()
            return ADMIN_LOGIN

def get_all_admins() -> list:
    """Get all currently active admin user IDs."""
    return list(active_admins)

# Show the admin menu
async def show_admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Use effective_user.id to handle both Message and CallbackQuery updates
    user_id = update.effective_user.id

    # Define the admin menu keyboard
    keyboard = [
        ["Manage Job Posts"],
        ["Share Job Posts"],
        ["Contact Management"],
        ["View Reports"],
        ["Broadcast"],
        ["Database Management"],
        ["Cancel"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

    # Send the admin menu message
    await context.bot.send_message(
        chat_id=user_id,
        text="Admin Menu:",
        reply_markup=reply_markup
    )
    return ADMIN_MAIN_MENU
# Handle admin menu choices
async def handle_admin_menu_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    choice = update.message.text

    if choice == "Manage Job Posts":
        await manage_job_posts(update, context)
        return ADMIN_MAIN_MENU
    elif choice == "Share Job Posts":
        await handle_share_job_posts(update, context)
    elif choice == "Contact Management":
        return await show_contact_management_dashboard(update, context)
    elif choice == "View Reports":
        await context.bot.send_message(
            chat_id=user_id,
            text="You selected View Reports. (Feature not implemented yet.)"
        )
        return ADMIN_MAIN_MENU
    elif choice == "Broadcast":
        await handle_broadcast_choice(update, context)
        return BROADCAST_TYPE
    elif choice == "Database Management":
        return await show_database_menu(update, context)  # Directly call the menu function
    elif choice == "Cancel":
        await context.bot.send_message(
            chat_id=user_id,
            text="Admin session canceled."
        )
        context.user_data.clear()
        return ConversationHandler.END

async def show_database_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show the new Database Management menu with expanded options"""
    user_id = update.effective_user.id

    keyboard = [
        [InlineKeyboardButton("Manage Users", callback_data="manage_users")],
        [InlineKeyboardButton("Manage Jobs", callback_data="manage_jobs")],
        [InlineKeyboardButton("Manage Vacancies", callback_data="ad_manage_vacancies")],
        [InlineKeyboardButton("Manage Applications", callback_data="manage_applications")],
        [InlineKeyboardButton("Export Data", callback_data="export_data")],
        [InlineKeyboardButton("Clear Data", callback_data="clear_data")],
        [InlineKeyboardButton("View System Errors", callback_data="view_system_errors")],
        [InlineKeyboardButton("Back to Admin Menu", callback_data="back_to_admin_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(
        chat_id=user_id,
        text="Database Management Menu:",
        reply_markup=reply_markup
    )
    return DATABASE_MANAGEMENT

async def manage_jobs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show submenu for managing jobs"""
    user_id = update.effective_user.id
    keyboard = [
        [InlineKeyboardButton("List Jobs", callback_data="list_jobs")],
        [InlineKeyboardButton("Remove Jobs", callback_data="remove_jobs")],
        [InlineKeyboardButton("Export Jobs", callback_data="export_jobs")],
        [InlineKeyboardButton("Back to Database Menu", callback_data="back_to_database_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(
        chat_id=user_id,
        text="Job Management Options:",
        reply_markup=reply_markup
    )
    return MANAGE_JOBS
async def ad_manage_vacancies(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show submenu for managing vacancies (renamed to avoid conflicts)"""
    user_id = update.effective_user.id
    keyboard = [
        [InlineKeyboardButton("List Vacancies", callback_data="list_vacancies")],
        [InlineKeyboardButton("Remove Vacancies", callback_data="remove_vacancies")],
        [InlineKeyboardButton("Export Vacancies", callback_data="export_vacancies")],
        [InlineKeyboardButton("Back to Database Menu", callback_data="back_to_database_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(
        chat_id=user_id,
        text="Vacancy Management Options:",
        reply_markup=reply_markup
    )
    return AD_MANAGE_VACANCIES
async def list_jobs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id

    # Fetch all jobs from the database
    jobs = db.get_all_jobs()  # Ensure this method exists in your Database class
    if not jobs:
        await context.bot.send_message(chat_id=user_id, text="No jobs found.")
        return await back_to_database_menu(update, context)

    # Create a list of jobs with buttons (paginate if needed)
    keyboard = []
    for job in jobs:
        job_title = job["job_title"]
        job_id = job["id"]
        keyboard.append([InlineKeyboardButton(f"{job_title} (ID: {job_id})", callback_data=f"job_detail_{job_id}")])
    keyboard.append([InlineKeyboardButton("Back", callback_data="back_to_manage_jobs")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(
        chat_id=user_id,
        text="Select a job to view details:",
        reply_markup=reply_markup
    )
    return LIST_JOBS

async def manage_job_posts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)
    try:
        # Normalize job post statuses before fetching pending job posts
        db.normalize_job_post_statuses()

        # Fetch pending job posts (status = 'pending') from job_posts
        pending_jobs = db.get_pending_job_posts()
        if not pending_jobs:
            await context.bot.send_message(
                chat_id=user_id,
                text=get_translation(user_id, "no_pending_jobs")
            )
            return ADMIN_MAIN_MENU

        # Validate and display pending jobs
        await fetch_and_display_pending_jobs(user_id, context)  # Fixed argument order

    except ValueError as ve:
        logging.error(f"ValueError in manage_job_posts: {ve}")
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "error_fetching_jobs", error=str(ve))
        )
    except Exception as e:
        logging.error(f"Unexpected error in manage_job_posts: {e}")
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "unexpected_error_occurred", error=str(e))
        )

    return ADMIN_MAIN_MENU


from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

# Add the "Approve & Share" button to the inline keyboard
# Add the "Approve & Share" button to the inline keyboard
async def fetch_and_display_pending_jobs(user_id: int, context: ContextTypes.DEFAULT_TYPE, page: int = 1,
                                          per_page: int = 10) -> None:
    try:
        # Fetch pending job posts
        pending_jobs = db.get_pending_job_posts()
        if not pending_jobs:
            await context.bot.send_message(
                chat_id=user_id,
                text=get_translation(user_id, "no_pending_jobs")
            )
            return

        validated_jobs = []
        for job in pending_jobs:
            try:
                job_dict = dict(zip([desc[0] for desc in db.cursor.description], list(job)))

                # Debugging: Log fetched job keys and values
                logging.debug(f"Fetched job keys: {list(job_dict.keys())}")
                logging.debug(f"Fetched job status: {job_dict.get('status', 'N/A')}")

                valid_statuses = {"pending", "rejected", "open", "closed", "approved"}
                status_value = job_dict.get("status", "").strip().lower()
                if status_value not in valid_statuses:
                    logging.warning(f"Skipping job post with invalid status: {status_value}")
                    continue

                if "source" not in job_dict or job_dict["source"] not in ("job_post", "vacancy"):
                    logging.warning(f"Skipping job post with invalid source: {job_dict.get('source', 'None')}")
                    continue

                validated_jobs.append(job_dict)
            except Exception as e:
                logging.error(f"Error validating job post: {e}")

        # Paginate results
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_jobs = validated_jobs[start_idx:end_idx]

        # Display jobs
        for job in paginated_jobs:
            job_text = (
                f"{get_translation(user_id, 'job_title')}: {job.get('job_title', 'N/A')}\n"
                f"{get_translation(user_id, 'employment_type')}: {job.get('employment_type', 'N/A')}\n"
                f"{get_translation(user_id, 'gender')}: {job.get('gender', 'N/A')}\n"
                f"{get_translation(user_id, 'quantity')}: {job.get('quantity', 'N/A')}\n"
                f"{get_translation(user_id, 'level')}: {job.get('level', 'N/A')}\n"
                f"{get_translation(user_id, 'description')}: {job.get('description', 'N/A')[:50]}...\n"
                f"{get_translation(user_id, 'deadline')}: {job.get('deadline', 'N/A')}\n"
                f"{get_translation(user_id, 'status')}: {job.get('status', 'N/A').capitalize()}\n"
                f"{get_translation(user_id, 'source')}: {job.get('source', 'N/A')}\n"
            )

            keyboard = [
                [InlineKeyboardButton(get_translation(user_id, "approve"), callback_data=f"approve_{job['id']}")],
                [InlineKeyboardButton(get_translation(user_id, "reject"), callback_data=f"reject_{job['id']}")],
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)
            await context.bot.send_message(
                chat_id=user_id,
                text=job_text,
                reply_markup=reply_markup
            )
    except Exception as e:
        logging.error(f"Error fetching and displaying pending jobs: {e}")
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "unexpected_error_occurred", error=str(e))
        )

# Handle the "Approve & Share" action
# Handle the "Approve & Share" action
async def handle_admin_job_approval(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    try:
        # Log raw callback_data
        logging.debug(f"Received callback_data: {query.data}")

        # Validate callback data
        job_id = validate_callback_data(query.data, ("approve_", "reject_"))
        if not job_id:
            logging.error(f"Invalid or missing job_id in callback_data: {query.data}")
            await context.bot.send_message(
                chat_id=user_id,
                text=get_translation(user_id, "invalid_data_detected", error="Missing or invalid job_id.")
            )
            return ADMIN_MAIN_MENU

        logging.debug(f"Extracted job_id: {job_id}")

        # Fetch and validate the job post
        validated_job_post = await fetch_and_validate_job_post(job_id, user_id, context)
        if not validated_job_post:
            logging.error(f"Failed to fetch and validate job post with ID: {job_id}")
            return ADMIN_MAIN_MENU

        try:
            validate_job_post_data(validated_job_post)
        except ValueError as ve:
            logging.error(f"Validation error in job post {job_id}: {ve}")
            await context.bot.send_message(
                chat_id=user_id,
                text=get_translation(user_id, "error_validating_job", job_id=job_id, error=str(ve))
            )
            return ADMIN_MAIN_MENU

        current_status = validated_job_post.get("status", "Unknown")
        logging.info(f"Admin {user_id} is processing job {job_id} with current status: {current_status}")

        action = query.data.split("_")[0]
        if action == "approve":
            try:
                # Get employer ID before approval
                employer_id = validated_job_post.get("employer_id")
                if not employer_id:
                    logging.error(f"No employer_id found for job {job_id}")
                    raise ValueError("No employer_id associated with this job post")

                db.approve_job_post(job_id)
                new_status = db.get_job_post_status(job_id)
                logging.info(f"Job {job_id} approved. New status: {new_status}")

                # Notify admin
                await context.bot.send_message(
                    chat_id=user_id,
                    text=get_translation(user_id, "job_approved", job_id=job_id)
                )

                # Notify employer - since employer_id is the same as user_id in your schema
                try:
                    await context.bot.send_message(
                        chat_id=employer_id,  # Directly use employer_id as it's the same as user_id
                        text=get_translation(employer_id, "your_job_approved",
                                             job_title=validated_job_post.get("job_title", "N/A"),
                                             job_id=job_id)
                    )
                except Exception as e:
                    logging.error(f"Failed to notify employer {employer_id} about approval: {e}")

            except Exception as e:
                logging.error(f"Error approving job post {job_id}: {e}")
                await context.bot.send_message(
                    chat_id=user_id,
                    text=get_translation(user_id, "error_approving_job", job_id=job_id, error=str(e))
                )
                return ADMIN_MAIN_MENU

        elif action == "reject":
            try:
                # Get employer ID from the job post
                employer_id = validated_job_post.get("employer_id")
                if not employer_id:
                    logging.error(f"No employer_id found for job {job_id}")
                    raise ValueError("No employer_id associated with this job post")

                # Store necessary information in context for the rejection process
                context.user_data.update({
                    "pending_rejection": {
                        "job_id": job_id,
                        "employer_id": employer_id,
                        "job_title": validated_job_post.get("job_title", "N/A")
                    }
                })

                # Prompt the admin for a rejection reason
                await context.bot.send_message(
                    chat_id=user_id,
                    text=get_translation(user_id, "ask_rejection_reason"),
                    reply_markup=ReplyKeyboardRemove()
                )
                return REJECT_JOB_REASON  # Transition to the next state for rejection

            except Exception as e:
                logging.error(f"Error handling job post rejection {job_id}: {e}")
                await context.bot.send_message(
                    chat_id=user_id,
                    text=get_translation(user_id, "unexpected_error_occurred", error=str(e))
                )
                return ADMIN_MAIN_MENU

    except Exception as e:
        logging.error(f"Unexpected error in handle_admin_job_approval: {e}")
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "unexpected_error_occurred", error=str(e))
        )
        return ADMIN_MAIN_MENU
#async def select_vacancy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
def format_job_post(user_id, job, bot_username, for_sharing=False):
    """Formats the job post using HTML."""
    job_details = (
        f"<b>📌 {get_translation(user_id, 'job_title')}: {escape_html(job['job_title'])}</b>\n"
        f"{'_' * 40}\n"
        f"<b>🏢 {get_translation(user_id, 'employer')}: </b>{escape_html(job.get('company_name', 'Not provided'))}\n"
        f"<b>📅 {get_translation(user_id, 'deadline')}: </b>{escape_html(job['deadline'])}\n"
        f"<b>💼 {get_translation(user_id, 'employment_type')}: </b>{escape_html(job['employment_type'])}\n"
        f"<b>🚻 {get_translation(user_id, 'gender')}: </b>{escape_html(job['gender'])}\n"
        f"<b>👥 {get_translation(user_id, 'quantity')}: </b>{(job['quantity'])}\n"
        f"<b>📊 {get_translation(user_id, 'level')}: </b>{escape_html(job['level'])}\n"
        f"{'_' * 40}\n"  
        f"<b>📝 {get_translation(user_id, 'description')}: \n </b><i>{escape_html(job['description'])}</i>\n"
        f"{'_' * 40}\n"
        f"<b>🎓 {get_translation(user_id, 'qualification')}: </b>\n{escape_html(job['qualification'])}\n"
        f"{'_' * 40}\n"
        f"<b>🔑 {get_translation(user_id, 'skills')}: </b>\n{escape_html(job['skills'])}\n"
        f"{'_' * 40}\n"
        f"<b>💲 {get_translation(user_id, 'salary')}: </b>\n{(job['salary'])}\n"
        f"<b>🎁 {get_translation(user_id, 'benefits')}: </b>\n{escape_html(job['benefits'])}\n"
        f"{'_' * 40}\n"
        f"<b>{get_translation(user_id, 'status')}: </b>{escape_html(job['status'].capitalize())}\n\n"
        f"👉 <a href='https://t.me/{bot_username}?start=apply_{job['job_id']}'>Apply Vacancy</a>"
    )
    return job_details



def escape_html(text):
    """Escape special characters for Telegram HTML formatting."""
    escape_chars = {'&': '&amp;', '<': '<', '>': '>'}
    return ''.join(escape_chars.get(char, char) for char in text)


async def handle_share_job_posts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles sharing approved job posts. Admin must manually forward them."""
    user_id = update.message.from_user.id

    try:
        db = Database()
        validated_jobs = db.fetch_approved_vacancies()

        if not validated_jobs:
            await context.bot.send_message(
                chat_id=user_id,
                text=get_translation(user_id, "no_job_posts_found")
            )
            return ADMIN_MAIN_MENU

        context.user_data["job_posts"] = validated_jobs

        for job in validated_jobs:
            job_text = format_job_post(user_id, job, context.bot.username)

            # Send the formatted job post (admin can forward manually)
            await context.bot.send_message(
                chat_id=user_id,
                text=job_text,
                parse_mode='HTML'  # Use HTML formatting
            )

        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "forward_job_posts_manually")  # Inform admin to forward manually
        )

    except Exception as e:
        logging.error(f"Unexpected error in handle_share_job_posts: {e}")
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "unexpected_error_occurred", error=str(e))
        )

    return ADMIN_MAIN_MENU


async def fetch_and_validate_job_post(job_id: int, user_id: int, context: ContextTypes.DEFAULT_TYPE) -> dict:
    try:
        # Fetch job from job_posts first
        job_post = db.get_job_post_by_id(job_id)
        if not job_post:
            # If not found, check vacancies table
            job_post = db.get_vacancy_by_id(job_id)
        if not job_post:
            raise ValueError(f"Job post with ID {job_id} not found in job_posts or vacancies.")

        # Ensure job_id and source are present
        if "job_id" not in job_post:
            raise ValueError(f"Missing job_id in fetched job post: {job_post}")
        if "source" not in job_post:
            raise ValueError(f"Missing source in fetched job post: {job_post}")

        # Validate status
        valid_statuses = {"pending", "approved", "rejected", "closed", "open"}
        job_status = job_post.get("status", "").strip().lower()
        if job_status not in valid_statuses:
            raise ValueError(f"Invalid status: '{job_status}'. Expected one of {valid_statuses}.")

        return job_post
    except ValueError as ve:
        logging.error(f"Invalid job post data: {ve}")
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "error_fetching_job", error=str(ve))
        )
        return None
    except Exception as e:
        logging.error(f"Error fetching job post {job_id}: {e}")
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "unexpected_error_occurred", error=str(e))
        )
        return None

def validate_job_post_for_rejection(job_id: int):
    """
    Validate that the job post exists and its status is 'pending'.
    """
    job_post = db.get_job_post_by_id(job_id)
    if not job_post:
        raise ValueError(f"Job post with ID {job_id} not found.")
    if job_post["status"] != "pending":
        raise ValueError(f"Cannot reject job post with ID {job_id}. Status must be 'pending'.")
    return job_post

async def handle_rejection_reason(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    reason = update.message.text.strip()

    try:
        # Validate the rejection reason
        if not reason or len(reason) > 500:
            await context.bot.send_message(
                chat_id=user_id,
                text=get_translation(user_id, "invalid_rejection_reason")
            )
            return REJECT_JOB_REASON

        # Retrieve the job ID from user_data
        job_id = context.user_data.pop("rejection_job_id", None)
        if not job_id:
            await context.bot.send_message(
                chat_id=user_id,
                text=get_translation(user_id, "error_processing_rejection_no_job_id")
            )
            return ADMIN_MAIN_MENU

        # Validate the job post before rejection
        try:
            validate_job_post_for_rejection(job_id)
        except ValueError as ve:
            logging.error(f"Invalid job post for rejection: {ve}")
            await context.bot.send_message(
                chat_id=user_id,
                text=get_translation(user_id, "error_rejecting_job", job_id=job_id, error=str(ve))
            )
            return ADMIN_MAIN_MENU

        # Reject the job post with the provided reason
        db.reject_job_post(job_id, reason)

        # Confirm the rejection to the admin
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "job_rejected", job_id=job_id, reason=reason)
        )

    except ValueError as ve:
        logging.error(f"ValueError in handle_rejection_reason: {ve}")
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "invalid_data_detected", error=str(ve))
        )
    except Exception as e:
        logging.error(f"Unexpected error rejecting job post {job_id}: {e}")
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "error_rejecting_job", job_id=job_id, error=str(e))
        )
        return ADMIN_MAIN_MENU

    # Refresh the list of pending job posts
    try:
        await manage_job_posts(update, context)
    except Exception as e:
        logging.error(f"Error refreshing job posts: {e}")
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "error_refreshing_job_posts")
        )

    return ADMIN_MAIN_MENU

# Cancel the admin session
async def cancel_admin_session(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    await context.bot.send_message(
        chat_id=user_id,
        text="Admin session canceled."
    )
    context.user_data.clear()
    return ConversationHandler.END

def update_user_data_and_proceed(context: ContextTypes.DEFAULT_TYPE, key: str, value, next_step: int):
    context.user_data[key] = value
    return next_step

def validate_quantity(quantity: str) -> bool:
    """Validate that the quantity is a positive integer."""
    try:
        value = int(quantity)
        return value > 0
    except ValueError:
        return False

from datetime import datetime

def validate_date(date_str: str) -> bool:
    """Validate that the date is in the format YYYY-MM-DD."""
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False

def validate_salary(salary: str) -> bool:
    """Validate that the salary is numeric or a valid range."""
    if "-" in salary:
        parts = salary.split("-")
        return len(parts) == 2 and all(part.strip().isdigit() for part in parts)
    return salary.strip().isdigit()

async def post_vacancy_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)

    # First, check if employer_id is already stored in user data
    employer_id = context.user_data.get("employer_id")

    # If not found in context, retrieve it from the database
    if not employer_id:
        employer_id = db.get_employer_id(user_id)

    if not employer_id:
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "employer_id_not_found")
        )
        return ConversationHandler.END

    # Store employer ID and initialize job post data
    context.user_data["job_post"] = {"employer_id": employer_id}

    await context.bot.send_message(
        chat_id=user_id,
        text=get_translation(user_id, "enter_job_title")
    )
    return POST_JOB_TITLE


async def post_job_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)

    # Validate input
    if not update.message or not update.message.text or not update.message.text.strip():
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "invalid_job_title")
        )
        return POST_JOB_TITLE

    # Store job title inside job_post
    job_title = update.message.text.strip()
    context.user_data["job_post"]["job_title"] = job_title

    # Confirm receipt of job title
    await context.bot.send_message(
        chat_id=user_id,
        text=get_translation(user_id, "job_title_received").format(job_title=job_title)
    )

    # Display employment type options
    keyboard = [
        [InlineKeyboardButton("Full-time", callback_data="full_time")],
        [InlineKeyboardButton("Part-time", callback_data="part_time")],
        [InlineKeyboardButton("Remote", callback_data="remote")],
        [InlineKeyboardButton("Hybrid", callback_data="hybrid")],
        [InlineKeyboardButton("Freelance", callback_data="freelance")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(
        chat_id=user_id,
        text=get_translation(user_id, "select_employment_type"),
        reply_markup=reply_markup
    )
    return POST_EMPLOYMENT_TYPE


async def post_employment_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    # Validate callback data
    allowed_types = {"full_time", "part_time", "remote", "hybrid", "freelance"}
    if query.data not in allowed_types:
        await query.message.reply_text(get_translation(user_id, "invalid_employment_type"))
        return POST_EMPLOYMENT_TYPE

    # Store employment type inside job_post dictionary
    context.user_data.setdefault("job_post", {})["employment_type"] = query.data

    # Confirm receipt and ask for gender preference
    keyboard = [
        [InlineKeyboardButton("Male", callback_data="male")],
        [InlineKeyboardButton("Female", callback_data="female")],
        [InlineKeyboardButton("Any", callback_data="any")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text=get_translation(user_id, "employment_type_received").format(employment_type=query.data)
        + "\n\n" + get_translation(user_id, "select_gender"),
        reply_markup=reply_markup
    )
    return POST_GENDER


async def post_gender(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    # Validate callback data
    allowed_genders = {"male", "female", "any"}
    if query.data not in allowed_genders:
        await query.message.reply_text(get_translation(user_id, "invalid_gender"))
        return POST_GENDER

    # Normalize gender to title case
    normalized_gender = query.data.capitalize()

    # Store normalized gender inside job_post
    context.user_data["job_post"]["gender"] = normalized_gender

    # Debugging log
    logging.debug(f"Received gender: {query.data}, normalized to: {normalized_gender}")

    # Confirm receipt and ask for quantity
    await query.edit_message_text(
        text=get_translation(user_id, "gender_received").format(gender=normalized_gender)
        + "\n\n" + get_translation(user_id, "enter_quantity")
    )
    return POST_QUANTITY

async def post_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)

    # Validate input
    if not update.message or not update.message.text.strip():
        await update.message.reply_text(get_translation(user_id, "invalid_quantity"))
        return POST_QUANTITY

    try:
        quantity = int(update.message.text.strip())
        if quantity <= 0:
            raise ValueError()
    except ValueError:
        await update.message.reply_text(get_translation(user_id, "invalid_quantity_positive"))
        return POST_QUANTITY

    # Store quantity inside job_post
    context.user_data["job_post"]["quantity"] = quantity

    # Confirm receipt and ask for job level
    keyboard = [
        [InlineKeyboardButton("Entry-level", callback_data="entry_level")],
        [InlineKeyboardButton("Mid-level", callback_data="mid_level")],
        [InlineKeyboardButton("Senior-level", callback_data="senior_level")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        get_translation(user_id, "quantity_received").format(quantity=quantity)
        + "\n\n" + get_translation(user_id, "select_level"),
        reply_markup=reply_markup
    )

    return POST_LEVEL


async def post_level(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    # Validate callback data
    allowed_levels = {"entry_level", "mid_level", "senior_level"}
    if query.data not in allowed_levels:
        await query.message.reply_text(get_translation(user_id, "invalid_level"))
        return POST_LEVEL

    # Store level in user data
    context.user_data.setdefault("job_post", {})["level"] = query.data

    # Confirm receipt and prompt for description in the same message
    await query.edit_message_text(
        text=f"{get_translation(user_id, 'level_received').format(level=query.data)}\n\n"
             f"{get_translation(user_id, 'enter_description')}"
    )

    return POST_DESCRIPTION


async def post_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)

    # Validate input
    if not update.message or not update.message.text.strip():
        await update.message.reply_text(get_translation(user_id, "invalid_description"))
        return POST_DESCRIPTION

    # Store description in user data
    description = update.message.text.strip()
    context.user_data["job_post"]["description"] = description

    # Confirm receipt and display qualification options in the same message
    keyboard = [
        [InlineKeyboardButton("Training", callback_data="training")],
        [InlineKeyboardButton("Degree", callback_data="degree")],
        [InlineKeyboardButton("MA", callback_data="ma")],
        [InlineKeyboardButton("PhD", callback_data="phd")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"{get_translation(user_id, 'description_received').format(description=description[:50])}\n\n"
        f"{get_translation(user_id, 'select_qualification')}",
        reply_markup=reply_markup
    )

    return POST_QUALIFICATION


async def post_qualification(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    # Validate callback data
    allowed_qualifications = {"training", "degree", "ma", "phd"}
    if query.data not in allowed_qualifications:
        await query.message.reply_text(get_translation(user_id, "invalid_qualification"))
        return POST_QUALIFICATION

    # Store qualification in user data
    context.user_data["job_post"]["qualification"] = query.data

    # Confirm receipt and prompt for skills
    await query.edit_message_text(
        text=get_translation(user_id, "qualification_received").format(qualification=query.data)
        + "\n\n" + get_translation(user_id, "enter_skills")
    )

    return POST_SKILLS


async def post_skills(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)

    # Validate input
    if not update.message or not update.message.text.strip():
        await update.message.reply_text(get_translation(user_id, "invalid_skills"))
        return POST_SKILLS

    # Store skills in user data
    skills = update.message.text.strip()
    context.user_data["job_post"]["skills"] = skills

    # Confirm receipt and prompt for salary
    await update.message.reply_text(
        text=get_translation(user_id, "skills_received").format(skills=skills[:50])
        + "\n\n" + get_translation(user_id, "enter_salary")
    )

    return POST_SALARY

async def post_salary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)

    # Ensure the message is not empty
    if not update.message or not update.message.text.strip():
        await update.message.reply_text(get_translation(user_id, "invalid_salary"))
        return POST_SALARY

    salary = update.message.text.strip()

    # Store salary in user data (no validation)
    context.user_data.setdefault("job_post", {})["salary"] = salary

    # Confirm receipt and prompt for benefits
    await update.message.reply_text(
        text=f"{get_translation(user_id, 'salary_received').format(salary=salary)}\n\n"
             f"{get_translation(user_id, 'enter_benefits')}"
    )

    return POST_BENEFITS


async def post_benefits(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)

    # Validate input
    if not update.message or not update.message.text.strip():
        await update.message.reply_text(get_translation(user_id, "invalid_benefits"))
        return POST_BENEFITS

    # Store benefits in user data
    benefits = update.message.text.strip()
    context.user_data["job_post"]["benefits"] = benefits

    # Confirm receipt and prompt for deadline
    await update.message.reply_text(
        text=f"{get_translation(user_id, 'benefits_received').format(benefits=benefits[:50])}\n\n"
             f"{get_translation(user_id, 'enter_deadline')}"
    )

    return POST_DEADLINE


import re
from datetime import datetime

async def post_deadline(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)

    if not update.message or not update.message.text.strip():
        await update.message.reply_text(get_translation(user_id, "invalid_deadline"))
        return POST_DEADLINE

    deadline = update.message.text.strip()

    if not re.match(r"^\d{4}[-/.]\d{1,2}[-/.]\d{1,2}$", deadline):
        await update.message.reply_text(
            get_translation(user_id, "invalid_date_format").format(format="YYYY-MM-DD, YYYY/MM/DD, or YYYY.MM.DD")
        )
        return POST_DEADLINE

    try:
        deadline_normalized = re.sub(r"[/.]", "-", deadline)
        deadline_date = datetime.strptime(deadline_normalized, "%Y-%m-%d").date()

        if deadline_date < datetime.now().date():
            await update.message.reply_text(
                get_translation(user_id, "invalid_deadline_future").format(format="YYYY-MM-DD, YYYY/MM/DD, or YYYY.MM.DD")
            )
            return POST_DEADLINE
    except ValueError:
        await update.message.reply_text(
            get_translation(user_id, "invalid_date_format").format(format="YYYY-MM-DD, YYYY/MM/DD, or YYYY.MM.DD")
        )
        return POST_DEADLINE

    context.user_data["job_post"]["deadline"] = deadline_normalized  # Use normalized date format for storage

    await update.message.reply_text(
        text=f"{get_translation(user_id, 'deadline_received').format(deadline=deadline_normalized)}\n\n"
             f"{get_translation(user_id, 'job_preview')}"
    )

    await job_preview(update, context)
    return CONFIRM_POST




async def save_pending_job_post(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)

    if "job_post" not in context.user_data:
        context.user_data["job_post"] = {}

    job_post = context.user_data["job_post"]

    # Store job details properly under job_post
    job_post["employer_id"] = db.get_employer_id(user_id)  # Ensure employer_id is set
    job_post["job_title"] = job_post.get("job_title", context.user_data.get("job_title"))
    job_post["employment_type"] = job_post.get("employment_type", context.user_data.get("employment_type"))
    job_post["gender"] = job_post.get("gender", context.user_data.get("gender"))
    job_post["quantity"] = job_post.get("quantity", context.user_data.get("quantity"))
    job_post["level"] = job_post.get("level", context.user_data.get("level"))
    job_post["description"] = job_post.get("description", context.user_data.get("description"))
    job_post["qualification"] = job_post.get("qualification", context.user_data.get("qualification"))
    job_post["skills"] = job_post.get("skills", context.user_data.get("skills"))
    job_post["salary"] = job_post.get("salary", context.user_data.get("salary"))
    job_post["benefits"] = job_post.get("benefits", context.user_data.get("benefits"))
    job_post["deadline"] = job_post.get("deadline", context.user_data.get("deadline"))
    job_post["status"] = "pending"  # Set status explicitly
    job_post["source"] = "job_post"  # Set source explicitly

    try:
        # Validate the job post data
        validate_job_post_data(job_post)

        # Debugging: Log the job post before saving
        logging.info(f"Saving job post with status 'pending': {job_post}")

        # Save the job post to the database
        db.save_pending_job_post(job_post)

        # Debugging: Confirm successful save
        logging.info(f"Job post saved successfully with ID: {job_post['id']}")

        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "job_post_saved_successfully")
        )
    except ValueError as e:
        logging.error(f"Validation error while saving job post: {e}")
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "job_post_validation_error").format(error=str(e))
        )
        return ConversationHandler.END
    except Exception as e:
        logging.error(f"Unexpected error while saving job post: {e}")
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "unexpected_error_occurred", error=str(e))
        )
        return ConversationHandler.END

    return await show_job_preview(update, context)
async def show_job_preview(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)

    # Extract job details properly
    job_post = context.user_data.get("job_post", {})

    if not job_post:
        logging.warning(f"🚨 Missing job post data for user {user_id}")
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "missing_job_post_data")
        )
        return ConversationHandler.END

    if "employer_id" not in job_post:
        logging.warning(f"🚨 Missing employer_id in job post for user {user_id}")
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "employer_id_not_found")
        )
        return ConversationHandler.END

    # Debugging log
    logging.info(f"✅ Job post data for preview: {job_post}")

    preview_message = (
        f"*Job Title:* {job_post.get('job_title', 'Not provided')}\n"
        f"*Employment Type:* {job_post.get('employment_type', 'Not provided')}\n"
        f"*Gender Preference:* {job_post.get('gender', 'Not provided')}\n"
        f"*Quantity:* {job_post.get('quantity', 'Not provided')}\n"
        f"*Level:* {job_post.get('level', 'Not provided')}\n"
        f"*Description:* {job_post.get('description', 'Not provided')}\n"
        f"*Qualification:* {job_post.get('qualification', 'Not provided')}\n"
        f"*Skills:* {job_post.get('skills', 'Not provided')}\n"
        f"*Salary:* {job_post.get('salary', 'Not provided')}\n"
        f"*Benefits:* {job_post.get('benefits', 'Not provided')}\n"
        f"*Application Deadline:* {job_post.get('deadline', 'Not provided')}"
    )

    keyboard = [
        [InlineKeyboardButton(get_translation(user_id, "confirm"), callback_data="confirm")],
        [InlineKeyboardButton(get_translation(user_id, "edit"), callback_data="edit")],
        [InlineKeyboardButton(get_translation(user_id, "cancel"), callback_data="cancel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(
        chat_id=user_id,
        text=preview_message,
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

    return JOB_PREVIEW


async def job_preview(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)
    job_post = context.user_data.get("job_post", {})

    if not job_post:
        logging.warning(f"🚨 Missing job post data in job_preview for user {user_id}")
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "missing_job_post_data")
        )
        return ConversationHandler.END

    if "employer_id" not in job_post:
        logging.warning(f"🚨 Missing employer_id in job_preview for user {user_id}")
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "employer_id_not_found")
        )
        return ConversationHandler.END

    try:
        # Debugging log before validation
        logging.info(f"✅ Job post before validation in job_preview: {job_post}")

        # Validate required fields
        validate_job_post_data_for_job_preview(job_post)

        # # Confirm receipt of job details
        # await context.bot.send_message(
        #     chat_id=user_id,
        #     text=get_translation(user_id, "preview_ready")
        # )

        # Generate preview text
        preview_text = generate_job_preview(job_post, user_id)

        # Create keyboard buttons (consistent with show_job_preview)
        keyboard = [
            [InlineKeyboardButton(get_translation(user_id, "confirm"), callback_data="confirm")],
            [InlineKeyboardButton(get_translation(user_id, "edit"), callback_data="edit")],
            [InlineKeyboardButton(get_translation(user_id, "cancel"), callback_data="cancel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Send preview to the user
        await context.bot.send_message(
            chat_id=user_id,
            text=preview_text,
            reply_markup=reply_markup
        )

    except ValueError as ve:
        missing_fields = str(ve)
        logging.error(f"❌ Validation error in job_preview: {missing_fields}")
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "error_validation").format(error=missing_fields)
        )
        return await post_vacancy_start(update, context)

    except Exception as e:
        logging.error(f"❌ Unexpected error in job_preview: {e}")
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "unexpected_error_occurred").format(error=str(e))
        )
        return ConversationHandler.END

    return CONFIRM_POST

def generate_job_preview(job_details: dict, user_id: int) -> str:
    """
    Generate a formatted preview of the job details.
    """
    preview_text = (
        f"{get_translation(user_id, 'job_title')}: {job_details['job_title']}\n"
        f"{get_translation(user_id, 'employment_type')}: {job_details['employment_type']}\n"
        f"{get_translation(user_id, 'gender')}: {job_details['gender']}\n"
        f"{get_translation(user_id, 'quantity')}: {job_details['quantity']}\n"
        f"{get_translation(user_id, 'level')}: {job_details['level']}\n"
        f"{get_translation(user_id, 'description')}: {job_details['description'][:50]}...\n"
        f"{get_translation(user_id, 'qualification')}: {job_details['qualification']}\n"
        f"{get_translation(user_id, 'skills')}: {job_details['skills']}\n"
        f"{get_translation(user_id, 'salary')}: {job_details['salary']}\n"
        f"{get_translation(user_id, 'benefits')}: {job_details['benefits']}\n"
        f"{get_translation(user_id, 'deadline')}: {job_details['deadline']}\n"
    )
    return preview_text
async def confirm_post(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "confirm":
        try:
            # Retrieve job post data safely
            job_post_data = context.user_data.get("job_post", {})

            # Debugging: Log the initial job post data from user context
            logging.info(f"Job post data retrieved from user context: {job_post_data}")

            # Check if job_post_data is empty or missing required fields
            required_fields = [
                "job_title", "employment_type", "gender", "quantity", "level",
                "description", "qualification", "skills", "salary", "benefits", "deadline"
            ]
            missing_fields = [field for field in required_fields if field not in job_post_data]

            if missing_fields:
                logging.error(f"Missing fields in job post data: {missing_fields}")
                await context.bot.send_message(
                    chat_id=user_id,
                    text=get_translation(user_id, "missing_required_fields").format(
                        fields=", ".join(missing_fields)
                    )
                )
                return ConversationHandler.END

            # Fetch employer ID
            employer_id = db.get_employer_id(user_id)
            if not employer_id:
                logging.warning(f"Employer ID not found for user {user_id}")
                await context.bot.send_message(
                    chat_id=user_id,
                    text=get_translation(user_id, "employer_not_registered")
                )
                return ConversationHandler.END

            # Add employer ID to job_post_data
            job_post_data["employer_id"] = employer_id

            # Debugging: Log the job post data before saving
            logging.info(f"Final job post data before saving: {job_post_data}")

            # Save job post to database
            db.save_pending_job_post(job_post_data)

            # Debugging: Confirm successful save
            logging.info(f"Job post saved successfully with employer ID: {employer_id}")

            # Confirm submission to user
            await context.bot.send_message(
                chat_id=user_id,
                text=get_translation(user_id, "post_submitted_for_approval")
            )

            # Notify all admins about the new pending job post
            admin_message = f"📢 New job post pending approval!\n\n" \
                            f"🏢 Employer ID: {employer_id}\n" \
                            f"📝 Job Title: {job_post_data.get('job_title', 'N/A')}\n" \
                            f"🕒 Submitted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n" \
                            f"Please review and approve/reject this post."

            for admin_id in get_all_admins():
                try:
                    await context.bot.send_message(
                        chat_id=admin_id,
                        text=admin_message
                    )
                except Exception as e:
                    logging.error(f"Failed to notify admin {admin_id}: {e}")
        except ValueError as ve:
            logging.error(f"Validation error while saving job post: {ve}")
            await context.bot.send_message(
                chat_id=user_id,
                text=get_translation(user_id, "error_validation", error=str(ve))
            )
        except Exception as e:
            logging.error(f"Unexpected error while saving job post: {e}")
            await context.bot.send_message(
                chat_id=user_id,
                text=get_translation(user_id, "unexpected_error_occurred", error=str(e))
            )
        finally:
            # Clear user data after processing
            logging.info(f"Clearing user data for user {user_id}")
            context.user_data.clear()
        return EMPLOYER_MAIN_MENU

    elif query.data == "edit":
        # Restart the post vacancy process
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "restarting_post_process")
        )
        return await post_vacancy_start(update, context)

#before
async def manage_vacancies(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)

    try:
        # Get enhanced job stats including application counts
        jobs_with_stats = db.get_jobs_with_stats(user_id)

        if not jobs_with_stats:
            await context.bot.send_message(
                chat_id=user_id,
                text="📭 You currently have no job listings",
                parse_mode="HTML"
            )
            return EMPLOYER_MAIN_MENU

        # Categorize jobs with visual indicators
        categorized = {
            'active': [],
            'pending': [],
            'expired': [],
            'closed': []
        }

        current_date = datetime.now().strftime('%Y-%m-%d')
        for job in jobs_with_stats:
            status = job['status'].lower()
            if status == 'pending':
                categorized['pending'].append(job)
            elif status == 'closed':
                categorized['closed'].append(job)
            elif job['application_deadline'] < current_date:
                # Mark as expired in the job data itself
                job['status'] = 'expired'
                categorized['expired'].append(job)
            else:
                categorized['active'].append(job)

        # Send overview stats
        stats_msg = (
            f"📊 <b>Your Job Listings Overview</b>\n\n"
            f"🟢 <b>Active:</b> {len(categorized['active'])} jobs\n"
            f"🟡 <b>Pending:</b> {len(categorized['pending'])} jobs\n"
            f"🔴 <b>Expired:</b> {len(categorized['expired'])} jobs\n"
            f"⚫ <b>Closed:</b> {len(categorized['closed'])} jobs\n\n"
            f"📨 <b>Total Applications:</b> {sum(j['application_count'] for j in jobs_with_stats)}\n"
        )
        await context.bot.send_message(
            chat_id=user_id,
            text=stats_msg,
            parse_mode="HTML"
        )

        # Display jobs by category with rich formatting
        for category, jobs in categorized.items():
            if jobs:
                await display_job_category(
                    category=category,
                    jobs=jobs,
                    user_id=user_id,
                    context=context,
                    include_actions=(category == 'active')
                )

    except Exception as e:
        logging.error(f"Error in manage_vacancies: {str(e)}")
        await context.bot.send_message(
            chat_id=user_id,
            text="⚠️ Failed to load vacancies. Please try again later."
        )

    return EMPLOYER_MAIN_MENU
async def select_job_to_manage(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)
    choice = update.message.text.strip()

    try:
        # Retrieve stored approved jobs
        approved_jobs = context.user_data.get("approved_jobs")
        if not approved_jobs:
            await context.bot.send_message(
                chat_id=user_id,
                text=get_translation(user_id, "no_approved_jobs_found")
            )
            return EMPLOYER_MAIN_MENU

        # Validate the selected index
        selected_index = int(choice) - 1
        if not (0 <= selected_index < len(approved_jobs)):
            raise ValueError(get_translation(user_id, "invalid_selection"))

        # Retrieve selected job details
        selected_job = approved_jobs[selected_index]
        job_id = selected_job["id"]

        # Store the selected job in user_data
        context.user_data["selected_job_id"] = job_id

        # Display actions for the selected job
        keyboard = [
            [InlineKeyboardButton(get_translation(user_id, "view_applications_button"), callback_data=f"view_apps {job_id}")],
            [InlineKeyboardButton(get_translation(user_id, "close_vacancy_button"), callback_data=f"close {job_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Send the job details and actions
        job_text = (
            f"{get_translation(user_id, 'job_title')}: {selected_job['job_title']}\n"
            f"{get_translation(user_id, 'deadline')}: {selected_job['deadline']}\n"
            f"{get_translation(user_id, 'status')}: {selected_job['status'].capitalize()}\n"
        )
        await context.bot.send_message(
            chat_id=user_id,
            text=job_text + get_translation(user_id, "select_action_for_job"),
            reply_markup=reply_markup
        )

        return HANDLE_JOB_ACTIONS  # Transition to job action handling state

    except ValueError as ve:
        logging.error(f"ValueError in select_job_to_manage: {ve}")
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "invalid_selection")
        )
        return SELECT_JOB_TO_MANAGE

    except Exception as e:
        logging.error(f"Unexpected error in select_job_to_manage: {e}")
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "unexpected_error_occurred")
        )
        return EMPLOYER_MAIN_MENU

async def handle_job_actions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    try:
        # Parse the callback data
        action, job_id_str = query.data.split("_", 1)
        job_id = int(job_id_str)

        # Validate job ownership
        job_type, job_data = validate_job_ownership(db, job_id, user_id)
        if not job_type:
            await context.bot.send_message(
                chat_id=user_id,
                text=get_translation(user_id, "unauthorized_access")
            )
            return EMPLOYER_MAIN_MENU

        # Normalize status
        try:
            validated_job = validate_job_post(job_data)
        except ValueError as ve:
            logging.error(f"Invalid job post data: {ve}")
            await context.bot.send_message(
                chat_id=user_id,
                text=get_translation(user_id, "invalid_job_post", error=str(ve))
            )
            return EMPLOYER_MAIN_MENU

        status = validated_job["status"]

        if action == "view_apps":
            if job_type != "vacancy":
                await context.bot.send_message(
                    chat_id=user_id,
                    text=get_translation(user_id, "cannot_view_apps_for_pending_job")
                )
                return EMPLOYER_MAIN_MENU

            # Fetch and display applicants
            await fetch_and_display_applicants(job_id, user_id, context)
            return VIEW_APPLICATIONS

        elif action == "close":
            if job_type == "vacancy" and status != "approved":
                await context.bot.send_message(
                    chat_id=user_id,
                    text=get_translation(user_id, "cannot_close_non_approved_vacancy")
                )
                return EMPLOYER_MAIN_MENU

            # Confirm closing the vacancy
            context.user_data["close_job_id"] = job_id
            await context.bot.send_message(
                chat_id=user_id,
                text=get_translation(user_id, "confirm_close_vacancy_prompt").format(job_id=job_id),
                reply_markup=ReplyKeyboardMarkup([["Yes", "No"]], one_time_keyboard=True, resize_keyboard=True)
            )
            return CONFIRM_CLOSE

        else:
            await context.bot.send_message(
                chat_id=user_id,
                text=get_translation(user_id, "unknown_action_detected")
            )
            return EMPLOYER_MAIN_MENU

    except ValueError as ve:
        logging.error(f"ValueError in handle_job_actions: {ve}")
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "invalid_action_detected", error=str(ve))
        )
    except Exception as e:
        logging.error(f"Unexpected error in handle_job_actions: {e}")
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "unexpected_error_occurred", error=str(e))
        )

    return EMPLOYER_MAIN_MENU


async def display_job_category(category: str, jobs: list, user_id: int,
                               context: ContextTypes.DEFAULT_TYPE, include_actions: bool):
    """Display jobs in a category with enhanced formatting"""
    category_titles = {
        'active': "🟢 ACTIVE VACANCIES",
        'pending': "🟡 PENDING APPROVAL",
        'expired': "🔴 EXPIRED VACANCIES",
        'closed': "⚫ CLOSED VACANCIES"
    }

    await context.bot.send_message(
        chat_id=user_id,
        text=f"<b>{category_titles[category]}</b>",
        parse_mode="HTML"
    )

    for job in sorted(jobs, key=lambda x: x['application_deadline']):
        await display_job_post(job, user_id, context, include_actions)


async def display_job_post(job: dict, user_id: int,
                           context: ContextTypes.DEFAULT_TYPE, include_actions: bool):
    """Display single job post with rich formatting"""
    try:
        # Calculate days remaining (for active jobs)
        days_left = "N/A"
        current_status = job['status'].lower()
        if 'application_deadline' in job and job['application_deadline']:
            delta = (datetime.strptime(job['application_deadline'], '%Y-%m-%d') - datetime.now()).days
            if current_status == 'approved':
                days_left = f"{max(0, delta)} days" if delta >= 0 else "Expired"
                if delta < 0:
                    current_status = 'expired'
            elif current_status == 'expired':
                days_left = "Expired"

        # Status indicator
        status_icons = {
            'approved': '🟢',
            'pending': '🟡',
            'rejected': '🔴',
            'closed': '⚫',
            'expired': '🔴'
        }
        status_icon = status_icons.get(current_status, '⚪')

        # Build message with professional formatting
        msg = (
            f"{status_icon} <b>{escape_html(job['job_title'])}</b>\n"
            f"📅 <i>Deadline:</i> {job['application_deadline']} ({days_left})\n"
            f"👥 <i>Applications:</i> {job.get('application_count', 0)}\n"
            f"💰 <i>Salary:</i> {job.get('salary', 'Not specified')}\n\n"
            f"📝 <i>Description:</i>\n{escape_html(job['description'][:150])}..."
        )

        # Add action buttons
        reply_markup = None
        if current_status == 'approved' and include_actions:
            reply_markup = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("👀 View Applicants", callback_data=f"view_apps_{job['id']}"),
                    InlineKeyboardButton("🔒 Close Job", callback_data=f"close_{job['id']}")
                ],
                [
                    InlineKeyboardButton("📊 Stats", callback_data=f"stats_{job['id']}"),
                    InlineKeyboardButton("🔄 Renew", callback_data=f"renew_{job['id']}")
                ]
            ])
        elif current_status == 'expired':
            reply_markup = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🔄 Renew Vacancy", callback_data=f"renew_{job['id']}"),
                    InlineKeyboardButton("📊 Stats", callback_data=f"stats_{job['id']}")
                ]
            ])

        await context.bot.send_message(
            chat_id=user_id,
            text=msg,
            parse_mode="HTML",
            reply_markup=reply_markup
        )

    except Exception as e:
        logging.error(f"Error displaying job post: {str(e)}")
        await context.bot.send_message(
            chat_id=user_id,
            text=f"⚠️ Couldn't display job {job.get('id', '')}"
        )

def validate_and_format_job_post(job: dict, user_id: int, include_actions: bool) -> tuple:
    """
    Validate and format a job post for display.
    """
    required_fields = {
        "job_id", "status", "job_title", "employment_type", "gender", "quantity", "level",
        "description", "qualification", "skills", "salary", "benefits", "deadline"
    }

    # Fill missing fields with "Not provided" instead of failing
    validated_job = {field: job.get(field, "Not provided") for field in required_fields}

    # Check for any missing required fields
    missing_fields = [field for field, value in validated_job.items() if value == "Not provided"]
    if missing_fields:
        raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")

    # Extract job details
    job_id = validated_job["job_id"]
    job_title = validated_job["job_title"]
    employment_type = validated_job["employment_type"]
    gender = validated_job["gender"]
    quantity = validated_job["quantity"]
    level = validated_job["level"]
    description = validated_job["description"][:50] + "..." if validated_job["description"] else "Not provided"
    qualification = validated_job["qualification"]
    skills = validated_job["skills"]
    salary = validated_job["salary"]
    benefits = validated_job["benefits"]
    deadline = validated_job["deadline"]
    status = validated_job["status"].lower()

    # Format the job post details
    job_text = (
        f"{get_translation(user_id, 'job_title')}: {job_title}\n"
        f"{get_translation(user_id, 'employment_type')}: {employment_type}\n"
        f"{get_translation(user_id, 'gender')}: {gender}\n"
        f"{get_translation(user_id, 'quantity')}: {quantity}\n"
        f"{get_translation(user_id, 'level')}: {level}\n"
        f"{get_translation(user_id, 'description')}: {description}\n"
        f"{get_translation(user_id, 'qualification')}: {qualification}\n"
        f"{get_translation(user_id, 'skills')}: {skills}\n"
        f"{get_translation(user_id, 'salary')}: {salary}\n"
        f"{get_translation(user_id, 'benefits')}: {benefits}\n"
        f"{get_translation(user_id, 'deadline')}: {deadline}\n"
        f"{get_translation(user_id, 'status')}: {status.capitalize()}\n"
    )

    # Define keyboard buttons based on the job status
    keyboard = []
    if include_actions:
        if status == "approved":
            keyboard.extend([
                [InlineKeyboardButton(get_translation(user_id, "view_applications_button"), callback_data=f"view_apps_{job_id}")],
                [InlineKeyboardButton(get_translation(user_id, "close_vacancy_button"), callback_data=f"close_{job_id}")]
            ])
        elif status == "pending":
            keyboard.append([InlineKeyboardButton(get_translation(user_id, "resubmit_vacancy_button"), callback_data=f"resubmit_{job_id}")])

    return job_text, InlineKeyboardMarkup(keyboard) if keyboard else None
def validate_job_ownership(db, job_id: int, employer_id: int):
    try:
        db.cursor.execute("""
            SELECT 
                CASE WHEN source = 'vacancy' THEN 'vacancy' ELSE 'job_post' END AS job_type,
                id AS job_id, 
                employer_id, 
                job_title, 
                employment_type, 
                gender, 
                quantity, 
                level, 
                description, 
                qualification, 
                skills, 
                salary, 
                benefits, 
                deadline, 
                status, 
                source
            FROM (
                SELECT 
                    id, 
                    employer_id, 
                    job_title, 
                    employment_type, 
                    gender, 
                    quantity, 
                    level, 
                    description, 
                    qualification, 
                    skills, 
                    salary, 
                    benefits, 
                    deadline, 
                    status, 
                    'job_post' AS source
                FROM job_posts
                WHERE id = ? AND employer_id = ?
                UNION ALL
                SELECT 
                    id, 
                    employer_id, 
                    job_title, 
                    employment_type, 
                    gender, 
                    quantity, 
                    level, 
                    description, 
                    qualification, 
                    skills, 
                    salary, 
                    benefits, 
                    application_deadline, 
                    status, 
                    'vacancy' AS source
                FROM vacancies
                WHERE id = ? AND employer_id = ?
            )
        """, (job_id, employer_id, job_id, employer_id))

        result = db.cursor.fetchone()
        if result:
            columns = [column[0] for column in db.cursor.description]
            job_data = dict(zip(columns, result))
            return job_data["source"], job_data  # Returns 'vacancy' or 'job_post'

        return None, None
    except sqlite3.Error as e:
        logging.error(f"Database error validating job ownership: {e}")
        return None, None


async def handle_vacancy_actions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    try:
        # More robust callback data parsing
        parts = query.data.split('_')
        if len(parts) < 2:
            raise ValueError(f"Invalid callback data format: {query.data}")

        action = parts[0]
        job_id_str = parts[-1]  # Always take last part as job ID

        try:
            job_id = int(job_id_str)
        except ValueError:
            raise ValueError(f"Invalid job ID format: {job_id_str}")

        # Validate job ownership
        job_type, job_data = validate_job_ownership(db, job_id, user_id)
        if not job_type:
            await context.bot.send_message(
                chat_id=user_id,
                text=get_translation(user_id, "unauthorized_access")
            )
            return EMPLOYER_MAIN_MENU

        validated_job = validate_job_post(job_data)
        status = validated_job["status"].lower()

        # Check if job is expired based on deadline
        current_date = datetime.now().strftime('%Y-%m-%d')
        is_expired = job_data['deadline'] < current_date

        # Handle all possible actions
        if action == "close":
            if job_type == "vacancy" and status != "approved":
                await context.bot.send_message(
                    chat_id=user_id,
                    text=get_translation(user_id, "cannot_close_non_approved_vacancy")
                )
                return await employer_main_menu(update, context)

            context.user_data["close_job_id"] = job_id
            await context.bot.send_message(
                chat_id=user_id,
                text=get_translation(user_id, "confirm_close_vacancy_prompt").format(job_id=job_id),
                reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Yes"), KeyboardButton("No")]],
                                                 resize_keyboard=True, one_time_keyboard=True)
            )
            return CONFIRM_CLOSE

        elif action == "view" and "apps" in query.data:  # Handle "view_apps_5" format
            if job_type != "vacancy":
                await context.bot.send_message(
                    chat_id=user_id,
                    text=get_translation(user_id, "cannot_view_apps_for_pending_job")
                )
                return EMPLOYER_MAIN_MENU
            return await view_applicants_list(update, context)

        elif action == "stats":
            stats = db.get_vacancy_stats(job_id)
            await context.bot.send_message(
                chat_id=user_id,
                text=format_vacancy_stats(stats, user_id),
                parse_mode="HTML"
            )
            return EMPLOYER_MAIN_MENU

        elif action == "renew":
            # Allow renew if either:
            # 1. Status is explicitly 'expired' in DB
            # 2. Or deadline has passed (even if status is still 'approved')
            if job_data['status'].lower() == 'expired' or is_expired:
                context.user_data["renew_job_id"] = job_id
                await show_renew_options(update, context)
                return RENEW_VACANCY
            else:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=get_translation(user_id, "can_only_renew_expired")
                )
                return EMPLOYER_MAIN_MENU

        else:
            await context.bot.send_message(
                chat_id=user_id,
                text=get_translation(user_id, "unknown_action_detected")
            )
            return EMPLOYER_MAIN_MENU

    except ValueError as ve:
        logging.error(f"ValueError in handle_vacancy_actions: {ve}")
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "invalid_action_detected", error=str(ve))
        )
    except Exception as e:
        logging.error(f"Unexpected error in handle_vacancy_actions: {e}")
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "unexpected_error_occurred", error=str(e))
        )

    return EMPLOYER_MAIN_MENU
def format_vacancy_stats(stats: dict, user_id: int) -> str:
    """Format stats into a readable message"""
    return (
        f"📊 <b>Vacancy Statistics</b>\n\n"
        f"📨 <i>Total Applications:</i> {stats.get('total_applications', 0)}\n"
        f"✅ <i>Successful Hires:</i> {stats.get('hires', 0)}\n"
        f"🕒 <i>Pending Reviews:</i> {stats.get('pending', 0)}\n"
        f"💡 <i>Tip:</i> {get_translation(user_id, 'stats_improvement_tip')}"
    )

async def show_renew_options(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show renewal options for expired vacancies"""
    user_id = update.callback_query.from_user.id
    await context.bot.send_message(
        chat_id=user_id,
        text="🔄 Select renewal duration:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("30 days", callback_data="renew_30")],
            [InlineKeyboardButton("60 days", callback_data="renew_60")],
            [InlineKeyboardButton("Custom", callback_data="renew_custom")]
        ])
    )


async def handle_renew_duration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    choice = query.data.split("_")[1]

    job_id = context.user_data.get("renew_job_id")
    if not job_id:
        await context.bot.send_message(user_id, "⚠️ Renewal session expired")
        return EMPLOYER_MAIN_MENU

    if choice in ("30", "60"):
        days = int(choice)
        new_deadline = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d')
        return await confirm_renewal(update, context, job_id, new_deadline)
    else:
        await context.bot.send_message(
            chat_id=user_id,
            text="📅 Enter custom duration in days (e.g., 45):",
            reply_markup=ReplyKeyboardRemove()
        )
        return RENEW_VACANCY


async def handle_custom_renew_duration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    job_id = context.user_data.get("renew_job_id")

    try:
        days = int(update.message.text.strip())
        if not 1 <= days <= 365:
            raise ValueError
        new_deadline = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d')
        return await confirm_renewal(update, context, job_id, new_deadline)
    except ValueError:
        await update.message.reply_text("❌ Please enter a number between 1-365")
        return RENEW_VACANCY


async def confirm_renewal(update: Update, context: ContextTypes.DEFAULT_TYPE,
                          job_id: int, new_deadline: str) -> int:
    user_id = update.message.from_user.id if update.message else update.callback_query.from_user.id

    context.user_data["renewal_data"] = {
        "job_id": job_id,
        "new_deadline": new_deadline
    }

    job_title = db.get_vacancy_title(job_id)
    await context.bot.send_message(
        chat_id=user_id,
        text=f"🔄 Confirm renewal for:\n<b>{job_title}</b>\nNew Deadline: {new_deadline}",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Confirm", callback_data="confirm_renew")],
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel_renew")]
        ])
    )
    return CONFIRM_RENEWAL


async def process_renewal_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    choice = query.data.split("_")[0]

    if choice == "cancel":
        await query.edit_message_text("❌ Renewal cancelled")
        return EMPLOYER_MAIN_MENU

    renewal_data = context.user_data.get("renewal_data")
    if not renewal_data:
        await query.edit_message_text("⚠️ Renewal session expired")
        return EMPLOYER_MAIN_MENU

    try:
        db.renew_vacancy(
            job_id=renewal_data["job_id"],
            new_deadline=renewal_data["new_deadline"]
        )
        await query.edit_message_text(
            f"✅ Vacancy renewed until {renewal_data['new_deadline']}",
            parse_mode="HTML"
        )
    except Exception as e:
        logging.error(f"Renewal failed: {e}")
        await query.edit_message_text("⚠️ Renewal failed. Please try again.")

    return EMPLOYER_MAIN_MENU


async def view_applicants_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    try:
        job_id = int(query.data.split("_")[2])
        context.user_data["selected_job_id"] = job_id

        # Get job details with stats
        job_details = db.get_vacancy_with_stats(job_id)
        if not job_details:
            await query.edit_message_text("Job not found")
            return EMPLOYER_MAIN_MENU

        # Format deadline display
        deadline = job_details.get('application_deadline', 'N/A')
        if deadline != 'N/A':
            try:
                deadline_date = datetime.strptime(deadline, '%Y-%m-%d')
                deadline = deadline_date.strftime('%b %d, %Y')
            except ValueError:
                pass

        validated_job = {
            'job_title': escape_html(job_details.get('job_title', 'Unspecified Position')),
            'deadline': deadline,
            'total_applications': job_details.get('total_applications', 0),
            'approved_count': job_details.get('approved_count', 0),
            'rejected_count': job_details.get('rejected_count', 0)
        }



        # Get and validate applicants
        raw_applicants = db.get_applications_for_job_with_title(job_id) or []
        applicants = []
        for app in raw_applicants:
            applicants.append({
                'application_id': app.get('application_id'),
                'full_name': escape_html(app.get('full_name', 'Anonymous')),
                'status': app.get('status', 'pending'),
                'application_date': app.get('application_date', 'N/A'),
                'field_of_study': app.get('field_of_study', 'Not specified'),
                'cv_exists': bool(app.get('cv_path')),
                'score': app.get('match_score', 0)
            })

        if not applicants:
            await context.bot.send_message(
                chat_id=user_id,
                text="📭 No applications received for this position yet",
                parse_mode="HTML"
            )
            return EMPLOYER_MAIN_MENU

        # Pagination setup
        context.user_data['applicant_page'] = 0
        context.user_data['all_applicants'] = applicants
        context.user_data['page_size'] = 5  # Applicants per page

        # Send job overview
        overview_msg = (
            f"📋 <b>Applications for:</b> {validated_job['job_title']}\n\n"
            f"📅 Deadline: {validated_job['deadline']} \n "
            f"👥 Total Applicants: {validated_job['total_applications']}\n"
            f"✅ Approved: {validated_job['approved_count']} | "
            f"❌ Rejected: {validated_job['rejected_count']}\n\n"
            f"<i>Showing top candidates:</i>"
            f"<i>(You can export to see all applicants in Excel and their respective CVs.)</i>"

        )
        await context.bot.send_message(
            chat_id=user_id,
            text=overview_msg,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(
                    "Export to Excel 📊",
                    callback_data=f"export_excel_{job_id}"
                )
            ]])
        )

        # Display first page
        await display_applicant_page(user_id, context)

    except Exception as e:
        logging.error(f"Error viewing applicants: {str(e)}")
        await context.bot.send_message(
            chat_id=user_id,
            text="⚠️ Failed to retrieve applicants. Please try again.",
            parse_mode="HTML"
        )

    return VIEW_APPLICATIONS


async def display_applicant_page(user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Display one page of applicants with navigation controls"""
    applicants = context.user_data['all_applicants']
    current_page = context.user_data['applicant_page']
    page_size = context.user_data['page_size']
    start_idx = current_page * page_size
    page_applicants = applicants[start_idx:start_idx + page_size]

    for i, applicant in enumerate(page_applicants, start_idx + 1):
        status_icon = {'pending': '🟡', 'approved': '🟢', 'rejected': '🔴'}.get(applicant['status'], '⚪')

        applicant_msg = (
            f"{i}. {status_icon} <b>{applicant['full_name']}</b>\n"
            f"📅 Applied: {applicant['application_date']}\n"
            f"📝 Status: {applicant['status'].capitalize()}\n"
            f"💼 Field of Study: {applicant['field_of_study']}"
        )

        await context.bot.send_message(
            chat_id=user_id,
            text=applicant_msg,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(
                    "Review",
                    callback_data=f"review_{applicant['application_id']}"
                )
            ]])
        )

    # Pagination controls
    total_pages = (len(applicants) + page_size - 1) // page_size
    if total_pages > 1:
        pagination_buttons = []
        if current_page > 0:
            pagination_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data="prev_page"))
        if current_page < total_pages - 1:
            pagination_buttons.append(InlineKeyboardButton("Next ➡️", callback_data="next_page"))

            # Add Export to Excel button
        pagination_buttons.append(InlineKeyboardButton("Export to Excel 📊",
                                                       callback_data=f"export_excel_{context.user_data['selected_job_id']}"))
        await context.bot.send_message(
            chat_id=user_id,
            text=f"Page {current_page + 1}/{total_pages}",
            reply_markup=InlineKeyboardMarkup([pagination_buttons])
        )


# Add to your callback handler
async def handle_page_navigation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "next_page":
        context.user_data['applicant_page'] += 1
    elif query.data == "prev_page":
        context.user_data['applicant_page'] -= 1

    await display_applicant_page(user_id, context)
    return VIEW_APPLICATIONS


async def handle_applicant_review(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    try:
        application_id = int(query.data.split('_')[1])
        application = db.get_complete_application_details(application_id)

        if not application:  # This now properly checks for empty dict
            await query.edit_message_text("⚠️ Application not found or no longer exists")
            return VIEW_APPLICATIONS

        context.user_data["selected_applicant"] = application
        try:
            details = format_applicant_details(application, user_id)
        except Exception as e:
            logging.error(f"Error formatting applicant details: {e}")
            await query.edit_message_text("⚠️ Error displaying application details")
            return VIEW_APPLICATIONS


        # Create buttons - make sure download button has correct pattern
        keyboard = [
            [InlineKeyboardButton("✅ Accept", callback_data="accept_applicant")],
            [InlineKeyboardButton("❌ Reject", callback_data="reject_applicant")],
        ]

        # Only show download button if CV exists
        if application.get('cv_path'):
            keyboard.append(
                [InlineKeyboardButton("📥 Download CV", callback_data=f"download_cv_{application_id}")]
            )

        await query.edit_message_text(
            text=details,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        return ACCEPT_REJECT_CONFIRMATION
    except Exception as e:
        logging.error(f"Error reviewing applicant: {e}")
        await query.edit_message_text("Failed to load application details")
        return VIEW_APPLICATIONS


def format_applicant_details(application: dict, user_id: int) -> str:
    """Completely safe applicant details formatter"""
    if not application or not isinstance(application, dict):
        return "⚠️ Application information not available"

    # Helper function for safe value extraction
    def safe_get(key, default='N/A'):
        value = application.get(key, default)
        return str(value) if value not in [None, ''] else default

    # Profile details
    profile = {
        'dob': safe_get('dob'),
        'qualification': safe_get('qualification'),
        'field_of_study': safe_get('field_of_study'),
        'cgpa': safe_get('cgpa'),
        'languages': safe_get('languages'),
        'profile_summary': safe_get('profile_summary', 'Not provided')
    }

    # Portfolio link
    portfolio_link = (
        f'<a href="{escape_html(application["portfolio_link"])}">View Portfolio</a>'
        if application.get("portfolio_link") else 'Not Provided'
    )

    separator = "────────────────────"

    return (
        f"<b>Applicant Details</b>\n\n"
        f"{separator}\n"
        f"👤 <b>Name:</b> {escape_html(safe_get('full_name'))}\n"
        f"📅 <b>Applied:</b> {safe_get('application_date')}\n"
        f"📝 <b>Status:</b> {safe_get('status', 'pending').capitalize()}\n"
        f"📄 <b>CV:</b> {'Available' if application.get('cv_path') else 'Not Provided'}\n"
        f"🔗 <b>Portfolio:</b> {portfolio_link}\n"
        f"👫 <b>Gender:</b> {escape_html(safe_get('gender'))}\n"
        f"📱 <b>Contact:</b> {escape_html(safe_get('contact_number'))}\n"
        f"🎂 <b>Date of Birth:</b> {profile['dob']}\n"
        f"{separator}\n"
        f"<b>Education</b>\n"
        f"🎓 <b>Qualification:</b> {escape_html(profile['qualification'])}\n"
        f"📚 <b>Field of Study:</b> {escape_html(profile['field_of_study'])}\n"
        f"⭐ <b>CGPA:</b> {profile['cgpa']}\n"
        f"{separator}\n"
        f"<b>Skills & Languages</b>\n"
        f"🗣️ <b>Languages:</b> {escape_html(profile['languages'])}\n"
        f"🛠️ <b>Skills:</b> {escape_html(safe_get('skills_experience'))}\n"
        f"{separator}\n"
        f"<b>Profile Summary</b>\n"
        f"{escape_html(profile['profile_summary'])}\n"
        f"{separator}\n"
        f"<b>For Position:</b> {escape_html(safe_get('job_title'))}\n"
        f"{separator}\n"
        f"<b>Cover Letter</b>\n"
        f"{escape_html(safe_get('cover_letter', 'Not provided'))}\n"
    )

async def handle_cv_download(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    try:
        application_id = int(query.data.split('_')[-1])
        application = context.user_data.get("selected_applicant") or db.get_application_details(application_id)

        if not application:
            await query.answer("Application not found", show_alert=True)
            return VIEW_APPLICATIONS

        cv_file_id = application.get("cv_path")
        if not cv_file_id:
            await query.answer("No CV available for this applicant", show_alert=True)
            return ACCEPT_REJECT_CONFIRMATION

        try:
            await context.bot.send_document(
                chat_id=query.from_user.id,
                document=cv_file_id,
                filename=f"CV_{application.get('full_name', 'Applicant').replace(' ', '_')}.pdf",
                caption=f"📄 CV for {application.get('full_name', 'Applicant')}"
            )
            return ACCEPT_REJECT_CONFIRMATION
        except Exception as e:
            logging.error(f"Failed to send CV: {str(e)}")
            await query.answer("Failed to send CV. Please try again.", show_alert=True)
            return ACCEPT_REJECT_CONFIRMATION

    except Exception as e:
        logging.error(f"Error in CV download handler: {str(e)}")
        await query.answer("Error processing request", show_alert=True)
        return ACCEPT_REJECT_CONFIRMATION
#this is before editting
#this is before editting
#this is before editting
#this is before editting
#this is before editting
async def select_applicant(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)
    choice = update.message.text.strip()

    try:
        # Retrieve the selected job ID from context
        job_id = context.user_data.get("selected_job_id")
        if not job_id:
            await context.bot.send_message(
                chat_id=user_id,
                text=get_translation(user_id, "no_job_selected_error")
            )
            return VIEW_APPLICATIONS

        # Fetch all applications for the selected job
        applications = db.get_applications_for_job_with_title(job_id)
        validated_apps = [validate_application(app) for app in applications]

        # Validate the selected index
        selected_index = int(choice) - 1
        if not (0 <= selected_index < len(validated_apps)):
            raise ValueError("Invalid applicant number")

        # Get the selected applicant's details
        selected_app = validated_apps[selected_index]
        context.user_data["selected_applicant"] = selected_app
        job_seeker_id = selected_app["job_seeker_id"]
        job_seeker_profile = db.get_user_profile(job_seeker_id)

        # Define a separator for better readability
        separator = escape_markdown("────────────────────")

        # Format applicant details with professional style
        details = (
            f"👤 *{escape_markdown(get_translation(user_id, 'applicant_details'))}*\n"
            f"{separator}\n"
            f"• *{escape_markdown(get_translation(user_id, 'name'))}:* `{escape_markdown(selected_app['full_name'])}`\n"
            f"• *{escape_markdown(get_translation(user_id, 'application_date'))}:* `{escape_markdown(selected_app['application_date'])}`\n"
            f"• *{escape_markdown(get_translation(user_id, 'cv'))}:* "
            f"`{'Available' if selected_app['additional_docs'] else 'Not Provided'}`\n"
            f"• *{escape_markdown(get_translation(user_id, 'portfolio_link'))}:* " +
            (f"[{escape_markdown(get_translation(user_id, 'view_portfolio'))}]({selected_app['portfolio_link']})\n"
             if selected_app['portfolio_link'] else f"`{escape_markdown('Not Provided')}`\n") +
            f"• *{escape_markdown(get_translation(user_id, 'gender'))}:* `{escape_markdown(selected_app['gender'])}`\n"
            f"• *{escape_markdown(get_translation(user_id, 'contact_number'))}:* `{escape_markdown(selected_app['contact_number'])}`\n"
            f"• *{escape_markdown(get_translation(user_id, 'dob'))}:* `{escape_markdown(job_seeker_profile.get('dob', 'N/A'))}`\n"
            f"{separator}\n"
            f"🎓 *{escape_markdown(get_translation(user_id, 'education_details'))}*\n"
            f"• *{escape_markdown(get_translation(user_id, 'qualification'))}:* `{escape_markdown(job_seeker_profile.get('qualification', 'N/A'))}`\n"
            f"• *{escape_markdown(get_translation(user_id, 'field_of_study'))}:* `{escape_markdown(job_seeker_profile.get('field_of_study', 'N/A'))}`\n"
            f"• *{escape_markdown(get_translation(user_id, 'cgpa'))}:* `{escape_markdown(str(job_seeker_profile.get('cgpa', 'N/A')))}`\n"
            f"{separator}\n"
            f"💼 *{escape_markdown(get_translation(user_id, 'skills_experience'))}*\n"
            f"• *{escape_markdown(get_translation(user_id, 'languages'))}:* `{escape_markdown(job_seeker_profile.get('languages', 'N/A'))}`\n"
            f"• *{escape_markdown(get_translation(user_id, 'skills'))}:* `{escape_markdown(job_seeker_profile.get('skills_experience', 'N/A'))}`\n"
            f"• *{escape_markdown(get_translation(user_id, 'profile_summary'))}:*\n"
            f"```{escape_markdown(job_seeker_profile.get('profile_summary', 'N/A'))}```\n"  
            f"{separator}\n"
            f"• *{escape_markdown(get_translation(user_id, 'cover_letter'))}:*\n"
            f"```{escape_markdown(selected_app['cover_letter'])}```\n" 
            f"{separator}\n"
            f"📝 *{escape_markdown(get_translation(user_id, 'status'))}:* `{escape_markdown(selected_app['status'].capitalize())}`\n"
        )

        # Send the formatted details message
        await context.bot.send_message(
            chat_id=user_id,
            text=details,
            parse_mode="MarkdownV2",
            disable_web_page_preview=True
        )

        # Send CV if available
        cv_file_id = selected_app.get("additional_docs")  # Get the file_id
        if cv_file_id:
            try:
                # Send the CV file directly using the file_id
                await context.bot.send_document(
                    chat_id=user_id,
                    document=cv_file_id,
                    caption=get_translation(user_id, "applicant_cv_caption")
                )
            except Exception as e:
                logging.error(f"Error sending CV document: {e}")
                await context.bot.send_message(
                    chat_id=user_id,
                    text=get_translation(user_id, "failed_to_send_cv")
                )

        query = update.callback_query
        application_id = int(query.data.split('_')[1])
        application = db.get_application_details(application_id)
        # Provide Accept/Reject buttons
        keyboard = [
            [InlineKeyboardButton("✅ Accept", callback_data="accept_applicant")],
            [InlineKeyboardButton("❌ Reject", callback_data="reject_applicant")]
        ]
        if application.get('cv_path'):
            keyboard.append(
                [InlineKeyboardButton("📥 Download CV", callback_data=f"download_cv_{application_id}")]
            )

    except ValueError:
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "invalid_selection_error")
        )
        return VIEW_APPLICATIONS



    except Exception as e:
        logging.error(f"Error fetching applicant details: {e}")
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "failed_to_retrieve_applicant_details")
        )

    return ACCEPT_REJECT_CONFIRMATION
async def handle_accept_reject(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    action = query.data

    try:
        # Retrieve the selected applicant
        selected_app = context.user_data.get("selected_applicant")
        if not selected_app:
            await query.edit_message_text(
                text=get_translation(user_id, "no_applicant_selected_error")
            )
            return VIEW_APPLICATIONS



        job_seeker_id = selected_app["job_seeker_id"]
        job_title = selected_app["job_title"]

        if action == "accept_applicant":
            # Prompt the employer to send an optional message
            await query.edit_message_text(
                text=get_translation(user_id, "send_optional_message_prompt")
            )
            return EMPLOYER_MESSAGE_INPUT
        elif action == "reject_applicant":
            # Prompt the employer to provide a rejection reason
            await query.edit_message_text(
                text=get_translation(user_id, "provide_rejection_reason_prompt")
            )
            return REJECTION_REASON_INPUT

    except Exception as e:
        logging.error(f"Unexpected error in handle_accept_reject: {e}")
        await query.edit_message_text(
            text=get_translation(user_id, "unexpected_error_occurred", error=str(e))
        )
        return VIEW_APPLICATIONS

    return VIEW_APPLICATIONS

async def handle_rejection_reason_application(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)
    rejection_reason = update.message.text.strip()

    try:
        # Retrieve the selected applicant
        selected_app = context.user_data.get("selected_applicant")
        if not selected_app:
            await context.bot.send_message(
                chat_id=user_id,
                text=get_translation(user_id, "no_applicant_selected_error")
            )
            return VIEW_APPLICATIONS

        job_seeker_id = selected_app["job_seeker_id"]
        job_title = selected_app["job_title"]

        # Save the rejection decision in the database
        db.save_decision(
            application_id=selected_app["application_id"],
            decision="rejected",
            rejection_reason=rejection_reason
        )

        # Update status to rejected in the database - now with correct arguments
        db.update_application_status(
            application_id=selected_app["application_id"],
            status="rejected",
            rejection_reason=rejection_reason
        )

        # Notify the job seeker
        await context.bot.send_message(
            chat_id=job_seeker_id,
            text=get_translation(job_seeker_id, "application_rejected").format(
                job_title=job_title,
                reason=rejection_reason if rejection_reason else "No reason provided"
            )
        )
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "applicant_rejected_confirmation")
        )

    except Exception as e:
        logging.error(f"Unexpected error in handle_rejection_reason: {e}")
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "unexpected_error_occurred", error=str(e))
        )
        return VIEW_APPLICATIONS

    return VIEW_APPLICATIONS

async def handle_employer_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)
    employer_message = update.message.text.strip()

    try:
        selected_app = context.user_data.get("selected_applicant")
        if not selected_app:
            await context.bot.send_message(
                chat_id=user_id,
                text=get_translation(user_id, "no_applicant_selected_error")
            )
            return VIEW_APPLICATIONS

        job_seeker_id = selected_app["job_seeker_id"]
        job_title = selected_app["job_title"]

        # Save the acceptance decision in the application_decisions table
        db.save_decision(
            application_id=selected_app["application_id"],
            decision="approved",
            employer_message=employer_message
        )

        # Update the status to approved in the applications table
        db.update_application_status(
            selected_app["application_id"],
            "approved"
        )

        applicant_message = (
            f"🎉 **Congratulations!** You have been selected for the job: *{job_title}*. 🎉\n\n"
            f"{employer_message if employer_message.lower() != 'skip' else 'The employer will contact you soon.'}"
        )

        # Notify the job seeker
        await context.bot.send_message(
            chat_id=job_seeker_id,
            text=applicant_message,
            parse_mode="Markdown"
        )

        # Confirm to the employer that the applicant has been accepted
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "applicant_accepted_confirmation")
        )
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "applicant_accepted_confirmation")
        )

    except Exception as e:
        logging.error(f"Unexpected error in handle_employer_message: {e}")
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "unexpected_error_occurred", error=str(e))
        )
        return VIEW_APPLICATIONS

    return VIEW_APPLICATIONS

import logging
import pandas as pd
from io import BytesIO


async def export_to_excel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.callback_query.from_user.id
    job_id = int(update.callback_query.data.split("_")[-1])
    try:
        # Generate Excel file
        applications = db.get_applications_for_job(job_id)
        validated_apps = [validate_application(app) for app in applications]

        # Prepare Excel data
        data = []
        for app in validated_apps:
            profile = db.get_user_profile(app["job_seeker_id"])
            # Format portfolio link as hyperlink
            portfolio_link = app.get("portfolio_link", "")
            if portfolio_link:
                portfolio_cell = f'=HYPERLINK("{portfolio_link}", "View Portfolio")'
            else:
                portfolio_cell = "Not Provided"
            # Check CV availability
            cv_status = "Available" if app.get("additional_docs") else "Not Provided"
            data.append([
                app["full_name"],
                app["application_date"],
                app["gender"],
                app["contact_number"],
                profile.get("dob", "N/A"),
                profile.get("qualification", "N/A"),
                profile.get("field_of_study", "N/A"),
                profile.get("cgpa", "N/A"),
                profile.get("languages", "N/A"),
                profile.get("skills_experience", "N/A"),
                profile.get("profile_summary", "N/A"),
                app["cover_letter"],
                portfolio_cell,
                cv_status,
                app["status"].capitalize()
            ])

        # Create DataFrame
        df = pd.DataFrame(data, columns=[
            "Full Name", "Application Date", "Gender", "Contact Number", "Date of Birth",
            "Qualification", "Field of Study", "CGPA", "Languages", "Skills",
            "Profile Summary", "Cover Letter", "Portfolio Link", "CV Available", "Status"
        ])

        # Replace NaN and INF values in the DataFrame
        df.replace([float('inf'), float('-inf')], "N/A", inplace=True)  # Replace INF with "N/A"
        df.fillna("N/A", inplace=True)  # Replace NaN with "N/A"

        # Use xlsxwriter for better formatting
        excel_file = BytesIO()
        with pd.ExcelWriter(excel_file, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name="Applicants")

            # Get workbook and worksheet
            workbook = writer.book
            worksheet = writer.sheets['Applicants']

            # Enable nan_inf_to_errors option in xlsxwriter
            workbook.use_future_functions = True  # Required for some advanced features
            workbook.nan_inf_to_errors = True  # Handle NaN/INF values

            # Add title section
            title_format = workbook.add_format({
                'bold': True,
                'font_size': 18,  # Larger font size for title
                'font_color': '#FFFFFF',
                'align': 'center',
                'valign': 'vcenter',
                'fg_color': '#002060'
            })
            worksheet.merge_range('A1:O2', f"📊 Applicants Report for Job ID: {job_id}", title_format)

            # Add headers with style
            header_format = workbook.add_format({
                'bold': True,
                'font_size': 14,  # Larger font size for headers
                'font_color': '#FFFFFF',
                'align': 'center',
                'valign': 'vcenter',
                'fg_color': '#002060',
                'border': 1
            })
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(2, col_num, value, header_format)

            # Add data rows with alternating colors
            even_row_format = workbook.add_format({
                'align': 'top',
                'valign': 'vcenter',
                'border': 1,
                'fg_color': '#E6E6E6',  # Slightly darker gray for better visibility
                'text_wrap': True  # Enable text wrapping
            })
            odd_row_format = workbook.add_format({
                'align': 'top',
                'valign': 'vcenter',
                'border': 1,
                'fg_color': '#FFFFFF',  # White for alternating rows
                'text_wrap': True  # Enable text wrapping
            })

            # Set column widths
            for col_num, column in enumerate(df.columns):
                if column in ["Profile Summary", "Cover Letter"]:
                    worksheet.set_column(col_num, col_num, 50)  # Fixed width for long text columns
                else:
                    # Auto-fit width for other columns based on header length
                    header_length = len(column)
                    worksheet.set_column(col_num, col_num, header_length + 5)  # Add padding

            for row_num in range(3, len(df) + 3):
                for col_num in range(len(df.columns)):
                    cell_value = df.iat[row_num - 3, col_num]
                    cell_format = even_row_format if row_num % 2 == 0 else odd_row_format

                    # Highlight "N/A" values in red and italic
                    if str(cell_value).strip() == "N/A":
                        cell_format = workbook.add_format({
                            'italic': True,
                            'font_color': '#FF0000',
                            'align': 'top',
                            'valign': 'vcenter',
                            'border': 1,
                            'text_wrap': True
                        })

                    # Format portfolio links as hyperlinks
                    if col_num == 12 and cell_value != "Not Provided":
                        worksheet.write_url(
                            row_num, col_num,
                            cell_value.split('"')[1],
                            string='View Portfolio',
                            cell_format=workbook.add_format({
                                'font_color': 'blue',
                                'underline': 1,
                                'align': 'top',
                                'valign': 'vcenter',
                                'border': 1
                            })
                        )
                    else:
                        worksheet.write(row_num, col_num, cell_value, cell_format)

                # Adjust row height based on content length
                profile_summary = df.iat[row_num - 3, 10]  # Column K (Profile Summary)
                cover_letter = df.iat[row_num - 3, 11]  # Column L (Cover Letter)
                max_lines = max(len(str(profile_summary).split('\n')), len(str(cover_letter).split('\n')))
                worksheet.set_row(row_num, 15 * max_lines)  # Adjust row height dynamically

            # Freeze headers
            worksheet.freeze_panes(3, 0)

            # Add Summary Sheet
            summary_sheet = workbook.add_worksheet("Summary")
            summary_sheet.merge_range('A1:B1', "📊 Applicants Summary Report", title_format)

            # Add summary data with safe calculations
            average_cgpa = round(df[df['CGPA'] != "N/A"]['CGPA'].astype(float).mean(), 2)
            average_cgpa = average_cgpa if not pd.isna(average_cgpa) else "N/A"

            summary_data = [
                ["Total Applicants", len(df)],
                ["Average CGPA", average_cgpa],
                ["Top 5 Qualifications", ', '.join(df['Qualification'].value_counts().head(5).index)],
                ["Most Common Languages", ', '.join(df['Languages'].value_counts().head(5).index)],
                ["Most Popular Fields of Study", ', '.join(df['Field of Study'].value_counts().head(5).index)],
                ["CVs Available", df['CV Available'].value_counts().get("Available", 0)],
                ["CVs Not Provided", df['CV Available'].value_counts().get("Not Provided", 0)]
            ]

            for row_num, row_data in enumerate(summary_data, 3):
                for col_num, value in enumerate(row_data):
                    summary_sheet.write(row_num, col_num, value, header_format if row_num == 3 else None)

            # Auto-fit summary sheet columns
            summary_sheet.set_column('A:B', 30)

        excel_file.seek(0)

        # Send Excel file
        await context.bot.send_document(
            chat_id=user_id,
            document=excel_file,
            filename=f"applicants_job_{job_id}.xlsx"
        )

        # Send individual CVs
        for app in validated_apps:
            if app.get("additional_docs"):
                try:
                    await context.bot.send_document(
                        chat_id=user_id,
                        document=app["additional_docs"],
                        caption=f"{app['full_name']}'s CV"
                    )
                except Exception as e:
                    logging.error(f"Failed to send CV for {app['full_name']}: {e}")
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=f"⚠️ Failed to send CV for {app['full_name']}"
                    )

    except Exception as e:
        logging.error(f"Export error: {e}", exc_info=True)
        await context.bot.send_message(
            chat_id=user_id,
            text="Export failed. Please try again later."
        )
async def fetch_and_validate_applications(job_id: int, user_id: int, context: ContextTypes.DEFAULT_TYPE) -> list:
    """Fetch and validate applications for a specific job."""
    try:
        applications = db.get_applications_for_job(job_id)
        if not applications:
            await context.bot.send_message(
                chat_id=user_id,
                text=get_translation(user_id, "no_applications_found").format(job_id=job_id)
            )
            return []
        validated_apps = [validate_application(app) for app in applications]
        return validated_apps
    except ValueError as ve:
        logging.error(f"Invalid application data for job {job_id}: {ve}")
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "error_fetching_applications")
        )
        return []
    except Exception as e:
        logging.error(f"Error fetching applications for job {job_id}: {e}")
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "unexpected_error_occurred")
        )
        return []

async def confirm_close(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    try:
        # Extract job ID from callback data
        job_id = validate_callback_data(query.data, "close")

        # Validate job ID exists and belongs to the employer
        job_type, job_data = validate_job_ownership(db, job_id, user_id)
        if not job_type:
            await context.bot.send_message(
                chat_id=user_id,
                text=get_translation(user_id, "unauthorized_access")
            )
            return EMPLOYER_MAIN_MENU

        # Store job ID in user_data
        context.user_data["close_job_id"] = job_id

        # Confirm closing the vacancy
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "confirm_close_vacancy_prompt").format(job_id=job_id)
        )

    except ValueError as ve:
        logging.error(f"ValueError in confirm_close: {ve}")
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "invalid_action_detected", error=str(ve))
        )
    except Exception as e:
        logging.error(f"Unexpected error in confirm_close: {e}")
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "unexpected_error_occurred")
        )

    return CONFIRM_CLOSE

async def handle_close_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)
    choice = update.message.text.strip().lower()

    try:
        if choice == "yes":
            job_id = context.user_data.pop("close_job_id", None)
            if not job_id:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=get_translation(user_id, "error_closing_vacancy")
                )
                return EMPLOYER_MAIN_MENU

            # Close the job post or vacancy
            try:
                db.update_vacancy_status(job_id, "closed")
                await context.bot.send_message(
                    chat_id=user_id,
                    text=get_translation(user_id, "vacancy_closed_successfully").format(job_id=job_id)
                )
            except Exception as e:
                logging.error(f"Error closing vacancy {job_id}: {e}")
                await context.bot.send_message(
                    chat_id=user_id,
                    text=get_translation(user_id, "error_closing_vacancy")
                )
                return EMPLOYER_MAIN_MENU

        elif choice == "no":
            await context.bot.send_message(
                chat_id=user_id,
                text=get_translation(user_id, "closing_canceled")
            )
        else:
            await context.bot.send_message(
                chat_id=user_id,
                text=get_translation(user_id, "invalid_choice")
            )
            return CONFIRM_CLOSE

    except Exception as e:
        logging.error(f"Unexpected error in handle_close_confirmation: {e}")
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "unexpected_error_occurred", error=str(e))
        )

    # Refresh the list of vacancies
    try:
        await manage_vacancies(update, context)
    except Exception as e:
        logging.error(f"Error refreshing vacancies: {e}")
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "error_refreshing_vacancies")
        )

    return EMPLOYER_MAIN_MENU

def validate_callback_data(callback_data: str, prefixes: tuple) -> int:
    """
    Validate and extract job_id from callback_data.
    """
    try:
        logging.debug(f"Processing callback_data: {callback_data}")  # Log the raw callback_data
        logging.debug(f"Using prefixes: {prefixes}")  # Log the prefixes being checked

        for prefix in prefixes:
            if callback_data.startswith(prefix):
                # Correctly remove the prefix without removing valid numbers
                job_id = callback_data[len(prefix):]

                logging.debug(f"Extracted job_id: {job_id}")  # Log the extracted job_id

                # Ensure job_id is numeric
                if not job_id.isdigit():
                    raise ValueError(f"Invalid job_id: {job_id}")

                return int(job_id)

        raise ValueError(f"Invalid callback_data: {callback_data}. Expected one of prefixes: {prefixes}")

    except Exception as e:
        logging.error(f"Error validating callback_data: {e}")
        return None

def validate_application(application: dict):
    """Validate the structure of an application dictionary."""
    required_fields = [
        "application_id", "job_seeker_id", "full_name", "cover_letter",
        "application_date", "status", "job_id", "additional_docs", "portfolio_link",
        "gender", "contact_number",
        "languages", "qualification", "field_of_study",
        "cgpa", "skills", "profile_summary"
    ]
    missing_fields = [field for field in required_fields if field not in application]
    if missing_fields:
        raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")

    # Validate application_date format
    try:
        datetime.strptime(application["application_date"], "%Y-%m-%d %H:%M:%S")
    except ValueError:
        raise ValueError(f"Invalid date format: {application['application_date']}")

    # Validate status
    if application["status"] not in ("pending", "reviewed", "approved", "rejected"):
        raise ValueError(f"Invalid status: {application['status']}")

    # Exclude withdrawn applications from further processing
    if application["status"] == "withdrawn":
        return None

    return application

async def VIEW_APPLICATIONS(job_id: int, user_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        # Fetch and display applicants
        await fetch_and_display_applicants(job_id, user_id, context)
    except ValueError as ve:
        logging.error(f"ValueError in VIEW_APPLICATIONS: {ve}")
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "invalid_data_detected", error=str(ve))
        )
    except Exception as e:
        logging.error(f"Unexpected error in VIEW_APPLICATIONS: {e}")
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "unexpected_error_occurred", error=str(e))
        )

async def fetch_and_display_applicants(update: Update, job_id: int, user_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        applications = db.get_applications_for_job(job_id)
        if not applications:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"No applications found for job ID {job_id}."
            )
            return

        validated_apps = []
        for app in applications:
            validated_app = validate_application(app)
            if validated_app is not None:  # Only include non-withdrawn applications
                validated_apps.append(validated_app)

        # Format the list of applicants
        message = ""
        for idx, app in enumerate(validated_apps, start=1):
            message += f"{idx}. {app['full_name']} ({app['application_date']})\n"

        if message:
            keyboard = [
                [InlineKeyboardButton("Export to Excel", callback_data=f"export_excel_{job_id}")],
                [InlineKeyboardButton("Back to Manage Vacancies", callback_data="back_to_manage_vacancies")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await context.bot.send_message(
                chat_id=user_id,
                text=message + "\nSelect an applicant by number to view details.",
                reply_markup=reply_markup
            )
        else:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"No valid applications found for job ID {job_id}."
            )

    except Exception as e:
        logging.error(f"Error fetching applicants for job {job_id}: {e}")
        await context.bot.send_message(
            chat_id=user_id,
            text=f"Error fetching applications: {str(e)}"
        )
async def handle_view_applications(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    try:
        # Extract job ID from callback data
        parts = query.data.split("_")
        if len(parts) < 3:
            raise ValueError("Invalid callback data format.")
        job_id = parts[2]

        # Validate job ID exists and is open/approved
        job_post = db.get_job_post_by_id(job_id)
        if not job_post or job_post["status"] not in ("approved", "open"):
            await context.bot.send_message(
                chat_id=user_id,
                text=get_translation(user_id, "job_not_open").format(job_id=job_id)
            )
            return EMPLOYER_MAIN_MENU

        # Fetch and display applicants
        await fetch_and_display_applicants(job_id, user_id, context)

    except ValueError as ve:
        logging.error(f"ValueError in handle_view_applications: {ve}")
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "invalid_data_detected", error=str(ve))
        )
    except Exception as e:
        logging.error(f"Unexpected error in handle_view_applications: {e}")
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "unexpected_error_occurred", error=str(e))
        )

    return VIEW_APPLICATIONS

async def confirm_resubmit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)
    job_id = context.user_data.get("resubmit_job_id")

    try:
        if not job_id:
            raise ValueError("Job ID not found in user data.")

        # Validate that the job post exists and belongs to the employer
        job_type, job_data = validate_job_ownership(db, job_id, user_id)
        if not job_type or job_type != "job_post":
            await context.bot.send_message(
                chat_id=user_id,
                text=get_translation(user_id, "job_not_found").format(job_id=job_id)
            )
            return EMPLOYER_MAIN_MENU

        # Reset the job post status to 'pending' and clear rejection reason
        db.resubmit_job_post(job_id)
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "vacancy_resubmitted_successfully").format(job_id=job_id)
        )

    except ValueError as ve:
        logging.error(f"ValueError in confirm_resubmit: {ve}")
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "invalid_data_detected", error=str(ve))
        )
    except Exception as e:
        logging.error(f"Error resubmitting job post {job_id}: {e}")
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "error_resubmitting_vacancy")
        )
    finally:
        # Clear user_data and refresh the list of vacancies
        context.user_data.pop("resubmit_job_id", None)
        try:
            await manage_vacancies(update, context)
        except Exception as e:
            logging.error(f"Error refreshing vacancies: {e}")
            await context.bot.send_message(
                chat_id=user_id,
                text=get_translation(user_id, "error_refreshing_vacancies")
            )
    return EMPLOYER_MAIN_MENU


async def fetch_and_display_vacancies(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> list:
    """
    Fetch and display all job posts (pending and approved) for the specified employer.
    """
    try:
        # Fetch job posts for the employer
        job_posts = db.get_job_posts_by_employer(user_id)
        if not job_posts:
            await context.bot.send_message(
                chat_id=user_id,
                text=get_translation(user_id, "no_job_posts_found")
            )
            return []

        # Validate and process job posts
        validated_jobs = []
        for job in job_posts:
            try:
                validated_job = validate_job_post(dict(zip([col[0] for col in db.cursor.description], job)))
                validated_jobs.append(validated_job)
            except ValueError as ve:
                logging.warning(f"Skipping invalid job post: {ve}")
                continue

        # Format job titles with unique numbers and statuses
        message = get_translation(user_id, "vacancies_list_header") + "\n"
        for idx, job in enumerate(validated_jobs, start=1):
            message += f"{idx}. {job['job_title']} ({job['status'].capitalize()})\n"

        # Store validated jobs in user_data
        context.user_data["vacancies"] = validated_jobs

        # Send the list of job posts to the employer
        await context.bot.send_message(
            chat_id=user_id,
            text=message + "\n" + get_translation(user_id, "select_vacancy_prompt"),
            reply_markup=ReplyKeyboardRemove()
        )

        return validated_jobs

    except Exception as e:
        logging.error(f"Error fetching and displaying job posts: {e}")
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "error_fetching_jobs", error=str(e))
        )
        return []
from openpyxl import Workbook
from io import BytesIO
import logging

def export_applications_to_excel(applications: list, job_title: str, user_id: int) -> BytesIO:
    """
    Export all applications for a job post to an Excel file.
    """
    try:
        wb = Workbook()
        ws = wb.active
        ws.title = job_title

        # Define headers with localization
        headers = [
            get_translation(user_id, "applicant_name"),
            get_translation(user_id, "cover_letter"),
            get_translation(user_id, "unique_number"),
            get_translation(user_id, "application_date"),
            get_translation(user_id, "status")
        ]
        ws.append(headers)

        # Validate and process applications
        validated_apps = [validate_application(app) for app in applications]

        # Add application data
        for app in validated_apps:
            ws.append([
                app["full_name"],
                app["cover_letter"][:50],  # Truncate cover letter for better readability
                app["application_id"],
                app["application_date"],
                app["status"].capitalize()
            ])

        # Save workbook to a BytesIO object
        excel_file = BytesIO()
        wb.save(excel_file)
        excel_file.seek(0)
        return excel_file

    except ValueError as ve:
        logging.error(f"Invalid application data: {ve}")
        raise  # Re-raise the exception to allow the caller to handle it
    except Exception as e:
        logging.error(f"Error exporting applications to Excel: {e}")
        raise  # Re-raise the exception to allow the caller to handle it


async def view_analytics(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)

    # Get comprehensive analytics data
    analytics_data = db.get_employer_analytics(user_id)
    company_name = db.get_employer_profile(user_id).get('company_name', 'Your Company')

    # Create visually rich analytics message
    analytics_msg = f"""
📊 <b>{company_name} - Employment Analytics Dashboard</b>
━━━━━━━━━━━━━━━━━━━━━━━━

<b>📈 PERFORMANCE OVERVIEW</b>
🟢 <b>Active Vacancies:</b> {analytics_data.get('active_vacancies', 0)}
📨 <b>Total Applications:</b> {analytics_data.get('total_applications', 0)}
✅ <b>Hire Rate:</b> {analytics_data.get('hire_rate', 0)}%
⏱️ <b>Avg Response Time:</b> {analytics_data.get('avg_response_time', 0)} days
📅 <b>Member Since:</b> {analytics_data.get('member_since', 'N/A')}

<b>📊 APPLICATION FLOW</b>
📥 <b>New Applications:</b> {analytics_data.get('pending_applications', 0)}
👁️ <b>Viewed Applications:</b> {analytics_data.get('reviewed_applications', 0)}
✅ <b>Approved:</b> {analytics_data.get('approved_applications', 0)}
❌ <b>Rejected:</b> {analytics_data.get('rejected_applications', 0)}

<b>📅 RECENT ACTIVITY</b>
{format_recent_activity(analytics_data.get('recent_activity', []))}

<b>💡 TIPS FOR IMPROVEMENT</b>
{get_analytics_tips(analytics_data)}
    """

    # Create interactive keyboard
    keyboard = [
        [InlineKeyboardButton("📈 Performance Trends", callback_data="analytics_trends")],
        [InlineKeyboardButton("👥 Candidate Demographics", callback_data="analytics_demographics")],
        [InlineKeyboardButton("⏱️ Response Time Analysis", callback_data="analytics_response")],
        [InlineKeyboardButton("📊 Compare to Peers", callback_data="analytics_benchmark")],
        [InlineKeyboardButton("📤 Export Data", callback_data="analytics_export")],
        [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="go_to_employer_main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        # Try to generate and send a chart
        chart = generate_analytics_chart(analytics_data)
        if chart:
            await context.bot.send_photo(
                chat_id=user_id,
                photo=chart,
                caption=analytics_msg,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
        else:
            # Fallback to text-only message if chart generation fails
            await context.bot.send_message(
                chat_id=user_id,
                text=analytics_msg,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
    except Exception as e:
        logging.error(f"Error sending analytics: {e}")
        # Fallback to simple message if anything fails
        await context.bot.send_message(
            chat_id=user_id,
            text=analytics_msg,
            parse_mode="HTML",
            reply_markup=reply_markup
        )

    return ANALYTICS_VIEW


def generate_analytics_chart(data: dict):
    """Generate a simple bar chart of key metrics"""
    try:
        import matplotlib.pyplot as plt
        import io

        # Prepare data
        labels = ['Vacancies', 'Applications', 'Hire Rate']
        values = [
            data.get('active_vacancies', 0),
            data.get('total_applications', 0),
            data.get('hire_rate', 0)
        ]

        # Create figure
        fig, ax = plt.subplots(figsize=(10, 5))
        bars = ax.bar(labels, values)

        # Add value labels
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2., height,
                    f'{height}',
                    ha='center', va='bottom')

        ax.set_title('Key Performance Metrics')
        plt.tight_layout()

        # Save to bytes buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=80)
        plt.close()
        buf.seek(0)

        return buf
    except Exception as e:
        logging.error(f"Chart generation error: {e}")
        return None

def format_recent_activity(activities: list) -> str:
    """Format recent activity into readable lines"""
    if not activities:
        return "No recent activity"

    formatted = []
    icons = {
        'application': '📨',
        'approval': '✅',
        'rejection': '❌',
        'post': '📢',
        'view': '👁️'
    }

    for activity in activities[:5]:  # Show last 5 activities
        icon = icons.get(activity['type'], '⚪')
        formatted.append(f"{icon} {activity['date']}: {activity['description']}")

    return "\n".join(formatted)


def get_analytics_tips(data: dict) -> str:
    """Generate personalized tips based on analytics"""
    tips = []

    if data['hire_rate'] < 20:
        tips.append("- Your hire rate is below average. Consider refining your job descriptions or requirements.")

    if data['avg_response_time'] > 7:
        tips.append("- Your response time is slower than average. Faster responses improve candidate experience.")

    if data['pending_applications'] > 10:
        tips.append(
            f"- You have {data['pending_applications']} pending applications. Review them to avoid missing good candidates.")

    if not data['active_vacancies']:
        tips.append("- You currently have no active vacancies. Post new jobs to attract more candidates.")

    return "\n".join(tips) if tips else "You're doing great! Keep up the good work."


async def handle_analytics_actions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle analytics sub-menu actions"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    action = query.data

    if action == "analytics_trends":
        await show_performance_trends(update, context)
    elif action == "analytics_demographics":
        await show_demographics(update, context)
    elif action == "analytics_response":
        await show_response_analysis(update, context)
    elif action == "analytics_benchmark":
        await show_benchmark_comparison(update, context)
    elif action == "analytics_export":
        await show_export_options(update, context)
        return ANALYTICS_EXPORT
    elif action == "analytics_back":
        return await view_analytics(update, context)
    elif action.startswith("export_"):  # Add this line to handle export actions directly
        return await handle_export_format(update, context)
    elif action == "go_to_employer_main_menu":
        return await employer_main_menu(update, context)

    return ANALYTICS_VIEW



async def show_export_options(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show export format selection menu with comprehensive error handling"""
    query = update.callback_query
    await query.answer()

    # Store user ID for easier access
    user_id = query.from_user.id

    # Create the export options keyboard
    keyboard = [
        [InlineKeyboardButton("📊 CSV Export", callback_data="export_csv")],
        [InlineKeyboardButton("📈 Excel Export", callback_data="export_excel")],
        [InlineKeyboardButton("📄 PDF Export", callback_data="export_pdf")],
        [InlineKeyboardButton("🔙 Back to Analytics", callback_data="back_to_analytics")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # First attempt: Try to edit the existing message
    try:
        if query.message and query.message.text:
            await query.edit_message_text(
                text="Select export format:",
                reply_markup=reply_markup
            )
            return
    except Exception as edit_error:
        logging.warning(f"Message edit failed for user {user_id}: {str(edit_error)}")

    # Second attempt: Try to delete then send new message
    try:
        # Clean up old message if it exists
        if query.message:
            try:
                await query.message.delete()
            except Exception as delete_error:
                logging.debug(f"Couldn't delete old message: {str(delete_error)}")

        # Send fresh message
        await context.bot.send_message(
            chat_id=user_id,
            text="Select export format:",
            reply_markup=reply_markup
        )
    except Exception as send_error:
        logging.error(f"Failed to send new message to user {user_id}: {str(send_error)}")
        # Ultimate fallback - send plain text instructions
        await context.bot.send_message(
            chat_id=user_id,
            text="Please select an export option:\n"
                 "1. Type /export_csv for CSV\n"
                 "2. Type /export_excel for Excel\n"
                 "3. Type /export_pdf for PDF"
        )
async def show_performance_trends(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show performance trends over time"""
    user_id = get_user_id(update)
    trends = db.get_performance_trends(user_id)

    msg = """
📈 <b>Performance Trends (Last 6 Months)</b>
━━━━━━━━━━━━━━━━━━━━━━━━

<b>Applications Over Time:</b>
{applications_chart}

<b>Hire Rate Trend:</b>
{hire_rate_chart}

<b>Response Time Trend:</b>
{response_time_chart}
    """.format(
        applications_chart=generate_sparkline(trends['applications']),
        hire_rate_chart=generate_sparkline(trends['hire_rate']),
        response_time_chart=generate_sparkline(trends['response_time'], inverse=True)
    )

    await context.bot.send_message(
        chat_id=user_id,
        text=msg,
        parse_mode="HTML"
    )


def generate_sparkline(data: list, inverse: bool = False) -> str:
    """Generate text-based sparkline with robust error handling"""
    if not data or not isinstance(data, list):
        return "📊"  # Return simple placeholder

    try:
        # Extract values safely
        values = []
        for item in data:
            if isinstance(item, dict):
                value = item.get('count', item.get('rate', item.get('days', 0)))
            else:
                value = float(item) if str(item).replace('.', '', 1).isdigit() else 0
            values.append(value)

        if not values:
            return "📊"

        # Normalize to 0-10 scale
        min_val, max_val = min(values), max(values)
        if max_val == min_val:
            normalized = [5] * len(values)  # All values are equal, map to middle
        else:
            normalized = [int(10 * (v - min_val) / (max_val - min_val)) for v in values]

        # Generate sparkline
        spark_chars = ['▁', '▂', '▃', '▄', '▅', '▆', '▇', '█']
        if inverse:
            spark_chars = spark_chars[::-1]  # Reverse sparkline characters

        # Map normalized values to sparkline characters
        return ''.join(
            [spark_chars[min(len(spark_chars) - 1, max(0, v // (10 // len(spark_chars))))] for v in normalized])

    except Exception as e:
        logging.error(f"Sparkline generation error: {e}")
        return "📊"  # Fallback to simple emoji

def compare_metric(user_value: float, benchmark_value: float, lower_better: bool = False) -> str:
    """Generate comparison text for benchmarks"""
    if user_value == benchmark_value:
        return "→ Equal to industry average"
    elif (user_value > benchmark_value and not lower_better) or (user_value < benchmark_value and lower_better):
        diff = abs(user_value - benchmark_value)
        return f"↑ {diff:.1f} better than average"
    else:
        diff = abs(user_value - benchmark_value)
        return f"↓ {diff:.1f} below average"


def format_recent_responses(responses: list) -> str:
    """Format recent responses for display"""
    if not responses:
        return "No recent responses"

    formatted = []
    for resp in responses[:5]:  # Show last 5 responses
        try:
            days = resp['days']
            emoji = "🚀" if days < 3 else "🐢" if days > 7 else "⏱️"
            formatted.append(f"{emoji} {resp.get('job_title', 'Unknown Job')}: {days:.1f} days")
        except (KeyError, TypeError) as e:
            logging.error(f"Error formatting response: {e}")
            formatted.append("⚠️ Invalid response data")

    return '\n'.join(formatted)


async def show_demographics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show candidate demographics with error handling"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    try:
        demographics = db.get_candidate_demographics(user_id)

        if not demographics:
            await context.bot.send_message(
                chat_id=user_id,
                text="No demographic data available yet.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📊 Back to Analytics", callback_data="back_to_analytics")]
                ])
            )
            return ANALYTICS_VIEW

        # Generate the chart
        chart_buffer = generate_demographics_chart(demographics)

        # Send the chart
        await context.bot.send_photo(
            chat_id=user_id,
            photo=chart_buffer,
            caption=format_demographics_message(demographics),
            parse_mode="HTML"
        )

        # Close the buffer
        chart_buffer.close()

    except Exception as e:
        logging.error(f"Error in show_demographics: {e}")
        await context.bot.send_message(
            chat_id=user_id,
            text="⚠️ Could not generate demographics chart",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📊 Back to Analytics", callback_data="back_to_analytics")]
            ])
        )

    return ANALYTICS_VIEW


def format_demographics_message(data: dict) -> str:
    """Format demographics data into a nicely structured message"""
    gender_dist = data.get('gender', {})
    education_dist = data.get('education', {})
    experience_dist = data.get('experience', {})

    message = [
        "👥 <b>Candidate Demographics</b>",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        "",
        "<b>Gender Distribution:</b>",
        f"🚹 Male: {gender_dist.get('Male', 0)}%",
        f"🚺 Female: {gender_dist.get('Female', 0)}%",
        f"⚧ Other: {gender_dist.get('Other', 0)}%",
        "",
        "<b>Education Level:</b>",
        "🎓 " + format_distribution(education_dist),
        "",
        "<b>Experience Level:</b>",
        "💼 " + format_distribution(experience_dist)
    ]

    return "\n".join(message)
def format_distribution(data: dict) -> str:
    """Format distribution data for display"""
    return " | ".join([f"{k}: {v}%" for k, v in data.items()])

# Add this helper function for navigation back to analytics
async def handle_analytics_back(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle back to analytics navigation"""
    query = update.callback_query
    await query.answer()
    await view_analytics(update, context)
    return ANALYTICS_VIEW


def generate_demographics_chart(demographics: dict):
    """Generate a demographics chart image using matplotlib without file operations"""
    try:
        # Create figure with subplots
        fig, axes = plt.subplots(1, 3, figsize=(15, 5))
        fig.suptitle('Candidate Demographics Overview')

        # Gender pie chart
        if demographics.get('gender'):
            genders = list(demographics['gender'].keys())
            sizes = list(demographics['gender'].values())
            axes[0].pie(sizes, labels=genders, autopct='%1.1f%%', startangle=90)
            axes[0].set_title('Gender Distribution')

        # Education bar chart
        if demographics.get('education'):
            educations = list(demographics['education'].keys())
            values = list(demographics['education'].values())
            axes[1].bar(educations, values)
            axes[1].set_title('Education Level')
            axes[1].tick_params(axis='x', rotation=45)

        # Experience bar chart
        if demographics.get('experience'):
            experiences = list(demographics['experience'].keys())
            exp_values = list(demographics['experience'].values())
            axes[2].bar(experiences, exp_values)
            axes[2].set_title('Experience Level')
            axes[2].tick_params(axis='x', rotation=45)

        # Save to bytes buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', dpi=100)
        plt.close(fig)
        buf.seek(0)

        return buf

    except Exception as e:
        logging.error(f"Error generating demographics chart: {e}")
        plt.close('all')
        raise

from telegram import InputFile


async def handle_export_format(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle export format selection and file generation"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    export_format = query.data.split('_')[1]  # csv, pdf, or excel

    try:
        # Notify user export is starting
        await context.bot.send_message(
            chat_id=user_id,
            text=f"⏳ Preparing your {export_format.upper()} export..."
        )

        # Get analytics data
        analytics_data = db.get_employer_analytics(user_id)
        if not analytics_data:
            raise ValueError("No analytics data found")

        company_name = db.get_employer_profile(user_id).get('company_name', 'Your Company')
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')

        # Generate and send the export file
        if export_format == 'csv':
            file_data = generate_csv_export(analytics_data, company_name, timestamp)
            await context.bot.send_document(
                chat_id=user_id,
                document=InputFile(file_data, filename=f"{company_name}_Analytics_{timestamp}.csv"),
                caption=f"📊 {company_name} Analytics (CSV)"
            )
        elif export_format == 'excel':
            file_data = generate_excel_export(analytics_data, company_name, timestamp)
            await context.bot.send_document(
                chat_id=user_id,
                document=InputFile(file_data, filename=f"{company_name}_Analytics_{timestamp}.xlsx"),
                caption=f"📈 {company_name} Analytics (Excel)"
            )
        elif export_format == 'pdf':
            file_data = generate_pdf_export(analytics_data, company_name, timestamp)
            await context.bot.send_document(
                chat_id=user_id,
                document=InputFile(file_data, filename=f"{company_name}_Analytics_{timestamp}.pdf"),
                caption=f"📄 {company_name} Analytics (PDF)"
            )

        # Send completion message
        await context.bot.send_message(
            chat_id=user_id,
            text=f"✅ {export_format.upper()} export completed!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📊 Back to Analytics", callback_data="analytics_back")]  # Changed here
            ])
        )

    except Exception as e:
        logging.error(f"Export error for user {user_id}: {str(e)}", exc_info=True)
        await context.bot.send_message(
            chat_id=user_id,
            text="⚠️ Failed to generate export. Please try again later.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📊 Back to Analytics", callback_data="back_to_analytics")]
            ])
        )

    return ANALYTICS_VIEW


async def export_analytics_data(update: Update, context: ContextTypes.DEFAULT_TYPE, format: str):
    """Simplified export handler"""
    user_id = update.effective_user.id
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=f"📤 Exporting data as {format.upper()}...",
        )

        # Generate simple CSV as fallback
        if format == 'csv':
            data = "Metric,Value\nActive Vacancies,0\nTotal Applications,0"
            await context.bot.send_document(
                chat_id=user_id,
                document=io.BytesIO(data.encode()),
                filename=f"analytics_export_{datetime.now().strftime('%Y%m%d')}.csv"
            )
        else:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"⚠️ {format.upper()} export is currently unavailable",
            )

    except Exception as e:
        logging.error(f"Export error: {e}")
        await context.bot.send_message(
            chat_id=user_id,
            text="⚠️ Export failed",
        )


# async def export_analytics_data(user_id: int, data: dict, format: str):
#     """Generate analytics export in specified format"""
#     try:
#         company_name = db.get_employer_profile(user_id).get('company_name', 'YourCompany')
#         timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
#
#         if format == 'csv':
#             return await generate_csv_export(data, company_name, timestamp)
#         elif format == 'excel':
#             return await generate_excel_export(data, company_name, timestamp)
#         elif format == 'pdf':
#             return await generate_pdf_export(data, company_name, timestamp)
#         else:
#             raise ValueError(f"Unsupported export format: {format}")
#
#     except Exception as e:
#         logging.error(f"Error in export_analytics_data: {e}")
#         raise


def generate_csv_export(data: dict, company_name: str, timestamp: str) -> io.BytesIO:
    """Generate CSV export in memory"""
    buffer = io.StringIO()
    writer = csv.writer(buffer)

    # Header
    writer.writerow([f"{company_name} - Analytics Export ({timestamp})"])
    writer.writerow([])

    # Performance Metrics
    writer.writerow(["PERFORMANCE METRICS"])
    writer.writerow(["Active Vacancies", data.get('active_vacancies', 0)])
    writer.writerow(["Total Applications", data.get('total_applications', 0)])
    writer.writerow(["Hire Rate (%)", data.get('hire_rate', 0)])
    writer.writerow(["Avg Response Time (days)", data.get('avg_response_time', 0)])
    writer.writerow([])

    # Application Flow
    writer.writerow(["APPLICATION FLOW"])
    writer.writerow(["Pending Applications", data.get('pending_applications', 0)])
    writer.writerow(["Reviewed Applications", data.get('reviewed_applications', 0)])
    writer.writerow(["Approved Applications", data.get('approved_applications', 0)])
    writer.writerow(["Rejected Applications", data.get('rejected_applications', 0)])
    writer.writerow([])

    # Convert to BytesIO for Telegram
    mem_file = io.BytesIO(buffer.getvalue().encode('utf-8'))
    buffer.close()
    return mem_file


from xlsxwriter.utility import xl_range
import io


def generate_excel_export(data: dict, company_name: str, timestamp: str) -> io.BytesIO:
    """Generate advanced formatted Excel export with professional styling"""
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})

    # Create formats
    header_format = workbook.add_format({
        'bold': True,
        'font_size': 14,
        'bg_color': '#4F81BD',
        'font_color': 'white',
        'align': 'center',
        'valign': 'vcenter',
        'border': 1
    })

    title_format = workbook.add_format({
        'bold': True,
        'font_size': 20,
        'font_color': '#1F497D',
        'align': 'center',
        'valign': 'vcenter'
    })

    subtitle_format = workbook.add_format({
        'italic': True,
        'font_color': '#7F7F7F',
        'align': 'center',
        'valign': 'vcenter'
    })

    section_format = workbook.add_format({
        'bold': True,
        'font_size': 12,
        'bg_color': '#DCE6F1',
        'border': 1,
        'align': 'left',
        'valign': 'vcenter'
    })

    metric_label_format = workbook.add_format({
        'bold': True,
        'font_color': '#002060',
        'bg_color': '#F2F2F2',
        'border': 1,
        'align': 'left',
        'valign': 'vcenter'
    })

    metric_value_format = workbook.add_format({
        'num_format': '#,##0',
        'bg_color': '#FFFFFF',
        'border': 1,
        'align': 'right',
        'valign': 'vcenter'
    })

    alt_row_format = workbook.add_format({
        'bg_color': '#F8F8F8',
        'border': 1
    })

    # Add worksheet with better name
    worksheet = workbook.add_worksheet("Analytics Report")

    # Set column widths
    worksheet.set_column('A:A', 30)  # Label column
    worksheet.set_column('B:B', 15)  # Value column

    # Title section
    worksheet.merge_range('A1:B1', f"{company_name} Analytics Report", title_format)
    worksheet.merge_range('A2:B2', f"Generated on {timestamp}", subtitle_format)
    worksheet.set_row(0, 30)  # Increase title row height
    worksheet.set_row(1, 20)  # Increase subtitle row height

    # Performance Metrics section
    worksheet.write('A4', "PERFORMANCE METRICS", section_format)
    metrics = [
        ("Active Vacancies", data.get('active_vacancies', 0)),
        ("Total Applications", data.get('total_applications', 0)),
        ("Hire Rate (%)", data.get('hire_rate', 0)),
        ("Avg Response Time (days)", data.get('avg_response_time', 0))
    ]

    for row, (label, value) in enumerate(metrics, start=5):
        format = metric_label_format if row % 2 == 0 else alt_row_format
        worksheet.write(f'A{row}', label, format)
        worksheet.write(f'B{row}', value, metric_value_format)

    # Application Flow section
    worksheet.write('A9', "APPLICATION FLOW", section_format)
    flow = [
        ("Pending Applications", data.get('pending_applications', 0)),
        ("Reviewed Applications", data.get('reviewed_applications', 0)),
        ("Approved Applications", data.get('approved_applications', 0)),
        ("Rejected Applications", data.get('rejected_applications', 0))
    ]

    for row, (label, value) in enumerate(flow, start=10):
        format = metric_label_format if row % 2 == 0 else alt_row_format
        worksheet.write(f'A{row}', label, format)
        worksheet.write(f'B{row}', value, metric_value_format)

    # Add borders around all used cells
    max_row = 13  # Update based on your data length
    worksheet.conditional_format(
        f'A1:B{max_row}',
        {'type': 'formula', 'criteria': 'TRUE', 'format': workbook.add_format({'border': 1})}
    )

    # Add chart for performance metrics
    chart = workbook.add_chart({'type': 'column'})
    # In the generate_excel_export function's chart creation section:
    chart.add_series({
        'name': 'Performance Metrics',
        'categories': f"='Analytics Report'!$A$5:$A$8",  # Added quotes around sheet name
        'values': f"='Analytics Report'!$B$5:$B$8",  # Added quotes around sheet name
        'fill': {'color': '#4F81BD'},
        'data_labels': {'value': True}
    })
    chart.set_title({'name': 'Key Performance Indicators'})
    chart.set_legend({'none': True})
    worksheet.insert_chart('D4', chart)

    # Freeze panes and set zoom
    worksheet.freeze_panes(4, 1)
    worksheet.set_zoom(85)

    # Close workbook and prepare output
    workbook.close()
    output.seek(0)
    return output


from fpdf import FPDF
from fpdf.enums import XPos, YPos


def generate_pdf_export(data: dict, company_name: str, timestamp: str) -> io.BytesIO:
    """Generate PDF export in memory"""
    buffer = io.BytesIO()
    pdf = FPDF()
    pdf.add_page()

    # Set font (use Helvetica instead of Arial)
    pdf.set_font("Helvetica", size=12)

    # Header
    pdf.set_font("Helvetica", 'B', 16)
    pdf.cell(200, 10, text=f"{company_name} - Analytics Export",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
    pdf.set_font("Helvetica", '', 10)
    pdf.cell(200, 10, text=f"Generated on {timestamp}",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
    pdf.ln(10)

    # Performance Metrics
    pdf.set_font("Helvetica", 'B', 14)
    pdf.cell(200, 10, text="PERFORMANCE METRICS",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", '', 12)
    metrics = [
        ("Active Vacancies", data.get('active_vacancies', 0)),
        ("Total Applications", data.get('total_applications', 0)),
        ("Hire Rate", f"{data.get('hire_rate', 0)}%"),
        ("Avg Response Time", f"{data.get('avg_response_time', 0)} days")
    ]
    for label, value in metrics:
        pdf.cell(200, 10, text=f"{label}: {value}",
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(5)

    # Application Flow
    pdf.set_font("Helvetica", 'B', 14)
    pdf.cell(200, 10, text="APPLICATION FLOW",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", '', 12)
    flow = [
        ("Pending Applications", data.get('pending_applications', 0)),
        ("Reviewed Applications", data.get('reviewed_applications', 0)),
        ("Approved Applications", data.get('approved_applications', 0)),
        ("Rejected Applications", data.get('rejected_applications', 0))
    ]
    for label, value in flow:
        pdf.cell(200, 10, text=f"{label}: {value}",
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # Save the PDF to the buffer
    pdf.output(buffer)
    buffer.seek(0)
    return buffer

async def show_response_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Simplified response analysis"""
    await update.callback_query.answer()
    await context.bot.send_message(
        chat_id=update.effective_user.id,
        text="⏱️ Response time analysis is currently unavailable",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 Back to Analytics", callback_data="back_to_analytics")]
        ])
    )

async def show_benchmark_comparison(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Simplified benchmark view"""
    await update.callback_query.answer()
    await context.bot.send_message(
        chat_id=update.effective_user.id,
        text="🏆 Benchmark comparison is currently unavailable",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 Back to Analytics", callback_data="back_to_analytics")]
        ])
    )


from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler
import sqlite3
# Function to show the broadcast options (job seekers or employers)
async def handle_broadcast_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    keyboard = [
        [InlineKeyboardButton("Job Seekers", callback_data="job_seekers")],
        [InlineKeyboardButton("Employers", callback_data="employers")],
        [InlineKeyboardButton("Cancel", callback_data="cancel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(
        chat_id=user_id,
        text="Choose the group to broadcast the message to:",
        reply_markup=reply_markup
    )
    return BROADCAST_TYPE

# Function to handle the broadcast type selection
async def select_broadcast_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    choice = query.data

    if choice == "cancel":
        await context.bot.send_message(
            chat_id=user_id,
            text="Broadcast canceled.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

    context.user_data["broadcast_group"] = choice  # Save the selected group
    await context.bot.send_message(
        chat_id=user_id,
        text=f"Enter the message you want to broadcast to {choice}:",
        reply_markup=ReplyKeyboardRemove()
    )
    return BROADCAST_MESSAGE

# Function to handle the broadcast message input
async def get_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    message = update.message.text

    if not message.strip():
        await context.bot.send_message(
            chat_id=user_id,
            text="Message cannot be empty. Please enter a valid message:"
        )
        return BROADCAST_MESSAGE

    context.user_data["broadcast_message"] = message  # Save the message
    keyboard = [
        [InlineKeyboardButton("Yes", callback_data="confirm")],
        [InlineKeyboardButton("No", callback_data="cancel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(
        chat_id=user_id,
        text=f"Are you sure you want to broadcast the following message?\n\n{message}",
        reply_markup=reply_markup
    )
    return CONFIRM_BROADCAST

# Function to confirm and send the broadcast message
async def confirm_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    choice = query.data

    if choice == "cancel":
        # Notify the admin that the broadcast was canceled
        await context.bot.send_message(
            chat_id=user_id,
            text="Broadcast canceled.",
            reply_markup=ReplyKeyboardRemove()
        )
        # Show the admin main menu buttons
        await show_admin_menu(update, context)
        return ADMIN_MAIN_MENU  # Return to the admin main menu on cancel

    broadcast_group = context.user_data.get("broadcast_group")
    broadcast_message = context.user_data.get("broadcast_message")

    if not broadcast_group or not broadcast_message:
        # Notify the admin of an error and return to the admin main menu
        await context.bot.send_message(
            chat_id=user_id,
            text="An error occurred while processing the broadcast."
        )
        await show_admin_menu(update, context)
        return ADMIN_MAIN_MENU  # Return to the admin main menu on error

    # Broadcast the message to the selected group
    await broadcast_to_group(broadcast_group, broadcast_message, context)

    # Notify the admin that the broadcast was successful
    await context.bot.send_message(
        chat_id=user_id,
        text=f"Message has been successfully broadcasted to {broadcast_group}.",
        reply_markup=ReplyKeyboardRemove()
    )

    # Clear user data to avoid conflicts
    context.user_data.pop("broadcast_group", None)
    context.user_data.pop("broadcast_message", None)

    # Show the admin main menu buttons
    await show_admin_menu(update, context)

    # Return to the admin main menu
    return ADMIN_MAIN_MENU

# Helper function to broadcast the message to the selected group
async def broadcast_to_group(group: str, message: str, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Use the existing database connection from the 'db' object
        cursor = db.cursor  # Access the cursor from the Database instance

        # Query the appropriate table based on the group
        if group == "job_seekers":
            cursor.execute("SELECT user_id FROM users")
        elif group == "employers":
            cursor.execute("SELECT employer_id FROM employers")
        else:
            return

        # Fetch all recipient IDs
        recipients = [row[0] for row in cursor.fetchall()]

        # Send the message to each recipient
        for recipient in recipients:
            try:
                await context.bot.send_message(chat_id=recipient, text=message)
            except Exception as e:
                print(f"Failed to send message to {recipient}: {e}")

    except sqlite3.OperationalError as e:
        print(f"Database error: {e}")
        await context.bot.send_message(
            chat_id=context._chat_id,  # Assuming admin's chat ID is stored here
            text="An error occurred while broadcasting the message. Please check the database."
        )

# Function to cancel the broadcast process
async def cancel_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    await context.bot.send_message(
        chat_id=user_id,
        text="Broadcast canceled.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

#apply Vacancy Job seeker

async def display_vacancies(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)
    try:
        # Fetch and display available vacancies
        db = Database()  # Assuming Database is properly initialized
        validated_jobs = db.fetch_approved_vacancies()

        if not validated_jobs:
            await context.bot.send_message(
                chat_id=user_id,
                text=get_translation(user_id, "no_vacancies_found")
            )
            return MAIN_MENU

        # Store the fetched vacancies in user_data for later use
        context.user_data["vacancies"] = validated_jobs

        # Debug: Log the fetched vacancies and their keys
        logging.debug(f"Fetched vacancies: {validated_jobs}")
        if validated_jobs:
            logging.debug(f"Keys in first vacancy: {validated_jobs[0].keys()}")

        # Format and display vacancies with emojis and improved styling
        vacancy_list = []
        for idx, vacancy in enumerate(validated_jobs, start=1):
            # Safely access fields, defaulting to placeholders if missing
            company_name = vacancy.get("company_name", get_translation(user_id, "not_provided"))
            job_title = vacancy.get("job_title", get_translation(user_id, "title_not_available"))
            deadline = vacancy.get("deadline", get_translation(user_id, "no_deadline"))
            employment_type = vacancy.get("employment_type", get_translation(user_id, "not_specified"))
            vacancy_text = (
                f"{idx}. 🌟 <b>{get_translation(user_id, 'job_title')}:</b> {job_title}\n"
                f"   🏢 <b>{get_translation(user_id, 'employer')}:</b> {company_name}\n"
                f"   ⏳ <b>{get_translation(user_id, 'deadline')}:</b> {deadline}\n"
                f"   💼 <b>{get_translation(user_id, 'employment_type')}:</b> {employment_type}\n"
                f"{'-' * 40}"  # Separator for visual appeal
            )
            vacancy_list.append(vacancy_text)

        # Combine all vacancies into a single message
        vacancies_message = "\n".join(vacancy_list)

        # Add an introduction and prompt for selection
        intro_message = (
            f"🎉 <b>{get_translation(user_id, 'welcome_message')}</b> 🎉\n\n"
            f"{get_translation(user_id, 'vacancy_instructions')}\n\n"
        )
        prompt_message = (
            f"\n📝 <b>{get_translation(user_id, 'how_to_proceed')}:</b>\n"
            f"{get_translation(user_id, 'select_vacancy_prompt')}"
        )

        # Send the formatted list of vacancies to the user
        await context.bot.send_message(
            chat_id=user_id,
            text=intro_message + vacancies_message + prompt_message,
            parse_mode="HTML",
            # reply_markup=ForceReply(selective=True)
        )

    except ValueError as ve:
        logging.error(f"ValueError in display_vacancies: {ve}")
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "error_fetching_jobs", error=str(ve))
        )
    except Exception as e:
        logging.error(f"Unexpected error in display_vacancies: {e}")
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "unexpected_error_occurred", error=str(e))
        )
    return SELECT_VACANCY


from telegram import InlineKeyboardButton, InlineKeyboardMarkup

async def select_vacancy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)
    choice = update.message.text.strip()
    try:
        # Retrieve stored job posts
        job_posts = context.user_data.get("vacancies")

        # Debug: Log the fetched vacancies
        logging.debug(f"Fetched vacancies: {context.user_data.get('vacancies', [])}")

        if not job_posts:
            await context.bot.send_message(
                chat_id=user_id,
                text=get_translation(user_id, "no_job_selected_error")
            )
            return MAIN_MENU

        # Validate the selected index
        selected_index = int(choice) - 1
        if not (0 <= selected_index < len(job_posts)):
            raise ValueError()

        # Retrieve selected job details
        selected_job = job_posts[selected_index]

        # Debug: Log the selected job and its keys
        logging.debug(f"Selected job: {selected_job}")
        logging.debug(f"Keys in selected job: {selected_job.keys() if selected_job else 'None'}")

        # Ensure the selected job has all required fields
        required_fields = {"job_id", "job_title", "employer_id", "employment_type", "deadline", "gender", "quantity", "level",
                           "description", "qualification", "skills", "salary", "benefits"}
        missing_fields = [field for field in required_fields if field not in selected_job]
        if missing_fields:
            logging.error(f"Selected job is missing required fields: {missing_fields}")
            await context.bot.send_message(
                chat_id=user_id,
                text=get_translation(user_id, "invalid_job_data_error")
            )
            return MAIN_MENU

        # Escape special characters for safe HTML parsing
        def escape_html(text):
            return text.replace("&", "&amp;").replace("<", "<").replace(">", ">").replace("-", "&#45;")

        job_details = {key: escape_html(str(selected_job[key])) for key in required_fields}


        # Store selected job details in user_data
        context.user_data["selected_job"] = job_details

        # Generate full job details preview with enhanced HTML formatting
        preview_text = (
            f"<b>📌 {get_translation(user_id, 'job_title')}: {job_details['job_title']}</b>\n"
            f"{'_' * 40}\n"  # Replace <hr> with a line of dashes
            f"<b>🏢 {get_translation(user_id, 'employer')}</b>: {selected_job.get('company_name', 'N/A')}\n"
            f"<b>📅 {get_translation(user_id, 'deadline')}</b>: {job_details['deadline']}\n"
            f"<b>💼 {get_translation(user_id, 'employment_type')}</b>: {job_details['employment_type']}\n"
            f"<b>🚻 {get_translation(user_id, 'gender')}</b>: {job_details['gender']}\n"
            f"<b>👥 {get_translation(user_id, 'quantity')}</b>: {job_details['quantity']}\n"
            f"<b>📊 {get_translation(user_id, 'level')}</b>: {job_details['level']}\n"
            f"{'_' * 40}\n"  # Replace <hr> with a line of dashes
            f"<b>📝 {get_translation(user_id, 'description')}</b>:\n<i>{job_details['description']}</i>\n"
            f"{'_' * 40}\n"  # Replace <hr> with a line of dashes
            f"<b>🎓 {get_translation(user_id, 'qualification')}</b>:\n{job_details['qualification']}\n"
            f"{'_' * 40}\n"  # Replace <hr> with a line of dashes
            f"<b>🔑 {get_translation(user_id, 'skills')}</b>:\n{job_details['skills']}\n"
            f"{'_' * 40}\n"  # Replace <hr> with a line of dashes
            f"<b>💲 {get_translation(user_id, 'salary')}</b>: {job_details['salary']}\n"
            f"<b>🎁 {get_translation(user_id, 'benefits')}</b>:\n{job_details['benefits']}\n"
        )

        # Create inline keyboard with Confirm and Cancel buttons
        keyboard = [
            [
                InlineKeyboardButton("Confirm", callback_data="confirm"),
                InlineKeyboardButton("Cancel", callback_data="cancel")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Send the formatted message with HTML parsing and inline keyboard
        await context.bot.send_message(
            chat_id=user_id,
            text=preview_text + "\n\n" + get_translation(user_id, "confirm_selection_prompt"),
            parse_mode="HTML",
            reply_markup=reply_markup
        )

    except ValueError as ve:
        logging.error(f"ValueError in select_vacancy: {ve}")
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "invalid_selection", error=str(ve))
        )
    except Exception as e:
        logging.error(f"Unexpected error in select_vacancy: {e}")
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "unexpected_error_occurred", error=str(e))
        )
    return CONFIRM_SELECTION


async def confirm_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)
    query = update.callback_query
    await query.answer()  # Acknowledge the callback query

    choice = query.data  # Get the callback data ("confirm" or "cancel")
    try:
        # Validate that a job is selected
        selected_job = context.user_data.get("selected_job")
        if not selected_job or "job_id" not in selected_job:
            await query.edit_message_text(
                text=get_translation(user_id, "no_job_selected_error")
            )
            return MAIN_MENU

        # Handle user's choice
        if choice == "confirm":
            # Proceed to write cover letter
            await query.edit_message_text(
                text=get_translation(user_id, "write_cover_letter_prompt")
            )
            return WRITE_COVER_LETTER
        elif choice == "cancel":
            # Return to main menu and clear selected job
            await query.edit_message_text(
                text=get_translation(user_id, "selection_canceled")
            )
            context.user_data.pop("selected_job", None)
            return MAIN_MENU
    except ValueError as ve:
        logging.error(f"ValueError in confirm_selection: {ve}")
        await query.edit_message_text(
            text=get_translation(user_id, "error_invalid_selection", error=str(ve))
        )
    except Exception as e:
        logging.error(f"Unexpected error in confirm_selection: {e}")
        await query.edit_message_text(
            text=get_translation(user_id, "unexpected_error_occurred", error=str(e))
        )
    return MAIN_MENU

async def write_cover_letter(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)

    try:
        # Validate that a job is selected
        selected_job = context.user_data.get("selected_job")
        if not selected_job:
            await context.bot.send_message(
                chat_id=user_id,
                text=get_translation(user_id, "no_job_selected_error")
            )
            return MAIN_MENU

        # Check if user has already applied for this job
        if db.has_user_applied(user_id, selected_job["job_id"]):
            await context.bot.send_message(
                chat_id=user_id,
                text=get_translation(user_id, "already_applied_error")
            )
            context.user_data.pop("selected_job", None)
            return await main_menu(update, context)

        # Fetch and validate cover letter
        cover_letter = update.message.text.strip()
        if not cover_letter:
            await context.bot.send_message(
                chat_id=user_id,
                text=get_translation(user_id, "cover_letter_empty_error")
            )
            return WRITE_COVER_LETTER

        # Save application in the database
        db.save_application(user_id, selected_job["job_id"], cover_letter)

        # Notify the user that the application was submitted
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "application_submitted_successfully")
        )

        # Show the submitted cover letter to the user
        await context.bot.send_message(
            chat_id=user_id,
            text=f"*Your Cover Letter:*\n\n{cover_letter}",
            parse_mode="Markdown"
        )

        # Forward the application to the employer
        employer_id = selected_job["employer_id"]
        await forward_application_to_employer(employer_id, user_id, context)

        # Clear user data to avoid conflicts
        context.user_data.pop("selected_job", None)

        return MAIN_MENU

    except ValueError as ve:
        logging.error(f"ValueError in write_cover_letter: {ve}")
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "error_invalid_selection", error=str(ve))
        )
    except Exception as e:
        logging.error(f"Unexpected error in write_cover_letter: {e}")
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "unexpected_error_occurred", error=str(e))
        )

async def forward_application_to_employer(employer_id: int, job_seeker_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Forward the application to the employer."""
    try:
        # Fetch job seeker's profile as a formatted message
        profile_message = await display_user_profile(job_seeker_id, context)

        # Fetch job seeker's cover letter
        selected_job = context.user_data.get("selected_job")
        if not selected_job:
            raise ValueError("No job selected.")
        cover_letter = db.get_cover_letter_for_job(job_seeker_id, selected_job["job_id"])

        # Send the application details to the employer
        await context.bot.send_message(
            chat_id=employer_id,
            text=(
                f"*New Job Application Received*\n\n"
                f"You have received a new application for a job you posted. "
                f"To review the applicant's details and take action, visit the *Manage Vacancies* section in your dashboard.\n\n"
                # f"New application received for job ID {selected_job['job_id']}:\n\n"
                # f"{profile_message}\n\n"
                # f"Cover Letter:\n{cover_letter or 'No cover letter provided.'}"
            ),
            parse_mode="Markdown"
        )
    except ValueError as ve:
        logging.error(f"ValueError in forward_application_to_employer: {ve}")
        await context.bot.send_message(
            chat_id=job_seeker_id,
            text=get_translation(job_seeker_id, "error_invalid_selection", error=str(ve))
        )
    except Exception as e:
        logging.error(f"Error forwarding application to employer: {e}")
        await context.bot.send_message(
            chat_id=job_seeker_id,
            text=get_translation(job_seeker_id, "unexpected_error_occurred", error=str(e))
        )


async def confirm_application(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)
    cover_letter = update.message.text.strip()

    try:
        # Validate that a job is selected
        selected_job = context.user_data.get("selected_job")
        if not selected_job:
            await context.bot.send_message(
                chat_id=user_id,
                text=get_translation(user_id, "no_job_selected_error")
            )
            return MAIN_MENU

        # Validate cover letter
        if not cover_letter:
            await context.bot.send_message(
                chat_id=user_id,
                text=get_translation(user_id, "cover_letter_empty_error")
            )
            return WRITE_COVER_LETTER

        # Store cover letter in user_data
        context.user_data["cover_letter"] = cover_letter

        # Confirm submission with inline buttons
        keyboard = [
            [InlineKeyboardButton(get_translation(user_id, "confirm_button"), callback_data="confirm")],
            [InlineKeyboardButton(get_translation(user_id, "cancel_button"), callback_data="cancel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "confirm_submission_prompt"),
            reply_markup=reply_markup
        )
    except ValueError as ve:
        logging.error(f"ValueError in confirm_application: {ve}")
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "error_invalid_selection", error=str(ve))
        )
    except Exception as e:
        logging.error(f"Unexpected error in confirm_application: {e}")
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "unexpected_error_occurred", error=str(e))
        )
    return CONFIRM_SUBMISSION


async def handle_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    action = query.data

    try:
        # Validate that a job is selected
        selected_job = context.user_data.get("selected_job")
        if not selected_job:
            await context.bot.send_message(
                chat_id=user_id,
                text=get_translation(user_id, "no_job_selected_error")
            )
            return MAIN_MENU

        # Check if user has already applied for this job
        if db.has_user_applied(user_id, selected_job["job_id"]):
            await context.bot.send_message(
                chat_id=user_id,
                text=get_translation(user_id, "already_applied_error")
            )
            context.user_data.pop("selected_job", None)
            context.user_data.pop("cover_letter", None)
            return MAIN_MENU

        # Validate that a cover letter is provided
        cover_letter = context.user_data.get("cover_letter")
        if not cover_letter:
            await context.bot.send_message(
                chat_id=user_id,
                text=get_translation(user_id, "cover_letter_empty_error")
            )
            return WRITE_COVER_LETTER

        # Handle user's action
        if action == "confirm":
            # Save application in the database
            db.save_application(user_id, selected_job["job_id"], cover_letter)

            # Notify the user that the application was submitted
            await context.bot.send_message(
                chat_id=user_id,
                text=get_translation(user_id, "application_submitted_successfully")
            )

            # Forward the application to the employer
            employer_id = selected_job["employer_id"]
            await forward_application_to_employer(employer_id, user_id, context)

            # Clear user data after submission
            context.user_data.pop("selected_job", None)
            context.user_data.pop("cover_letter", None)
            return MAIN_MENU

        elif action == "cancel":
            # Cancel submission and return to main menu
            await context.bot.send_message(
                chat_id=user_id,
                text=get_translation(user_id, "submission_canceled")
            )
            context.user_data.pop("selected_job", None)  # Clear selected job
            context.user_data.pop("cover_letter", None)  # Clear cover letter
            return MAIN_MENU

        else:
            # Invalid action
            await context.bot.send_message(
                chat_id=user_id,
                text=get_translation(user_id, "invalid_action_error")
            )
            return CONFIRM_SUBMISSION

    except ValueError as ve:
        logging.error(f"ValueError in handle_confirmation: {ve}")
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "error_invalid_selection", error=str(ve))
        )
    except Exception as e:
        logging.error(f"Unexpected error in handle_confirmation: {e}")
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "unexpected_error_occurred", error=str(e))
        )
    return MAIN_MENU

# async def fetch_and_display_vacancies(user_id, context):
#     try:
#         # Fetch approved vacancies from the database
#         db = Database()  # Assuming Database is properly initialized
#         vacancies = db.fetch_approved_vacancies()
#
#         if not vacancies:
#             return []
#
#         # Return the vacancies as a list of dictionaries
#         return vacancies
#
#     except Exception as e:
#         logging.error(f"Error fetching vacancies: {e}")
#         raise

#search vaccancies

async def start_job_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Initiate the job search process with filter options."""
    user_id = get_user_id(update)

    # Create an attractive intro message
    intro_message = (
        f"🔍 <b>{get_translation(user_id, 'advanced_job_search')}</b> 🔍\n\n"
        f"{get_translation(user_id, 'search_intro_message')}\n\n"
        f"✨ {get_translation(user_id, 'search_tip_message')}"
    )

    # Create inline keyboard with search options
    keyboard = [
        [
            InlineKeyboardButton(get_translation(user_id, "search_by_keyword"), callback_data="search_by_keyword"),
            InlineKeyboardButton(get_translation(user_id, "advanced_filters"), callback_data="advanced_filters")
        ],
        [
            InlineKeyboardButton(get_translation(user_id, "quick_search_recent"), callback_data="quick_search_recent"),
            InlineKeyboardButton(get_translation(user_id, "quick_search_high_paying"),
                                 callback_data="quick_search_high_paying")
        ],
        [
            InlineKeyboardButton(get_translation(user_id, "cancel_search"), callback_data="cancel_search")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(
        chat_id=user_id,
        text=intro_message,
        parse_mode="HTML",
        reply_markup=reply_markup
    )

    return SEARCH_OPTIONS


async def handle_search_options(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the user's choice of search method."""
    query = update.callback_query
    await query.answer()
    user_id = get_user_id(update)

    choice = query.data

    if choice == "search_by_keyword":
        await query.edit_message_text(
            text=get_translation(user_id, "enter_keyword_prompt"),
            parse_mode="HTML"
        )
        context.user_data["search_type"] = "keyword"
        return KEYWORD_SEARCH

    elif choice == "advanced_filters":
        return await display_advanced_filters(update, context)

    elif choice == "quick_search_recent":
        context.user_data["search_filters"] = {"sort_by": "newest"}
        return await perform_search(update, context)

    elif choice == "quick_search_high_paying":
        context.user_data["search_filters"] = {"sort_by": "salary_desc"}
        return await perform_search(update, context)

    elif choice == "cancel_search":
        await query.edit_message_text(
            text=get_translation(user_id, "search_cancelled"),
            parse_mode="HTML"
        )
        return MAIN_MENU

    return SEARCH_OPTIONS


async def display_advanced_filters(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Display a menu of advanced filter options."""
    user_id = get_user_id(update)

    # Create a message explaining the filters
    filter_explanation = (
        f"⚙️ <b>{get_translation(user_id, 'advanced_filters_title')}</b> ⚙️\n\n"
        f"{get_translation(user_id, 'filter_explanation')}\n\n"
        f"📌 {get_translation(user_id, 'current_filters')}:\n"
    )

    # Get current filters if any
    current_filters = context.user_data.get("search_filters", {})
    if not current_filters:
        filter_explanation += get_translation(user_id, "no_filters_applied")
    else:
        for key, value in current_filters.items():
            filter_explanation += f"• {key}: {value}\n"

    # Create filter buttons
    keyboard = [
        [InlineKeyboardButton(get_translation(user_id, "filter_job_type"), callback_data="filter_job_type")],
        [InlineKeyboardButton(get_translation(user_id, "filter_salary"), callback_data="filter_salary")],
        [InlineKeyboardButton(get_translation(user_id, "filter_experience"), callback_data="filter_experience")],
        [
            InlineKeyboardButton(get_translation(user_id, "apply_filters"), callback_data="apply_filters"),
            InlineKeyboardButton(get_translation(user_id, "clear_filters"), callback_data="clear_filters")
        ],
        [InlineKeyboardButton(get_translation(user_id, "back_to_search"), callback_data="back_to_search")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Handle both callback queries and regular messages
    if hasattr(update, 'callback_query') and update.callback_query:
        # Edit existing message if coming from callback
        await update.callback_query.edit_message_text(
            text=filter_explanation,
            parse_mode="HTML",
            reply_markup=reply_markup
        )
    else:
        # Send new message if coming from regular message
        await context.bot.send_message(
            chat_id=user_id,
            text=filter_explanation,
            parse_mode="HTML",
            reply_markup=reply_markup
        )

    return ADVANCED_FILTERS

async def filter_job_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle job type filter selection."""
    user_id = get_user_id(update)

    keyboard = [
        [InlineKeyboardButton(get_translation(user_id, "full_time"), callback_data="job_type_full_time")],
        [InlineKeyboardButton(get_translation(user_id, "part_time"), callback_data="job_type_part_time")],
        [InlineKeyboardButton(get_translation(user_id, "freelance"), callback_data="job_type_freelance")],
        [InlineKeyboardButton(get_translation(user_id, "remote"), callback_data="job_type_remote")],
        [InlineKeyboardButton(get_translation(user_id, "hybrid"), callback_data="job_type_hybrid")],
        [InlineKeyboardButton(get_translation(user_id, "back_to_filters"), callback_data="back_to_filters")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.callback_query.edit_message_text(
        text=get_translation(user_id, "select_job_type_prompt"),
        parse_mode="HTML",
        reply_markup=reply_markup
    )

    return FILTER_JOB_TYPE


async def perform_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Perform the actual search based on filters."""
    user_id = get_user_id(update)
    search_filters = context.user_data.get("search_filters", {})

    try:
        db = Database()

        # Base query
        query = """
            SELECT v.id AS job_id, v.job_title, v.employment_type, v.gender, v.quantity, v.level,
                   v.description, v.qualification, v.skills, v.salary, v.benefits,
                   v.application_deadline AS deadline,
                   e.company_name, v.employer_id, v.status, 'vacancy' AS source
            FROM vacancies v
            JOIN employers e ON v.employer_id = e.employer_id
            WHERE v.status = 'approved'
        """

        params = []

        # Apply filters - updated to match posting format
        if "job_type" in search_filters:
            # Map search filter to posted job types
            type_mapping = {
                "full_time": "full_time",
                "part_time": "part_time",
                "freelance": "freelance",
                "remote": "remote",
                "hybrid": "hybrid"
            }
            query += " AND v.employment_type = ?"
            params.append(type_mapping.get(search_filters["job_type"], search_filters["job_type"]))

        if "min_salary" in search_filters:
            # Handle salary format matching (remove currency symbols, commas)
            query += """ AND CAST(REPLACE(REPLACE(REPLACE(v.salary, '$', ''), ',', ''), ' ', '') AS INTEGER) >= ?"""
            params.append(int(search_filters["min_salary"]))

        if "max_salary" in search_filters:
            query += """ AND CAST(REPLACE(REPLACE(REPLACE(v.salary, '$', ''), ',', ''), ' ', '') AS INTEGER) <= ?"""
            params.append(int(search_filters["max_salary"]))

        if "experience_level" in search_filters:
            # Map search filter to posted levels
            level_mapping = {
                "entry": "entry_level",
                "mid": "mid_level",
                "senior": "senior_level"
            }
            query += " AND v.level = ?"
            params.append(level_mapping.get(search_filters["experience_level"], search_filters["experience_level"]))

        # Sorting
        if search_filters.get("sort_by") == "newest":
            query += " ORDER BY v.id DESC"
        elif search_filters.get("sort_by") == "salary_desc":
            query += " ORDER BY CAST(REPLACE(REPLACE(REPLACE(v.salary, '$', ''), ',', ''), ' ', '') AS INTEGER) DESC"
        else:
            query += " ORDER BY v.application_deadline ASC"

        # Execute query
        db.cursor.execute(query, params)
        results = db.cursor.fetchall()
        jobs = [dict(row) for row in results]

        if not jobs:
            message = get_translation(user_id, "no_jobs_found_with_filters")
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    text=message,
                    parse_mode="HTML"
                )
            else:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=message,
                    parse_mode="HTML"
                )
            return await display_advanced_filters(update, context)

        # Store results and display
        context.user_data["search_results"] = jobs
        return await display_search_results(update, context, jobs)

    except Exception as e:
        logging.error(f"Error performing search: {e}")
        message = get_translation(user_id, "search_error_message")
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text=message,
                parse_mode="HTML"
            )
        else:
            await context.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode="HTML"
            )
        return MAIN_MENU


async def display_search_results(update: Update, context: ContextTypes.DEFAULT_TYPE, jobs: list) -> int:
    """Display the search results in an attractive format."""
    user_id = get_user_id(update)

    # Prepare the results message
    results_message = f"🎯 <b>{get_translation(user_id, 'search_results_title')}</b> 🎯\n\n"
    results_message += f"📊 {get_translation(user_id, 'jobs_found')}: {len(jobs)}\n\n"

    # Show all jobs if coming from view_all_results, otherwise first 10
    display_jobs = jobs if len(jobs) <= 10 or context.user_data.get("showing_all_results") else jobs[:10]

    # Add each job to the message
    for idx, job in enumerate(display_jobs, start=1):
        results_message += (
            f"<b>{idx}. {job['job_title']}</b>\n"
            f"🏢 {job['company_name']}\n"
            f"💰 {job.get('salary', get_translation(user_id, 'salary_not_specified'))}\n"
            f"⏱ {job['employment_type']} | 📅 {job['deadline']}\n"
            f"📌 {job['level']}\n\n"
        )

    # Create action buttons
    keyboard = []
    if len(jobs) > 10 and not context.user_data.get("showing_all_results"):
        keyboard.append([InlineKeyboardButton(
            get_translation(user_id, "view_all_results"),
            callback_data="view_all_results")
        ])
        context.user_data["showing_all_results"] = False  # Reset flag

    keyboard.extend([
        [InlineKeyboardButton(
            get_translation(user_id, "refine_search"),
            callback_data="refine_search")
        ],
        [InlineKeyboardButton(
            get_translation(user_id, "new_search"),
            callback_data="new_search")
        ],
        [InlineKeyboardButton(
            get_translation(user_id, "back_to_main"),
            callback_data="back_to_main")
        ]
    ])

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Send or edit the message
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text=results_message,
            parse_mode="HTML",
            reply_markup=reply_markup
        )
    else:
        await context.bot.send_message(
            chat_id=user_id,
            text=results_message,
            parse_mode="HTML",
            reply_markup=reply_markup
        )

    return SEARCH_RESULTS

async def handle_keyword_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle keyword search input from user."""
    user_id = get_user_id(update)
    keyword = update.message.text.strip()

    if not keyword:
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "empty_keyword_error")
        )
        return KEYWORD_SEARCH

    # Store keyword and perform search
    context.user_data["search_filters"] = {"keyword": keyword}
    return await perform_search(update, context)


async def handle_advanced_filters(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle selections from the advanced filters menu."""
    query = update.callback_query
    await query.answer()
    user_id = get_user_id(update)

    choice = query.data

    if choice == "filter_job_type":
        return await filter_job_type(update, context)
    elif choice == "filter_salary":
        await query.edit_message_text(
            text=get_translation(user_id, "enter_salary_range_prompt"),
            parse_mode="HTML"
        )
        return FILTER_SALARY
    elif choice == "filter_experience":
        return await display_experience_levels(update, context)

    elif choice == "apply_filters":
        return await perform_search(update, context)
    elif choice == "clear_filters":
        context.user_data.pop("search_filters", None)
        return await display_advanced_filters(update, context)
    elif choice == "back_to_search":
        return await start_job_search(update, context)

    return ADVANCED_FILTERS


async def handle_job_type_filter(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle job type filter selection."""
    query = update.callback_query
    await query.answer()
    user_id = get_user_id(update)

    choice = query.data

    if choice.startswith("job_type_"):
        job_type = choice.replace("job_type_", "")
        # Map to posting format
        type_mapping = {
            "full_time": "full_time",
            "part_time": "part_time",
            "freelance": "freelance",
            "remote": "remote",
            "hybrid": "hybrid"
        }
        filtered_type = type_mapping.get(job_type, job_type)

        if "search_filters" not in context.user_data:
            context.user_data["search_filters"] = {}
        context.user_data["search_filters"]["job_type"] = filtered_type

        await query.edit_message_text(
            text=get_translation(user_id, "job_type_set_success", job_type=job_type.replace("_", " ")),
            parse_mode="HTML"
        )
        return await display_advanced_filters(update, context)
    elif choice == "back_to_filters":
        return await display_advanced_filters(update, context)

    return FILTER_JOB_TYPE


async def handle_experience_filter(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle experience level selection."""
    query = update.callback_query
    await query.answer()
    user_id = get_user_id(update)

    choice = query.data

    if choice.startswith("exp_"):
        exp_level = choice.replace("exp_", "")
        # Map to posting format
        level_mapping = {
            "entry": "entry_level",
            "mid": "mid_level",
            "senior": "senior_level"
        }
        filtered_level = level_mapping.get(exp_level, exp_level)

        if "search_filters" not in context.user_data:
            context.user_data["search_filters"] = {}
        context.user_data["search_filters"]["experience_level"] = filtered_level

        await query.edit_message_text(
            text=get_translation(user_id, "experience_level_set_success", level=exp_level.replace("_", " ")),
            parse_mode="HTML"
        )
        return await display_advanced_filters(update, context)
    elif choice == "back_to_filters":
        return await display_advanced_filters(update, context)

    return FILTER_EXPERIENCE


async def handle_salary_filter(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle salary range input from user."""
    user_id = get_user_id(update)
    salary_input = update.message.text.strip()

    try:
        # Parse salary range (format: "min-max" or "min" or "max+")
        if "-" in salary_input:
            min_salary, max_salary = map(str.strip, salary_input.split("-"))
            min_salary = int(''.join(filter(str.isdigit, min_salary)))
            max_salary = int(''.join(filter(str.isdigit, max_salary)))
        elif "+" in salary_input:
            min_salary = int(''.join(filter(str.isdigit, salary_input.replace("+", ""))))
            max_salary = 999999  # Arbitrary large number
        else:
            min_salary = int(''.join(filter(str.isdigit, salary_input)))
            max_salary = min_salary  # Exact amount

        if min_salary > max_salary:
            raise ValueError("Min salary cannot be greater than max salary")

        # Store in filters
        if "search_filters" not in context.user_data:
            context.user_data["search_filters"] = {}
        context.user_data["search_filters"]["min_salary"] = min_salary
        context.user_data["search_filters"]["max_salary"] = max_salary

        # Send confirmation message
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "salary_range_set_success",
                                 min_salary=min_salary, max_salary=max_salary),
            parse_mode="HTML"
        )

        # Return to filters menu with proper update context
        return await display_advanced_filters(update, context)

    except ValueError as e:
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "invalid_salary_format_error"),
            parse_mode="HTML"
        )
        return FILTER_SALARY


async def display_experience_levels(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Display experience level options to user."""
    user_id = get_user_id(update)

    keyboard = [
        [InlineKeyboardButton(get_translation(user_id, "entry_level"), callback_data="exp_entry")],
        [InlineKeyboardButton(get_translation(user_id, "mid_level"), callback_data="exp_mid")],
        [InlineKeyboardButton(get_translation(user_id, "senior_level"), callback_data="exp_senior")],
        [InlineKeyboardButton(get_translation(user_id, "back_to_filters"), callback_data="back_to_filters")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.callback_query.edit_message_text(
        text=get_translation(user_id, "select_experience_level_prompt"),
        parse_mode="HTML",
        reply_markup=reply_markup
    )
    return FILTER_EXPERIENCE


async def handle_experience_filter(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle experience level selection."""
    query = update.callback_query
    await query.answer()
    user_id = get_user_id(update)

    choice = query.data

    if choice.startswith("exp_"):
        exp_level = choice.replace("exp_", "")
        if "search_filters" not in context.user_data:
            context.user_data["search_filters"] = {}
        context.user_data["search_filters"]["experience_level"] = exp_level
        await query.edit_message_text(
            text=get_translation(user_id, "experience_level_set_success", level=exp_level),
            parse_mode="HTML"
        )
        return await display_advanced_filters(update, context)
    elif choice == "back_to_filters":
        return await display_advanced_filters(update, context)

    return FILTER_EXPERIENCE


async def handle_search_results(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle actions from search results view."""
    query = update.callback_query
    await query.answer()
    user_id = get_user_id(update)

    choice = query.data

    if choice == "view_all_results":
        # Pass all results without limiting to 10
        return await display_search_results(update, context, context.user_data["search_results"])
    elif choice == "refine_search":
        return await display_advanced_filters(update, context)
    elif choice == "new_search":
        context.user_data.pop("search_filters", None)
        context.user_data.pop("search_results", None)
        return await start_job_search(update, context)
    elif choice == "back_to_main":
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text=get_translation(user_id, "returning_to_main_menu"),
                parse_mode="HTML"
            )
        else:
            await context.bot.send_message(
                chat_id=user_id,
                text=get_translation(user_id, "returning_to_main_menu"),
                parse_mode="HTML"
            )
        return MAIN_MENU
    elif choice.startswith("view_job_"):
        job_index = int(choice.replace("view_job_", ""))
        return await display_job_details(update, context, job_index)

    return SEARCH_RESULTS


async def display_job_details(update: Update, context: ContextTypes.DEFAULT_TYPE, job_index: int) -> int:
    """Display detailed view of a specific job."""
    user_id = get_user_id(update)
    jobs = context.user_data.get("search_results", [])

    if not jobs or job_index < 0 or job_index >= len(jobs):
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translation(user_id, "invalid_job_selection_error"),
            parse_mode="HTML"
        )
        return SEARCH_RESULTS

    job = jobs[job_index]

    # Format job details (similar to your existing job display format)
    details = (
        f"<b>📌 {get_translation(user_id, 'job_title')}:</b> {job['job_title']}\n"
        f"🏢 <b>{get_translation(user_id, 'employer')}:</b> {job.get('company_name', 'N/A')}\n"
        f"📅 <b>{get_translation(user_id, 'deadline')}:</b> {job['deadline']}\n"
        f"💼 <b>{get_translation(user_id, 'employment_type')}:</b> {job['employment_type']}\n"
        f"💰 <b>{get_translation(user_id, 'salary')}:</b> {job.get('salary', get_translation(user_id, 'not_specified'))}\n\n"
        f"<b>📝 {get_translation(user_id, 'description')}:</b>\n{job['description']}\n\n"
        f"<b>🎓 {get_translation(user_id, 'qualification')}:</b>\n{job['qualification']}\n\n"
        f"<b>🔑 {get_translation(user_id, 'skills')}:</b>\n{job['skills']}"
    )

    # Create action buttons
    keyboard = [
        [InlineKeyboardButton(get_translation(user_id, "back_to_results"), callback_data="back_to_results")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:  # Check if this is a callback query update
        await update.callback_query.edit_message_text(
            text=details,
            parse_mode="HTML",
            reply_markup=reply_markup
        )
    else:  # Fallback for non-callback updates
        await context.bot.send_message(
            chat_id=user_id,
            text=details,
            parse_mode="HTML",
            reply_markup=reply_markup
        )

    return VIEW_JOB_DETAILS


async def handle_job_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle actions from job details view."""
    query = update.callback_query
    await query.answer()
    user_id = get_user_id(update)

    choice = query.data

    if choice == "back_to_results":
        return await display_search_results(update, context, context.user_data["search_results"])

    return VIEW_JOB_DETAILS

#remove buttons
async def remove_job_seekers(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = get_user_id(update)

    # Prompt for search term with clearer instructions
    await context.bot.send_message(
        chat_id=user_id,
        text="Enter search term (name, ID, or leave empty for all). Example: 'John' or '12345':"
    )
    return SEARCH_JOB_SEEKERS

async def handle_job_seeker_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    search_term = update.message.text.strip()
    context.user_data["search_term"] = search_term
    page = 1  # Start from the first page

    try:
        # Fetch paginated results
        job_seekers = db.search_job_seekers(search_term, page=page)
        total_pages = db.get_total_pages_job_seekers(search_term)

        if not job_seekers:
            await context.bot.send_message(
                chat_id=user_id,
                text="No matching job seekers found."
            )
            return await back_to_database_menu(update, context)

        # Create paginated keyboard
        keyboard = create_paginated_keyboard(job_seekers, page, total_pages, "job_seeker")
        keyboard.append([InlineKeyboardButton("Back", callback_data="back_to_manage_users")])

        await context.bot.send_message(
            chat_id=user_id,
            text=f"Results for '{search_term}' (Page {page}/{total_pages}):",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logging.error(f"Error handling job seeker search: {e}")
        await context.bot.send_message(
            chat_id=user_id,
            text="An error occurred while fetching job seekers. Please try again later."
        )
        return await back_to_database_menu(update, context)

    return REMOVE_JOB_SEEKERS_PAGINATED

def create_paginated_keyboard(items, current_page, total_pages, entity_type):
    keyboard = []
    # Add item buttons
    for item in items:
        if entity_type == "job_seeker":
            text = f"{item['full_name']} (ID: {item['user_id']})"
            callback_data = f"remove_seeker_{item['user_id']}"
        elif entity_type == "employer":
            text = f"{item['company_name']} (ID: {item['employer_id']})"
            callback_data = f"remove_employer_{item['employer_id']}"
        elif entity_type == "application":
            text = f"{item['job_title']} - {item['full_name']} (ID: {item['application_id']})"
            callback_data = f"remove_application_{item['application_id']}"
        elif entity_type == "job":
            text = f"{item['full_name']} (ID: {item['user_id']})"
            callback_data = f"remove_seeker_{item['user_id']}"
        elif entity_type == "vacancy":
            text = f"{item['job_title']} (ID: {item['id']})"
            callback_data = f"remove_vacancy_{item['id']}"

        # Add other entity types here...
        else:
            continue  # Skip unsupported entity types
        keyboard.append([InlineKeyboardButton(text, callback_data=callback_data)])

    # Add pagination buttons
    nav_buttons = []
    if current_page > 1:
        nav_buttons.append(InlineKeyboardButton("⬅ Prev", callback_data=f"prev_{entity_type}_{current_page}"))
    if current_page < total_pages:
        nav_buttons.append(InlineKeyboardButton("Next ➡", callback_data=f"next_{entity_type}_{current_page}"))

    if nav_buttons:
        keyboard.append(nav_buttons)

    return keyboard

async def handle_pagination(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data.split("_")

    # Validate data structure
    if len(data) != 3:
        await query.edit_message_text("Invalid action.")
        return await back_to_database_menu(update, context)

    action, entity_type, current_page = data
    current_page = int(current_page)
    search_term = context.user_data.get("search_term", "")

    # Calculate new page
    new_page = current_page + 1 if action == "next" else current_page - 1

    try:
        if entity_type == "job_seeker":
            items = db.search_job_seekers(search_term, new_page)
            total_pages = db.get_total_pages_job_seekers(search_term)
        elif entity_type == "employer":
            items = db.search_employers(search_term, new_page)
            total_pages = db.get_total_pages_employers(search_term)
        elif entity_type == "application":
            items = db.search_applications(search_term, new_page)
            total_pages = db.get_total_pages_applications(search_term)
        elif entity_type == "job":
            items = db.search_jobs(search_term, new_page)
            total_pages = db.get_total_pages_jobs(search_term)
        elif entity_type == "vacancy":
            items = db.search_vacancies(search_term, new_page)
            total_pages = db.get_total_pages_vacancies(search_term)
        # Add other entity types here...
        else:
            raise ValueError("Unsupported entity type.")

        keyboard = create_paginated_keyboard(items, new_page, total_pages, entity_type)
        keyboard.append([InlineKeyboardButton("Back", callback_data="back_to_manage_users")])

        await query.edit_message_text(
            text=f"Results for '{search_term}' (Page {new_page}/{total_pages}):",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logging.error(f"Error handling pagination: {e}")
        await query.edit_message_text("An error occurred while fetching results. Please try again later.")
        return await back_to_database_menu(update, context)

    return REMOVE_JOB_SEEKERS_PAGINATED

import asyncio
from threading import Lock
import logging

# Define a lock
notification_lock = Lock()

import asyncio
from threading import Lock
import logging

# Define a lock
notification_lock = Lock()

async def handle_notifications(context):
    if not notification_lock.acquire(blocking=False):  # Try to acquire the lock
        logging.debug("Notification handler is already running. Skipping this execution.")
        return

    try:
        # Fetch and process up to 5 notifications at a time
        notifications = db.fetch_notifications(limit=3)
        if notifications:
            for notification in notifications:
                user_id = notification["user_id"]
                action = notification["action"]

                if action == "removed":
                    await context.bot.send_message(
                        chat_id=user_id,
                        text="You have been removed by Admin. Please restart by clicking /start."
                    )

            # Clear processed notifications after batch processing
            db.clear_notifications(limit=3)

    except Exception as e:
        logging.error(f"Error handling notifications: {e}")

    finally:
        notification_lock.release()  # Release the lock when done




async def remove_employers(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = get_user_id(update)

    # Prompt for search term with clearer instructions
    await context.bot.send_message(
        chat_id=user_id,
        text="Enter search term (company name, ID, or leave empty for all). Example: 'TechCorp' or '12345':"
    )
    return SEARCH_EMPLOYERS


async def handle_employer_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    search_term = update.message.text.strip()
    context.user_data["search_term"] = search_term
    page = 1  # Start from the first page

    try:
        # Fetch paginated results
        employers = db.search_employers(search_term, page=page)
        total_pages = db.get_total_pages_employers(search_term)

        if not employers:
            await context.bot.send_message(
                chat_id=user_id,
                text="No matching employers found."
            )
            return await back_to_database_menu(update, context)

        # Create paginated keyboard
        keyboard = create_paginated_keyboard(employers, page, total_pages, "employer")
        keyboard.append([InlineKeyboardButton("Back", callback_data="back_to_manage_users")])

        await context.bot.send_message(
            chat_id=user_id,
            text=f"Results for '{search_term}' (Page {page}/{total_pages}):",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logging.error(f"Error handling employer search: {e}")
        await context.bot.send_message(
            chat_id=user_id,
            text="An error occurred while fetching employers. Please try again later."
        )
        return await back_to_database_menu(update, context)

    return REMOVE_EMPLOYERS_PAGINATED


async def remove_applications(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = get_user_id(update)

    # Prompt for search term with clearer instructions
    await context.bot.send_message(
        chat_id=user_id,
        text="Enter search term (job title, seeker name, or leave empty for all). Example: 'Software Engineer' or 'John Doe':"
    )
    return SEARCH_APPLICATIONS


async def handle_application_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    search_term = update.message.text.strip()
    context.user_data["search_term"] = search_term
    page = 1  # Start from the first page

    try:
        # Fetch paginated results
        applications = db.search_applications(search_term, page=page)
        total_pages = db.get_total_pages_applications(search_term)

        if not applications:
            await context.bot.send_message(
                chat_id=user_id,
                text="No matching applications found."
            )
            return await back_to_database_menu(update, context)

        # Create paginated keyboard
        keyboard = create_paginated_keyboard(applications, page, total_pages, "application")
        keyboard.append([InlineKeyboardButton("Back", callback_data="back_to_manage_users")])

        await context.bot.send_message(
            chat_id=user_id,
            text=f"Results for '{search_term}' (Page {page}/{total_pages}):",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logging.error(f"Error handling application search: {e}")
        await context.bot.send_message(
            chat_id=user_id,
            text="An error occurred while fetching applications. Please try again later."
        )
        return await back_to_database_menu(update, context)

    return REMOVE_APPLICATIONS_PAGINATED

async def list_applications(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    page = 1
    search_term = ""  # Default search term for all applications

    try:
        applications = db.search_applications(search_term, page)
        total_pages = db.get_total_pages_applications(search_term)

        if not applications:
            await context.bot.send_message(
                chat_id=user_id,
                text="No applications found."
            )
            return await back_to_database_menu(update, context)

        keyboard = create_paginated_keyboard(applications, page, total_pages, "application_list")
        keyboard.append([InlineKeyboardButton("Back", callback_data="back_to_manage_applications")])

        await context.bot.send_message(
            chat_id=user_id,
            text=f"Applications (Page {page}/{total_pages}):",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logging.error(f"Error listing applications: {e}")
        await context.bot.send_message(
            chat_id=user_id,
            text="An error occurred while fetching applications. Please try again later."
        )
        return await back_to_database_menu(update, context)

    return LIST_APPLICATIONS_PAGINATED

async def remove_jobs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle job removal with search/pagination"""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id

    # Prompt for search term with clearer instructions
    await context.bot.send_message(
        chat_id=user_id,
        text="Enter search term (job title, employer name, or leave empty for all). Example: 'Software Engineer' or 'TechCorp':"
    )
    return SEARCH_JOBS


async def export_jobs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Export jobs to a professionally formatted Excel file."""
    user_id = update.effective_user.id
    jobs = db.get_all_job_posts()  # Fetch all job posts

    if not jobs:
        await context.bot.send_message(chat_id=user_id, text="No jobs found.")
        return

    # Convert to DataFrame
    df = pd.DataFrame(jobs)

    # Handle missing values
    df.fillna("Not provided", inplace=True)

    # Create Excel workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Jobs"

    # Title section
    ws.merge_cells("A1:O2")
    title = ws.cell(row=1, column=1, value="📋 Job Posts Report")
    title.font = Font(size=16, bold=True, color="FFFFFF")
    title.fill = PatternFill(start_color="005B96", end_color="005B96", fill_type="solid")  # Blue theme
    title.alignment = Alignment(horizontal='center', vertical='center')

    # Headers styling
    header_fill = PatternFill(start_color="005B96", end_color="005B96", fill_type="solid")
    for col_num, column_title in enumerate(df.columns, 1):
        cell = ws.cell(row=4, column=col_num, value=column_title)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.border = Border(bottom=Side(style='thin'))

    # Adding data rows with alternating colors and formatting
    light_blue = PatternFill(start_color="E6F3FF", end_color="E6F3FF", fill_type="solid")
    for r_idx, row in enumerate(df.itertuples(index=False), 5):
        for c_idx, value in enumerate(row, 1):
            cell = ws.cell(row=r_idx, column=c_idx, value=value)
            cell.alignment = Alignment(wrap_text=True, vertical='top')
            cell.border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'),
                                 bottom=Side(style='thin'))

            # Alternating row colors
            if (r_idx - 4) % 2 == 0:
                cell.fill = light_blue

            # Style "Not provided" entries
            if str(value).strip() == "Not provided":
                cell.font = Font(italic=True, color="FF0000")

    # Auto-fit column widths for jobs sheet
    for column_cells in ws.columns:
        if isinstance(column_cells[0], MergedCell):
            continue
        max_length = max(len(str(cell.value)) for cell in column_cells if cell.value)
        column_letter = ws.column_dimensions[column_cells[0].column_letter]
        column_letter.width = max_length + 4

    # Freeze top row
    ws.freeze_panes = 'A5'

    # Save and send file
    filename = "Job_Posts_Report.xlsx"
    wb.save(filename)

    try:
        with open(filename, "rb") as doc:
            await context.bot.send_document(
                chat_id=user_id,
                document=doc,
                filename=filename,
                caption="📋 Job Posts Report"
            )
    finally:
        if os.path.exists(filename):
            os.remove(filename)

async def handle_job_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle job search with pagination"""
    user_id = update.effective_user.id
    search_term = update.message.text.strip()
    context.user_data["search_term"] = search_term
    page = 1  # Start from the first page

    try:
        # Fetch paginated results
        jobs = db.search_jobs(search_term, page=page)
        total_pages = db.get_total_pages_jobs(search_term)

        if not jobs:
            await context.bot.send_message(
                chat_id=user_id,
                text="No matching jobs found."
            )
            return await back_to_database_menu(update, context)

        # Create paginated keyboard
        keyboard = create_paginated_keyboard(jobs, page, total_pages, "job")
        keyboard.append([InlineKeyboardButton("Back", callback_data="back_to_manage_jobs")])

        await context.bot.send_message(
            chat_id=user_id,
            text=f"Jobs matching '{search_term}' (Page {page}/{total_pages}):",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logging.error(f"Error handling job search: {e}")
        await context.bot.send_message(
            chat_id=user_id,
            text="An error occurred while fetching jobs. Please try again later."
        )
        return await back_to_database_menu(update, context)

    return REMOVE_JOBS_PAGINATED

# 1. List Vacancies Handler
async def list_vacancies(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    page = 1
    search_term = ""  # Default search term for all vacancies

    try:
        vacancies = db.search_vacancies(search_term, page)
        total_pages = db.get_total_pages_vacancies(search_term)

        if not vacancies:
            await context.bot.send_message(
                chat_id=user_id,
                text="No vacancies found."
            )
            return await back_to_database_menu(update, context)

        keyboard = create_paginated_keyboard(vacancies, page, total_pages, "vacancy")
        keyboard.append([InlineKeyboardButton("Back", callback_data="back_to_manage_vacancies")])

        await context.bot.send_message(
            chat_id=user_id,
            text=f"Vacancies (Page {page}/{total_pages}):",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logging.error(f"Error listing vacancies: {e}")
        await context.bot.send_message(
            chat_id=user_id,
            text="An error occurred while fetching vacancies. Please try again later."
        )
        return await back_to_database_menu(update, context)

    return LIST_VACANCIES_PAGINATED

# 2. Remove Vacancies Handler
async def remove_vacancies(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id

    await context.bot.send_message(
        chat_id=user_id,
        text="Enter search term (job title, employer name, or leave empty for all). Example: 'Software Engineer' or 'TechCorp':"
    )
    return SEARCH_VACANCIES


async def handle_vacancy_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    search_term = update.message.text.strip()
    context.user_data["search_term"] = search_term
    page = 1  # Start from the first page

    try:
        # Fetch paginated results
        vacancies = db.search_vacancies(search_term, page)
        total_pages = db.get_total_pages_vacancies(search_term)

        if not vacancies:
            await context.bot.send_message(
                chat_id=user_id,
                text="No matching vacancies found."
            )
            return await back_to_database_menu(update, context)

        # Create paginated keyboard
        keyboard = create_paginated_keyboard(vacancies, page, total_pages, "vacancy_remove")
        keyboard.append([InlineKeyboardButton("Back", callback_data="back_to_manage_vacancies")])

        await context.bot.send_message(
            chat_id=user_id,
            text=f"Vacancies matching '{search_term}' (Page {page}/{total_pages}):",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logging.error(f"Error handling vacancy search: {e}")
        await context.bot.send_message(
            chat_id=user_id,
            text="An error occurred while fetching vacancies. Please try again later."
        )
        return await back_to_database_menu(update, context)

    return REMOVE_VACANCIES_PAGINATED

# 3. Export Vacancies Handler
async def export_vacancies(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Export all vacancies to a professionally formatted Excel file."""
    user_id = update.effective_user.id
    vacancies = db.get_all_vacancies_posts()  # Fetch all vacancies

    if not vacancies:
        await context.bot.send_message(chat_id=user_id, text="No vacancies found.")
        return

    # Convert to DataFrame
    df = pd.DataFrame(vacancies)

    # Handle missing values
    df.fillna("Not provided", inplace=True)

    # Create Excel workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Vacancies"

    # Title section
    ws.merge_cells("A1:N2")  # Merge cells for the title
    title = ws.cell(row=1, column=1, value="📋 Vacancy Report")
    title.font = Font(size=16, bold=True, color="FFFFFF")
    title.fill = PatternFill(start_color="4B0082", end_color="4B0082", fill_type="solid")  # Indigo theme
    title.alignment = Alignment(horizontal='center', vertical='center')

    # Headers styling
    header_fill = PatternFill(start_color="4B0082", end_color="4B0082", fill_type="solid")
    for col_num, column_title in enumerate(df.columns, 1):
        cell = ws.cell(row=4, column=col_num, value=column_title)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.border = Border(bottom=Side(style='thin'))

    # Adding data rows with alternating colors and formatting
    light_indigo = PatternFill(start_color="E6E6FA", end_color="E6E6FA", fill_type="solid")
    for r_idx, row in enumerate(df.itertuples(index=False), 5):
        for c_idx, value in enumerate(row, 1):
            cell = ws.cell(row=r_idx, column=c_idx, value=value)
            cell.alignment = Alignment(wrap_text=True, vertical='top')
            cell.border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'),
                                 bottom=Side(style='thin'))

            # Alternating row colors
            if (r_idx - 4) % 2 == 0:
                cell.fill = light_indigo

            # Style "Not provided" entries
            if str(value).strip() == "Not provided":
                cell.font = Font(italic=True, color="FF0000")

    # Auto-fit column widths for vacancies sheet
    for column_cells in ws.columns:
        if isinstance(column_cells[0], MergedCell):
            continue
        max_length = max(len(str(cell.value)) for cell in column_cells if cell.value)
        column_letter = ws.column_dimensions[column_cells[0].column_letter]
        column_letter.width = max_length + 4

    # Freeze top row
    ws.freeze_panes = 'A5'

    # Save and send file
    filename = "Vacancy_Report.xlsx"
    wb.save(filename)

    try:
        with open(filename, "rb") as doc:
            await context.bot.send_document(
                chat_id=user_id,
                document=doc,
                filename=filename,
                caption="📋 Vacancy Report"
            )
    finally:
        if os.path.exists(filename):
            os.remove(filename)


# 4. Export All Data Handler
async def export_all_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id

    # Export all entity types
    await export_job_seekers(update, context)
    await export_employers(update, context)
    await export_applications(update, context)
    await export_vacancies(update, context)
    await export_jobs(update, context)

    await context.bot.send_message(
        chat_id=user_id,
        text="All data exports completed."
    )
    return await back_to_database_menu(update, context)


async def confirm_removal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = get_user_id(update)
    data = query.data

    # Extract the type and ID from the callback data
    if data.startswith("remove_seeker_"):
        target_id = data.split("_")[-1]
        await query.edit_message_text(text=f"Are you sure you want to remove job seeker with ID {target_id}?")
        context.user_data["action"] = ("remove_seeker", target_id)
    elif data.startswith("remove_employer_"):
        target_id = data.split("_")[-1]
        await query.edit_message_text(text=f"Are you sure you want to remove employer with ID {target_id}?")
        context.user_data["action"] = ("remove_employer", target_id)
    elif data.startswith("remove_application_"):
        target_id = data.split("_")[-1]
        await query.edit_message_text(text=f"Are you sure you want to remove application with ID {target_id}?")
        context.user_data["action"] = ("remove_application", target_id)
    else:
        await query.edit_message_text(text="Invalid action.")
        return await back_to_admin_menu(update, context)

    # Confirm removal with Yes/No buttons
    keyboard = [
        [InlineKeyboardButton("Yes", callback_data="confirm_yes")],
        [InlineKeyboardButton("No", callback_data="confirm_no")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=user_id, text="Confirm action:", reply_markup=reply_markup)
    return CONFIRM_REMOVAL

async def perform_removal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = get_user_id(update)
    action, target_id = context.user_data.get("action", (None, None))
    if query.data == "confirm_yes" and action and target_id:
        try:
            if action == "remove_seeker":
                db.remove_job_seeker(target_id)
                await query.edit_message_text(text=get_translation(user_id, "job_seeker_removed_successfully", id=target_id))
            elif action == "remove_employer":
                db.remove_employer(target_id)
                await query.edit_message_text(text=get_translation(user_id, "employer_removed_successfully", id=target_id))
            elif action == "remove_application":
                db.remove_application(target_id)
                await query.edit_message_text(text=get_translation(user_id, "application_removed_successfully", id=target_id))
        except Exception as e:
            await context.bot.send_message(chat_id=user_id, text=get_translation(user_id, "error_performing_removal", error=str(e)))
    elif query.data == "confirm_no":
        await query.edit_message_text(text=get_translation(user_id, "removal_canceled"))
    else:
        await query.edit_message_text(text=get_translation(user_id, "invalid_action"))
    return await back_to_manage_users(update, context)

import pandas as pd

import pandas as pd


import pandas as pd
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.worksheet.dimensions import ColumnDimension
from openpyxl.worksheet.table import Table, TableStyleInfo


import os
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.styles import Font, Alignment, PatternFill, Color

from openpyxl.styles import (
    Font, Alignment, PatternFill, Border, Side, GradientFill, Color
)
from openpyxl.utils import get_column_letter

import os
import pandas as pd
from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.worksheet.table import Table, TableStyleInfo

import os
import pandas as pd
from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.worksheet.table import Table, TableStyleInfo


import os
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from openpyxl.utils import get_column_letter

import os
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from openpyxl.utils import get_column_letter

async def export_job_seekers(update, context):
    """Export job seekers to a professionally formatted Excel file."""
    user_id = get_user_id(update)
    job_seekers = db.get_all_job_seekers_details()

    if not job_seekers:
        await context.bot.send_message(chat_id=user_id, text="No job seekers found.")
        return

    # Create DataFrame
    df = pd.DataFrame(job_seekers, columns=[
        "User ID", "Full Name", "Contact Number", "DOB", "CV Path",
        "Languages", "Qualification", "Field of Study", "CGPA",
        "Skills & Experience", "Profile Summary"
    ])

    # Handle NaN values: Separate logic for numeric and non-numeric columns
    numeric_columns = ["CGPA"]  # Add other numeric columns if needed
    df[numeric_columns] = df[numeric_columns].fillna(0)  # Fill numeric columns with 0

    non_numeric_columns = df.columns.difference(numeric_columns)
    df[non_numeric_columns] = df[non_numeric_columns].fillna("Not provided")  # Fill non-numeric columns with "Not provided"

    df.replace("", "Not provided", inplace=True)  # Replace empty strings with "Not provided"

    # Replace CV Path with "Provided" if a CV is available
    df["CV Path"] = df["CV Path"].apply(lambda x: "Provided" if x != "Not provided" else "Not provided")

    # Create Excel workbook and worksheet
    wb = Workbook()
    ws = wb.active
    ws.title = "Job Seekers"

    # Create title section
    ws.merge_cells("A1:K2")
    title = ws.cell(row=1, column=1, value="📊 Job Seekers Report")
    title.font = Font(size=16, bold=True, color="FFFFFF")
    title.fill = PatternFill(start_color="002060", end_color="002060", fill_type="solid")
    title.alignment = Alignment(horizontal='center', vertical='center')

    # Adding headers with style
    for col_num, column_title in enumerate(df.columns, 1):
        cell = ws.cell(row=4, column=col_num, value=column_title)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill(start_color="002060", end_color="002060", fill_type="solid")
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.border = Border(bottom=Side(style='thin'))

    # Adding data rows with alternating colors
    for r_idx, row in enumerate(df.itertuples(index=False), 5):
        for c_idx, value in enumerate(row, 1):
            cell = ws.cell(row=r_idx, column=c_idx, value=value)
            cell.alignment = Alignment(wrap_text=True, vertical='top')  # Enable text wrapping
            cell.border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'),
                                 bottom=Side(style='thin'))

            if (r_idx - 4) % 2 == 0:
                cell.fill = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")

            # Format CGPA
            if c_idx == 9 and value != "Not provided":
                try:
                    cell.value = float(value)
                    cell.number_format = '0.00'
                except ValueError:
                    pass

            # Conditional Formatting for CGPA
            if c_idx == 9 and isinstance(value, (int, float)):
                if value > 3.5:
                    cell.font = Font(color="008000", bold=True)  # Green for high CGPA
                elif value < 2.5:
                    cell.font = Font(color="FF0000", bold=True)  # Red for low CGPA

            # Style "Not provided" entries
            if str(value).strip() == "Not provided":
                cell.font = Font(italic=True, color="FF0000")

    # Auto-fit column widths for most columns, but limit width for long-text columns
    for column_cells in ws.columns:
        column_letter = get_column_letter(column_cells[0].column)
        max_length = max(len(str(cell.value)) for cell in column_cells if cell.value)

        # Limit width for specific columns with long text
        if column_cells[0].value in ["Skills & Experience", "Profile Summary"]:
            ws.column_dimensions[column_letter].width = 50  # Fixed width for long-text columns (wider)
        else:
            ws.column_dimensions[column_letter].width = min(max_length + 6, 40)  # Auto-fit with a wider maximum width

    # Adjust row height for long-text columns
    for row in range(5, len(df) + 5):  # Start from row 5 (data rows)
        ws.row_dimensions[row].height = 40  # Increased row height for better readability

    # Freeze top row
    ws.freeze_panes = 'A5'

    # Add Advanced Summary Sheet
    summary_ws = wb.create_sheet(title="Summary")
    summary_ws.append(["📊 Job Seekers Summary Report"])
    summary_ws.merge_cells("A1:B1")
    title_cell = summary_ws.cell(row=1, column=1)
    title_cell.font = Font(size=14, bold=True, color="FFFFFF")
    title_cell.fill = PatternFill(start_color="002060", end_color="002060", fill_type="solid")
    title_cell.alignment = Alignment(horizontal='center', vertical='center')

    summary_data = [
        ["Total Job Seekers", len(df)],
        ["Average CGPA", round(df[df['CGPA'] != "Not provided"]['CGPA'].astype(float).mean(), 2)],
        ["Top 5 Qualifications", ', '.join(df['Qualification'].value_counts().head(5).index)],
        ["Most Common Languages", ', '.join(df['Languages'].value_counts().head(5).index)],
        ["Most Popular Fields of Study", ', '.join(df['Field of Study'].value_counts().head(5).index)]
    ]

    for row in summary_data:
        summary_ws.append(row)

    for row in summary_ws.iter_rows(min_row=2, max_row=6, min_col=1, max_col=2):
        for cell in row:
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color="EAEAEA", end_color="EAEAEA", fill_type="solid")
            cell.border = Border(bottom=Side(style='thin'))

    # Auto-fit column widths for summary sheet
    for column_cells in summary_ws.columns:
        max_length = max(len(str(cell.value)) for cell in column_cells if cell.value)
        column_letter = get_column_letter(column_cells[0].column)
        summary_ws.column_dimensions[column_letter].width = max_length + 8  # Slightly wider columns for summary

    # Save and send file
    filename = "Job_Seekers_Report.xlsx"
    wb.save(filename)

    try:
        with open(filename, "rb") as doc:
            await context.bot.send_document(chat_id=user_id, document=doc, filename=filename,
                                            caption="📊 Job Seekers Report")
    finally:
        if os.path.exists(filename):
            os.remove(filename)

async def export_applications(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Export applications to a professionally formatted Excel file."""
    user_id = get_user_id(update)
    applications = db.get_all_applications_details()  # Ensure this returns full details

    if not applications:
        await context.bot.send_message(chat_id=user_id, text="No applications found.")
        return await back_to_admin_menu(update, context)

    # Create DataFrame with proper columns
    df = pd.DataFrame(applications, columns=[
        "Application ID", "Job Title", "Job Seeker Name",
        "Employer Name", "Application Date", "Status",
        "Cover Letter", "Vacancy ID"
    ])
    df.fillna("Not provided", inplace=True)
    df.replace("", "Not provided", inplace=True)

    # Convert dates to datetime
    df['Application Date'] = pd.to_datetime(df['Application Date']).dt.strftime('%Y-%m-%d')

    # Create Excel workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Applications"

    # Title section
    ws.merge_cells("A1:H2")
    title = ws.cell(row=1, column=1, value="📄 Application Tracking Report")
    title.font = Font(size=16, bold=True, color="FFFFFF")
    title.fill = PatternFill(start_color="007030", end_color="007030", fill_type="solid")  # Green theme
    title.alignment = Alignment(horizontal='center', vertical='center')

    # Headers styling
    header_fill = PatternFill(start_color="007030", end_color="007030", fill_type="solid")
    for col_num, column_title in enumerate(df.columns, 1):
        cell = ws.cell(row=4, column=col_num, value=column_title)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.border = Border(bottom=Side(style='thin'))

    # Adding data rows with alternating colors and formatting
    light_green = PatternFill(start_color="E9F5DB", end_color="E9F5DB", fill_type="solid")
    for r_idx, row in enumerate(df.itertuples(index=False), 5):
        for c_idx, value in enumerate(row, 1):
            cell = ws.cell(row=r_idx, column=c_idx, value=value)
            cell.alignment = Alignment(wrap_text=True, vertical='top')
            cell.border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'),
                                 bottom=Side(style='thin'))

            # Alternating row colors
            if (r_idx - 4) % 2 == 0:
                cell.fill = light_green

            # Style "Not provided" entries
            if str(value).strip() == "Not provided":
                cell.font = Font(italic=True, color="FF0000")

            # Conditional formatting for status
            if c_idx == 6:  # Status column
                if value.lower() == "approved":
                    cell.font = Font(color="008000", bold=True)  # Green for approved
                elif value.lower() == "rejected":
                    cell.font = Font(color="FF0000", bold=True)  # Red for rejected
                else:
                    cell.font = Font(color="FFA500", bold=True)  # Orange for pending

    # Auto-fit column widths for applications sheet
    for column_cells in ws.columns:
        max_length = max(len(str(cell.value)) for cell in column_cells if cell.value)
        column_letter = get_column_letter(column_cells[0].column)
        ws.column_dimensions[column_letter].width = max_length + 4

    # Freeze top row
    ws.freeze_panes = 'A5'

    # Add Summary Sheet
    summary_ws = wb.create_sheet(title="Summary")
    summary_ws.append(["📊 Application Summary Report"])
    summary_ws.merge_cells("A1:B1")
    title_cell = summary_ws.cell(row=1, column=1)
    title_cell.font = Font(size=14, bold=True, color="FFFFFF")
    title_cell.fill = PatternFill(start_color="007030", end_color="007030", fill_type="solid")
    title_cell.alignment = Alignment(horizontal='center', vertical='center')

    # Generate summary data
    total_applications = len(df)
    applications_by_status = df['Status'].value_counts().to_dict()
    most_applied_jobs = df['Job Title'].value_counts().head(5).to_dict()
    active_job_seekers = df['Job Seeker Name'].nunique()
    active_employers = df['Employer Name'].nunique()

    summary_data = [
        ["Total Applications", total_applications],
        ["Approved Applications", applications_by_status.get("approved", 0)],
        ["Rejected Applications", applications_by_status.get("rejected", 0)],
        ["Pending Applications", applications_by_status.get("pending", 0)],
        ["Most Applied Jobs", ', '.join(f"{job} ({count})" for job, count in most_applied_jobs.items())],
        ["Active Job Seekers", active_job_seekers],
        ["Active Employers", active_employers]
    ]

    for row in summary_data:
        summary_ws.append(row)

    # Style summary sheet
    for row in summary_ws.iter_rows(min_row=2, max_row=len(summary_data) + 1, min_col=1, max_col=2):
        for cell in row:
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color="E9F5DB", end_color="E9F5DB", fill_type="solid")
            cell.border = Border(bottom=Side(style='thin'))
            cell.alignment = Alignment(horizontal='left', vertical='center')

    # Auto-fit column widths for summary sheet
    for column_cells in summary_ws.columns:
        max_length = max(len(str(cell.value)) for cell in column_cells if cell.value)
        column_letter = get_column_letter(column_cells[0].column)
        summary_ws.column_dimensions[column_letter].width = max_length + 4

    # Save and send file
    filename = "Application_Tracking_Report.xlsx"
    wb.save(filename)

    try:
        with open(filename, "rb") as doc:
            await context.bot.send_document(
                chat_id=user_id,
                document=doc,
                filename=filename,
                caption="📄 Application Tracking Report"
            )
    finally:
        if os.path.exists(filename):
            os.remove(filename)


import pandas as pd
from telegram import Update
from telegram.ext import ContextTypes


import os
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.cell import MergedCell
from openpyxl.utils.dataframe import dataframe_to_rows
import pandas as pd

async def export_employers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Export employers to a professionally formatted Excel file."""
    user_id = update.effective_user.id
    employers = db.get_all_employers_details()

    if not employers:
        await context.bot.send_message(chat_id=user_id, text="No employers found.")
        return

    # Convert to DataFrame
    df = pd.DataFrame(employers, columns=[
        "Employer ID", "Company Name", "Contact Number", "City", "Employer Type",
        "About Company", "Verification Docs"
    ])
    df.fillna("Not provided", inplace=True)
    df.replace("", "Not provided", inplace=True)

    # Modify Verification Docs column: Replace paths with "Provided" or "Not provided"
    df["Verification Docs"] = df["Verification Docs"].apply(
        lambda x: "Provided" if str(x).strip() != "Not provided" else "Not provided"
    )

    # Create Excel workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Employers"

    # Title section
    ws.merge_cells("A1:H2")
    title = ws.cell(row=1, column=1, value="🏢 Employers Report")
    title.font = Font(size=16, bold=True, color="FFFFFF")
    title.fill = PatternFill(start_color="FF6F00", end_color="FF6F00", fill_type="solid")  # Orange theme
    title.alignment = Alignment(horizontal='center', vertical='center')

    # Headers styling
    header_fill = PatternFill(start_color="FF6F00", end_color="FF6F00", fill_type="solid")
    for col_num, column_title in enumerate(df.columns, 1):
        cell = ws.cell(row=4, column=col_num, value=column_title)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.border = Border(bottom=Side(style='thin'))

    # Adding data rows with alternating colors and formatting
    light_orange = PatternFill(start_color="FFF3E0", end_color="FFF3E0", fill_type="solid")
    for r_idx, row in enumerate(df.itertuples(index=False), 5):
        for c_idx, value in enumerate(row, 1):
            cell = ws.cell(row=r_idx, column=c_idx, value=value)
            cell.alignment = Alignment(wrap_text=True, vertical='top')
            cell.border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'),
                                 bottom=Side(style='thin'))

            # Alternating row colors
            if (r_idx - 4) % 2 == 0:
                cell.fill = light_orange

            # Style "Not provided" entries
            if str(value).strip() == "Not provided":
                cell.font = Font(italic=True, color="FF0000")

            # Hyperlink for Verification Docs
            if c_idx == 7 and value == "Provided":
                cell.value = "Provided"  # Ensure the cell displays "Provided"
                cell.font = Font(color="0000FF", underline="single")  # Blue font for hyperlink-like appearance

    # Auto-fit column widths for employers sheet
    for column_cells in ws.columns:
        # Skip merged cells
        if isinstance(column_cells[0], MergedCell):
            continue

        max_length = max(len(str(cell.value)) for cell in column_cells if cell.value)
        column_letter = ws.column_dimensions[column_cells[0].column_letter]
        column_letter.width = max_length + 4

    # Freeze top row
    ws.freeze_panes = 'A5'

    # Add Summary Sheet
    summary_ws = wb.create_sheet(title="Summary")
    summary_ws.append(["📊 Employer Summary Report"])
    summary_ws.merge_cells("A1:B1")
    title_cell = summary_ws.cell(row=1, column=1)
    title_cell.font = Font(size=14, bold=True, color="FFFFFF")
    title_cell.fill = PatternFill(start_color="FF6F00", end_color="FF6F00", fill_type="solid")
    title_cell.alignment = Alignment(horizontal='center', vertical='center')

    # Generate summary data
    total_employers = len(df)
    verified_employers = df[df['Verification Docs'] == "Provided"].shape[0]
    most_common_cities = ', '.join(df['City'].value_counts().head(5).index)
    most_common_types = ', '.join(df['Employer Type'].value_counts().head(5).index)

    summary_data = [
        ["Total Employers", total_employers],
        ["Verified Employers", verified_employers],
        ["Unverified Employers", total_employers - verified_employers],
        ["Most Common Cities", most_common_cities],
        ["Most Common Employer Types", most_common_types]
    ]

    for row in summary_data:
        summary_ws.append(row)

    # Style summary sheet
    for row in summary_ws.iter_rows(min_row=2, max_row=len(summary_data) + 1, min_col=1, max_col=2):
        for cell in row:
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color="FFF3E0", end_color="FFF3E0", fill_type="solid")
            cell.border = Border(bottom=Side(style='thin'))
            cell.alignment = Alignment(horizontal='left', vertical='center')

    # Auto-fit column widths for summary sheet
    for column_cells in summary_ws.columns:
        # Skip merged cells
        if isinstance(column_cells[0], MergedCell):
            continue

        max_length = max(len(str(cell.value)) for cell in column_cells if cell.value)
        column_letter = summary_ws.column_dimensions[column_cells[0].column_letter]
        column_letter.width = max_length + 4

    # Save and send file
    filename = "Employers_Report.xlsx"
    wb.save(filename)

    try:
        with open(filename, "rb") as doc:
            await context.bot.send_document(
                chat_id=user_id,
                document=doc,
                filename=filename,
                caption="🏢 Employers Report"
            )
    finally:
        if os.path.exists(filename):
            os.remove(filename)



# Step 1: Implement back_to_database_menu handler
async def back_to_database_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Return to the main database management menu"""
    query = update.callback_query
    if query:
        await query.answer()

    return await show_database_menu(update, context)


# Step 2: Implement export_data handler
async def export_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show export options menu"""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id

    keyboard = [
        [InlineKeyboardButton("Export Job Seekers", callback_data="export_job_seekers")],
        [InlineKeyboardButton("Export Employers", callback_data="export_employers")],
        [InlineKeyboardButton("Export Applications", callback_data="export_applications")],
        [InlineKeyboardButton("Export All Data", callback_data="export_all_data")],
        [InlineKeyboardButton("Back to Database Menu", callback_data="back_to_database_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(
        chat_id=user_id,
        text="Select data to export:",
        reply_markup=reply_markup
    )
    return EXPORT_DATA  # Make sure this state is defined in your conversation handler

async def clear_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show confirmation dialog for data clearing"""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id

    keyboard = [
        [InlineKeyboardButton("Yes, clear all data", callback_data="confirm_clear")],
        [InlineKeyboardButton("Cancel", callback_data="back_to_database_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(
        chat_id=user_id,
        text="⚠️ Are you sure you want to CLEAR ALL DATA? This action cannot be undone!",
        reply_markup=reply_markup
    )
    return CLEAR_CONFIRMATION


async def perform_clear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Execute data clearing after confirmation"""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id

    # Clear all data
    db.clear_all_data()

    await context.bot.send_message(
        chat_id=user_id,
        text="✅ All data has been successfully cleared.",
        reply_markup=ReplyKeyboardRemove()
    )
    return await back_to_database_menu(update, context)


async def back_to_manage_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)
    await context.bot.send_message(chat_id=user_id, text="Returning to Manage Users menu...")
    return await show_manage_users_menu(update, context)

async def back_to_admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)
    await context.bot.send_message(chat_id=user_id, text="Returning to Admin Menu...")
    return await show_admin_menu(update, context)

async def show_manage_users_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)

    # Define the manage users menu keyboard
    keyboard = [
        [InlineKeyboardButton("Remove Job Seekers", callback_data="remove_job_seekers")],
        [InlineKeyboardButton("Remove Employers", callback_data="remove_employers")],
        [InlineKeyboardButton("Ban Job Seekers", callback_data="ban_job_seekers")],
        [InlineKeyboardButton("Ban Employers", callback_data="ban_employers")],
        [InlineKeyboardButton("Unban Users", callback_data="unban_users_menu")],
        [InlineKeyboardButton("View Banned Users", callback_data="view_banned_users")],
        [InlineKeyboardButton("Remove Applications", callback_data="remove_applications")],
        [InlineKeyboardButton("Export Job Seekers", callback_data="export_job_seekers")],
        [InlineKeyboardButton("Export Employers", callback_data="export_employers")],
        [InlineKeyboardButton("Export Applications", callback_data="export_applications")],
        [InlineKeyboardButton("Clear All Data", callback_data="clear_all_data")],
        [InlineKeyboardButton("Back to Admin Menu", callback_data="back_to_admin_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(
        chat_id=user_id,
        text="Select an action to manage users:",
        reply_markup=reply_markup
    )
    return MANAGE_USERS

async def manage_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Redirect to the original user management menu"""
    return await show_manage_users_menu(update, context)

async def manage_applications(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show application management submenu"""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id

    keyboard = [
        [InlineKeyboardButton("List Applications", callback_data="list_applications")],
        [InlineKeyboardButton("Remove Applications", callback_data="remove_applications")],
        [InlineKeyboardButton("Export Applications", callback_data="export_applications")],
        [InlineKeyboardButton("Back to Database Menu", callback_data="back_to_database_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(
        chat_id=user_id,
        text="Application Management Options:",
        reply_markup=reply_markup
    )
    return MANAGE_APPLICATIONS

async def ban_job_seekers(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = get_user_id(update)

    # Prompt for search term
    await context.bot.send_message(
        chat_id=user_id,
        text="🔍 Enter search term (name, ID, or leave empty for all):"
    )
    return SEARCH_JOB_SEEKERS_FOR_BAN

async def handle_job_seeker_ban_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    search_term = update.message.text.strip()
    context.user_data["search_term"] = search_term
    page = 1  # Start from the first page

    try:
        # Fetch paginated results
        job_seekers = db.search_job_seekers_for_ban(search_term, page=page)
        total_pages = db.get_total_pages_job_seekers_for_ban(search_term)

        if not job_seekers:
            await context.bot.send_message(
                chat_id=user_id,
                text="❌ No matching job seekers found."
            )
            return await back_to_database_menu(update, context)

        # Create paginated keyboard using the unified function
        keyboard = create_ban_paginated_keyboard(job_seekers, page, total_pages, "job_seeker", "ban")
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_manage_users")])

        await context.bot.send_message(
            chat_id=user_id,
            text=f"🔍 Results for '{search_term}' (Page {page}/{total_pages}):",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logging.error(f"Error handling job seeker ban search: {e}")
        await context.bot.send_message(
            chat_id=user_id,
            text="❌ An error occurred while fetching job seekers. Please try again later."
        )
        return await back_to_database_menu(update, context)

    return BAN_JOB_SEEKERS_PAGINATED

async def confirm_ban_job_seeker(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    # Log the received callback_data for debugging
    logging.info(f"Received callback_data: {query.data}")

    # Validate the callback_data format
    if not query.data.startswith("ban_job_seeker_"):
        await query.edit_message_text("❌ Invalid action.")
        return await back_to_database_menu(update, context)

    try:
        # Extract the job seeker ID (everything after the prefix)
        job_seeker_id = int(query.data.split("ban_job_seeker_")[1])  # Ensure ID is an integer
        context.user_data["target_job_seeker_id"] = job_seeker_id  # Store properly
    except ValueError:
        await query.edit_message_text("❌ Invalid job seeker ID.")
        return await back_to_database_menu(update, context)

    await query.edit_message_text(
        text="📝 Enter the reason for banning this job seeker:"
    )
    return REASON_FOR_BAN_JOB_SEEKER

async def apply_ban_job_seeker(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    reason = update.message.text.strip()

    if not reason:
        await update.message.reply_text("❌ Ban reason cannot be empty. Please enter a valid reason.")
        return REASON_FOR_BAN_JOB_SEEKER

    target_job_seeker_id = context.user_data.get("target_job_seeker_id")

    if not target_job_seeker_id:
        await update.message.reply_text("❌ Error: Job seeker ID not found. Restart the process.")
        return await back_to_database_menu(update, context)

    try:
        # Apply the ban in the database
        db.ban_user(user_id=target_job_seeker_id, reason=reason, entity_type="job_seeker")

        # Notify the banned job seeker
        await context.bot.send_message(
            chat_id=target_job_seeker_id,
            text=f"🚫 You have been banned. Reason: {reason}\n\n"
                 "If you believe this was a mistake, you can appeal by:\n"
                 "1. Clicking 'Start Bot' below\n"
                 "2. Writing your appeal message\n\n"
                 "Our team will review your case within 48 hours.",
            reply_markup=ReplyKeyboardMarkup(
                [[KeyboardButton("/start")]],
                resize_keyboard=True,
                one_time_keyboard=True
            )
        )

        # Notify the admin
        await update.message.reply_text(f"✅ Successfully banned job seeker with ID {target_job_seeker_id}.")
        logging.info(f"Job seeker {target_job_seeker_id} successfully banned for reason: {reason}")

    except ValueError as e:
        logging.error(f"Validation error in ban_user: {e}")
        await update.message.reply_text(f"❌ Error: {e}")
    except Exception as e:
        logging.error(f"Unexpected error during job seeker ban: {e}", exc_info=True)
        await update.message.reply_text("❌ A server error occurred. Please try again later.")

    return await back_to_database_menu(update, context)

async def ban_employers(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = get_user_id(update)
    # Prompt for search term
    await context.bot.send_message(
        chat_id=user_id,
        text="Enter search term (company name, ID, or leave empty for all):"
    )
    return SEARCH_EMPLOYERS_FOR_BAN

async def handle_employer_ban_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    search_term = update.message.text.strip()
    context.user_data["search_term"] = search_term
    page = 1  # Start from the first page
    try:
        employers = db.search_employers_for_ban(search_term, page=page)
        total_pages = db.get_total_pages_employers_for_ban(search_term)
        if not employers:
            await context.bot.send_message(
                chat_id=user_id,
                text="No matching employers found."
            )
            return await back_to_database_menu(update, context)
        # Create paginated keyboard using the new function
        keyboard = create_ban_paginated_keyboard(employers, page, total_pages, "employer", "ban")
        keyboard.append([InlineKeyboardButton("Back", callback_data="back_to_manage_users")])
        await context.bot.send_message(
            chat_id=user_id,
            text=f"Results for '{search_term}' (Page {page}/{total_pages}):",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logging.error(f"Error handling employer ban search: {e}")
        await context.bot.send_message(
            chat_id=user_id,
            text="An error occurred while fetching employers. Please try again later."
        )
        return await back_to_database_menu(update, context)
    return BAN_EMPLOYERS_PAGINATED


async def confirm_ban_employer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data.split("_")

    if len(data) != 3 or data[0] != "ban" or data[1] != "employer":
        await query.edit_message_text("Invalid action.")
        return await back_to_database_menu(update, context)

    try:
        employer_id = int(data[2])  # Ensure ID is an integer
        context.user_data["target_employer_id"] = employer_id  # Store properly
        context.user_data["ban_reason_pending"] = True  # Flag to track state
    except ValueError:
        await query.edit_message_text("Invalid employer ID.")
        return await back_to_database_menu(update, context)

    await query.edit_message_text(text="Enter the reason for banning this employer:")
    return REASON_FOR_BAN_EMPLOYER


async def apply_ban_employer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    reason = update.message.text.strip() if update.message and update.message.text else None

    # Validate reason to ensure it's a non-empty string
    if not reason:
        logging.error("Invalid or empty ban reason received.")
        await update.message.reply_text("❌ Ban reason cannot be empty. Please enter a valid reason.")
        return REASON_FOR_BAN_EMPLOYER  # Ask for reason again

    target_employer_id = context.user_data.get("target_employer_id")

    if not target_employer_id:
        logging.error("Employer ID is missing from context.user_data.")
        await update.message.reply_text("❌ Error: Employer ID not found. Restart the process.")
        return await back_to_database_menu(update, context)

    try:
        # Explicitly ensure entity_type is "employer"
        db.ban_user(
            user_id=None,
            employer_id=target_employer_id,
            reason=reason,
            entity_type="employer"
        )

        # Notify the banned employer
        await context.bot.send_message(
            chat_id=target_employer_id,
            text=f"🚫 You have been banned. Reason: {reason}\n\n"
                 "If you believe this was a mistake, you can appeal by:\n"
                 "1. Clicking 'Start Bot' below\n"
                 "2. Writing your appeal message\n\n"
                 "Our team will review your case within 48 hours.",
            reply_markup=ReplyKeyboardMarkup(
                [[KeyboardButton("/start")]],
                resize_keyboard=True,
                one_time_keyboard=True
            )
        )

        # Notify the admin
        await update.message.reply_text(f"✅ Successfully banned employer with ID {target_employer_id}.")
        logging.info(f"Employer {target_employer_id} successfully banned for reason: {reason}")

    except ValueError as e:
        logging.error(f"Validation error in ban_user: {e}")
        await update.message.reply_text(f"❌ Error: {e}")

    except Exception as e:
        logging.error(f"Unexpected error during employer ban: {e}", exc_info=True)
        await update.message.reply_text("❌ A server error occurred. Please try again later.")

    return await back_to_database_menu(update, context)


async def unban_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = get_user_id(update)
    banned_users = db.get_banned_users()
    if not banned_users:
        await context.bot.send_message(
            chat_id=user_id,
            text="No banned users found."
        )
        return await back_to_database_menu(update, context)
    keyboard = []
    for user in banned_users:
        text = f"{user['full_name']} (ID: {user['user_id']}) - Reason: {user['reason']}"
        callback_data = f"unban_{user['user_id']}"
        keyboard.append([InlineKeyboardButton(text, callback_data=callback_data)])
    keyboard.append([InlineKeyboardButton("Back", callback_data="back_to_database_menu")])
    await context.bot.send_message(
        chat_id=user_id,
        text="Banned Users:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return UNBAN_USERS

# async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     query = update.callback_query
#     await query.answer()
#     data = query.data.split("_")
#     if len(data) != 2:
#         await query.edit_message_text("Invalid action.")
#         return await back_to_database_menu(update, context)
#     action, user_id = data
#     try:
#         db.unban_user(user_id)
#         await context.bot.send_message(
#             chat_id=user_id,
#             text="You have been unbanned. You can now use the bot again."
#         )
#         await query.edit_message_text(
#             text="User has been unbanned successfully."
#         )
#     except Exception as e:
#         logging.error(f"Error unbanning user: {e}")
#         await query.edit_message_text(
#             text="An error occurred while unbanning the user. Please try again later."
#         )
#     return await back_to_database_menu(update, context)
#

async def view_banned_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)
    banned_users = db.get_banned_users()

    if not banned_users:
        await context.bot.send_message(
            chat_id=user_id,
            text="No banned users found."
        )
        return await back_to_database_menu(update, context)

    keyboard = []
    for user in banned_users:
        if user['user_id']:  # Job seeker
            text = f"👤 {user['name']} (ID: {user['user_id']}) - Reason: {user['reason']}"
            callback_data = f"unban_user_{user['user_id']}"
        else:  # Employer
            text = f"🏢 {user['name']} (ID: {user['employer_id']}) - Reason: {user['reason']}"
            callback_data = f"unban_employer_{user['employer_id']}"

        keyboard.append([InlineKeyboardButton(text, callback_data=callback_data)])

    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_database_menu")])

    await context.bot.send_message(
        chat_id=user_id,
        text="🚫 Banned Users:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return UNBAN_USERS


async def handle_unban(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    try:
        # Parse callback data
        parts = query.data.split('_')
        if len(parts) != 3:
            raise ValueError("Invalid callback data format")

        action, entity_type, entity_id_str = parts
        entity_id = int(entity_id_str)

        # Get ban reason before unbanning
        if entity_type == "user":
            reason = db.get_ban_reason(user_id=entity_id)
            db.unban_user(user_id=entity_id)
            entity_name = "job seeker"
        elif entity_type == "employer":
            reason = db.get_ban_reason(employer_id=entity_id)
            db.unban_employer(employer_id=entity_id)
            entity_name = "employer"
        else:
            raise ValueError("Invalid entity type")

        # Notify the unbanned user/employer
        try:
            await context.bot.send_message(
                chat_id=entity_id,
                text=f"🎉 Your ban has been lifted!\n\n"
                     f"Previous reason: {reason}\n"
                     f"You can now use the bot normally."
            )
        except Exception as e:
            logging.error(f"Could not notify unbanned {entity_type} {entity_id}: {e}")

        # Confirm to admin
        await query.edit_message_text(
            text=f"✅ Successfully unbanned {entity_name} with ID {entity_id}.\n"
                 f"They have been notified.",
            reply_markup=None
        )

    except ValueError as e:
        logging.error(f"Validation error in handle_unban: {e}")
        await query.edit_message_text("❌ Invalid request. Please try again.")
    except Exception as e:
        logging.error(f"Error in handle_unban: {e}", exc_info=True)
        await query.edit_message_text("❌ Failed to unban. Please try again.")

    return await back_to_database_menu(update, context)


async def unban_users_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = get_user_id(update)

    # Get banned users from database
    banned_users = db.get_banned_users()

    if not banned_users:
        await query.edit_message_text("No banned users found.")
        return await back_to_database_menu(update, context)

    # Create menu with unban options
    keyboard = [
        [InlineKeyboardButton("📝 Unban by selection", callback_data="unban_by_selection")],
        [InlineKeyboardButton("🚀 Unban all users", callback_data="unban_all_confirmation")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_to_manage_users")]
    ]

    await query.edit_message_text(
        text="🔓 Unban Users Menu:\n\n"
             f"Total banned users: {len(banned_users)}\n"
             "Choose an unban option:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return UNBAN_USERS_MENU


async def unban_by_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = get_user_id(update)

    banned_users = db.get_banned_users()
    context.user_data["banned_users_list"] = banned_users

    # Create numbered list with user details
    user_list = []
    for idx, user in enumerate(banned_users, start=1):
        if user['user_id']:
            user_type = "👤 Job Seeker"
            user_id = user['user_id']
            name = user.get('full_name', 'Unknown')
        else:
            user_type = "🏢 Employer"
            user_id = user['employer_id']
            name = user.get('company_name', 'Unknown')

        user_list.append(
            f"{idx}. {user_type} - {name} (ID: {user_id})\n"
            f"   Reason: {user['reason']}\n"
        )

    await query.edit_message_text(
        text="📋 Banned Users List:\n\n" + "".join(user_list) +
             "\nEnter numbers to unban (e.g., '1,3,5') or 'all' to unban everyone:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="unban_users_menu")]])
    )
    return UNBAN_SELECTION


async def handle_unban_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)
    selection = update.message.text.strip().lower()
    banned_users = context.user_data.get("banned_users_list", [])

    if not banned_users:
        await update.message.reply_text("No banned users found. Please try again.")
        return await back_to_database_menu(update, context)

    try:
        if selection == "all":
            # Unban all users
            success_count = 0
            for user in banned_users:
                try:
                    if user['user_id']:
                        db.unban_user(user['user_id'])
                        entity_id = user['user_id']
                        entity_type = "job seeker"
                    else:
                        db.unban_employer(user['employer_id'])
                        entity_id = user['employer_id']
                        entity_type = "employer"

                    # Notify unbanned user
                    try:
                        await context.bot.send_message(
                            chat_id=entity_id,
                            text=f"🎉 Your ban has been lifted!\n\n"
                                 f"Reason: {user['reason']}\n"
                                 f"You can now use the bot normally."
                        )
                    except Exception as e:
                        logging.error(f"Could not notify unbanned user {entity_id}: {e}")

                    success_count += 1
                except Exception as e:
                    logging.error(f"Error unbanning user {entity_id}: {e}")

            await update.message.reply_text(
                f"✅ Successfully unbanned {success_count}/{len(banned_users)} users."
            )
        else:
            # Unban selected users
            selected_indices = [int(num.strip()) - 1 for num in selection.split(",")]
            success_count = 0

            for idx in selected_indices:
                if 0 <= idx < len(banned_users):
                    user = banned_users[idx]
                    try:
                        if user['user_id']:
                            db.unban_user(user['user_id'])
                            entity_id = user['user_id']
                            entity_type = "job seeker"
                        else:
                            db.unban_employer(user['employer_id'])
                            entity_id = user['employer_id']
                            entity_type = "employer"

                        # Notify unbanned user
                        try:
                            await context.bot.send_message(
                                chat_id=entity_id,
                                text=f"🎉 Your ban has been lifted!\n\n"
                                     f"Reason: {user['reason']}\n"
                                     f"You can now use the bot normally."
                            )
                        except Exception as e:
                            logging.error(f"Could not notify unbanned user {entity_id}: {e}")

                        success_count += 1
                    except Exception as e:
                        logging.error(f"Error unbanning user {entity_id}: {e}")

            await update.message.reply_text(
                f"✅ Successfully unbanned {success_count}/{len(selected_indices)} selected users."
            )

    except Exception as e:
        logging.error(f"Error in handle_unban_selection: {e}")
        await update.message.reply_text(
            "❌ Invalid input. Please enter numbers separated by commas (e.g., '1,3,5') or 'all'."
        )
        return UNBAN_SELECTION

    return await back_to_database_menu(update, context)


async def confirm_unban_all(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("✅ Confirm Unban All", callback_data="execute_unban_all")],
        [InlineKeyboardButton("🔙 Cancel", callback_data="unban_users_menu")]
    ]

    await query.edit_message_text(
        text="⚠️ Are you sure you want to unban ALL users?\n"
             "This action cannot be undone!",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return UNBAN_ALL_CONFIRMATION


async def execute_unban_all(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    banned_users = db.get_banned_users()
    success_count = 0

    for user in banned_users:
        try:
            if user['user_id']:
                db.unban_user(user['user_id'])
                entity_id = user['user_id']
                entity_type = "job seeker"
            else:
                db.unban_employer(user['employer_id'])
                entity_id = user['employer_id']
                entity_type = "employer"

            # Notify unbanned user
            try:
                await context.bot.send_message(
                    chat_id=entity_id,
                    text=f"🎉 Your ban has been lifted!\n\n"
                         f"Reason: {user['reason']}\n"
                         f"You can now use the bot normally."
                )
            except Exception as e:
                logging.error(f"Could not notify unbanned user {entity_id}: {e}")

            success_count += 1
        except Exception as e:
            logging.error(f"Error unbanning user {entity_id}: {e}")

    await query.edit_message_text(
        text=f"✅ Successfully unbanned {success_count}/{len(banned_users)} users.",
        reply_markup=None
    )
    return await back_to_database_menu(update, context)

def create_ban_paginated_keyboard(items, current_page, total_pages, entity_type, action="ban"):
    """
    Creates a paginated keyboard specifically for banning operations.

    Args:
        items (list): List of items (job seekers or employers) to display.
        current_page (int): The current page number.
        total_pages (int): Total number of pages available.
        entity_type (str): Type of entity ("job_seeker" or "employer").
        action (str): Action to perform ("ban" by default).

    Returns:
        list: A list of InlineKeyboardButton rows.
    """
    keyboard = []

    # Add item buttons with ban action
    for item in items:
        if entity_type == "job_seeker":
            text = f"{item['full_name']} (ID: {item['user_id']})"
            callback_data = f"ban_job_seeker_{item['user_id']}"
        elif entity_type == "employer":
            text = f"{item['company_name']} (ID: {item['employer_id']})"
            callback_data = f"{action}_employer_{item['employer_id']}"
        else:
            continue  # Skip unsupported entity types
        keyboard.append([InlineKeyboardButton(text, callback_data=callback_data)])

    # Add pagination buttons
    nav_buttons = []
    if current_page > 1:
        nav_buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"prev_{entity_type}_{current_page}"))
    if current_page < total_pages:
        nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"next_{entity_type}_{current_page}"))
    if nav_buttons:
        keyboard.append(nav_buttons)

    return keyboard

async def reject_appeal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data.split("_")
    if len(data) != 3:
        await query.edit_message_text("Invalid action.")
        return await back_to_database_menu(update, context)
    _, _, user_id = data
    try:
        db.reject_appeal(user_id)
        await context.bot.send_message(
            chat_id=user_id,
            text="Your appeal has been rejected. For more details, please contact the admin."
        )
        await query.edit_message_text(
            text="Appeal has been rejected successfully."
        )
    except Exception as e:
        logging.error(f"Error rejecting appeal: {e}")
        await query.edit_message_text(
            text="An error occurred while rejecting the appeal. Please try again later."
        )
    return await back_to_database_menu(update, context)

async def confirm_ban(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data.split("_")
    if len(data) != 3:
        await query.edit_message_text("Invalid action.")
        return await back_to_database_menu(update, context)
    action, entity_type, user_id = data
    context.user_data["target_user_id"] = user_id
    await query.edit_message_text(
        text="Enter the reason for banning this user:"
    )
    return REASON_FOR_BAN

async def apply_ban(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    target_user_id = context.user_data.get("target_user_id")
    reason = update.message.text.strip()
    try:
        db.ban_user(target_user_id, reason)
        await context.bot.send_message(
            chat_id=target_user_id,
            text=f"You are temporarily banned from using this bot due to: {reason}. Please contact the admin for more details."
        )
        await context.bot.send_message(
            chat_id=user_id,
            text="User has been banned successfully."
        )
    except Exception as e:
        logging.error(f"Error applying ban: {e}")
        await context.bot.send_message(
            chat_id=user_id,
            text="An error occurred while banning the user. Please try again later."
        )
    return await back_to_database_menu(update, context)

# async def view_banned_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     user_id = get_user_id(update)
#     banned_users = db.get_banned_users()
#     if not banned_users:
#         await context.bot.send_message(
#             chat_id=user_id,
#             text="No banned users found."
#         )
#         return await back_to_database_menu(update, context)
#     keyboard = []
#     for user in banned_users:
#         text = f"{user['full_name']} (ID: {user['user_id']}) - Reason: {user['reason']}"
#         callback_data = f"unban_{user['user_id']}"
#         keyboard.append([InlineKeyboardButton(text, callback_data=callback_data)])
#     keyboard.append([InlineKeyboardButton("Back", callback_data="back_to_database_menu")])
#     await context.bot.send_message(
#         chat_id=user_id,
#         text="Banned Users:",
#         reply_markup=InlineKeyboardMarkup(keyboard)
#     )
#     return UNBAN_USERS
#
# async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     query = update.callback_query
#     await query.answer()
#     data = query.data.split("_")
#     if len(data) != 2:
#         await query.edit_message_text("Invalid action.")
#         return await back_to_database_menu(update, context)
#     action, user_id = data
#     try:
#         db.unban_user(user_id)
#         await context.bot.send_message(
#             chat_id=user_id,
#             text="You have been unbanned. You can now use the bot again."
#         )
#         await query.edit_message_text(
#             text="User has been unbanned successfully."
#         )
#     except Exception as e:
#         logging.error(f"Error unbanning user: {e}")
#         await query.edit_message_text(
#             text="An error occurred while unbanning the user. Please try again later."
#         )
#     return await back_to_database_menu(update, context)

async def start_ban_appeal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    if not db.is_user_banned(user_id=user_id) and not db.is_user_banned(employer_id=user_id):
        await query.edit_message_text("You are not currently banned.")
        return ConversationHandler.END

    # Store the original message ID for cleanup
    context.user_data["ban_message_id"] = query.message.message_id

    try:
        await query.edit_message_text(
            "✍️ Please write your appeal message (max 500 characters):\n\n"
            "Explain why you believe the ban should be lifted. "
            "Include any relevant details or evidence."
        )
    except Exception as e:
        logging.error(f"Error editing message: {e}")
        await context.bot.send_message(
            chat_id=user_id,
            text="✍️ Please write your appeal message (max 500 characters):\n\n"
                 "Explain why you believe the ban should be lifted. "
                 "Include any relevant details or evidence."
        )

    return APPEAL_INPUT


def get_complete_ban_reason(user_id):
    """Get ban reason checking both job seeker and employer status"""
    # Check job seeker ban first
    if db.is_user_banned(user_id=user_id, employer_id=None):
        reason = db.get_ban_reason(user_id=user_id, employer_id=None)
        if reason:
            return reason

    # Check employer ban if no job seeker ban found
    employer_profile = db.get_employer_profile(user_id)
    if employer_profile and db.is_user_banned(user_id=None, employer_id=employer_profile.get("employer_id")):
        reason = db.get_ban_reason(user_id=None, employer_id=employer_profile.get("employer_id"))
        if reason:
            return reason

    return "No reason provided"

async def handle_appeal_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    appeal_text = update.message.text.strip()

    if len(appeal_text) > 500:
        await update.message.reply_text("❌ Appeal is too long (max 500 characters). Please shorten it.")
        return APPEAL_INPUT

    try:
        # Clean up original ban message if possible
        if "ban_message_id" in context.user_data:
            try:
                await context.bot.delete_message(
                    chat_id=user_id,
                    message_id=context.user_data["ban_message_id"]
                )
            except Exception as e:
                logging.error(f"Couldn't delete ban message: {e}")

        # Save appeal to database
        db.create_appeal(
            user_id=user_id,
            content=appeal_text
        )

        # Get user details for admin notification
        user_type = "Job Seeker"
        name = db.get_user_profile(user_id).get('full_name', 'Unknown')
        if db.is_user_banned(employer_id=user_id):  # Check if employer
            employer = db.get_employer_profile(user_id)
            user_type = "Employer"
            name = employer.get('company_name', 'Unknown')

        ban_reason = get_complete_ban_reason(user_id)

        # Notify all active admins
        for admin_id in active_admins:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=f"📩 New Ban Appeal\n\n"
                         f"User Type: {user_type}\n"
                         f"Name: {name}\n"
                         f"User ID: {user_id}\n\n"
                         f"Ban Reason: {ban_reason}\n\n"
                         f"Appeal Content:\n{appeal_text}\n\n",

                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔓 Lift Ban", callback_data=f"lift_ban_{user_id}"),
                         InlineKeyboardButton("🔒 Uphold Ban", callback_data=f"uphold_ban_{user_id}")],
                        [InlineKeyboardButton("ℹ️ Request Info", callback_data=f"request_info_{user_id}")]
                    ])
                )
            except Exception as e:
                logging.error(f"Could not notify admin {admin_id}: {e}")

        # Confirm to user
        await update.message.reply_text(
            "✅ Your appeal has been submitted!\n\n"
            "Our team will review it when available. "
            "You'll receive a notification when a decision is made."
        )

    except Exception as e:
        logging.error(f"Error handling appeal: {e}")
        await update.message.reply_text("❌ Failed to submit appeal. Please try again later.")

    return ConversationHandler.END


async def review_appeal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        if not context.args:
            await update.message.reply_text("Usage: /review_appeal <user_id>")
            return

        user_id = int(context.args[0])
        appeal = db.get_appeal(user_id)

        if not appeal:
            await update.message.reply_text("No pending appeal found for this user.")
            return

        # Get user details
        user_type = "Job Seeker"
        name = db.get_user_profile(user_id).get('full_name', 'Unknown')
        if db.is_user_banned(employer_id=user_id):
            employer = db.get_employer_profile(user_id)
            user_type = "Employer"
            name = employer.get('company_name', 'Unknown')

        ban_reason = get_complete_ban_reason(user_id)

        # Updated to match the new callback patterns
        keyboard = [
            [InlineKeyboardButton("🔓 Lift Ban", callback_data=f"lift_ban_{user_id}"),
             InlineKeyboardButton("🔒 Uphold Ban", callback_data=f"uphold_ban_{user_id}")],
            [InlineKeyboardButton("ℹ️ Request Info", callback_data=f"request_info_{user_id}")]
        ]

        await update.message.reply_text(
            f"📄 Appeal Review\n\n"
            f"User Type: {user_type}\n"
            f"Name: {name}\n"
            f"User ID: {user_id}\n\n"
            f"Ban Reason: {ban_reason}\n\n"
            f"Appeal Content:\n{appeal['content']}\n\n"
            f"Submitted: {appeal['review_date']}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        return APPEAL_REVIEW

    except ValueError:
        await update.message.reply_text("❌ Invalid user ID. Please provide a numeric ID.")
    except Exception as e:
        logging.error(f"Error in review_appeal: {str(e)}")
        await update.message.reply_text("❌ Failed to review appeal. Please try again.")


async def handle_appeal_decision(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    try:
        # Extract action and user_id from callback_data
        action, user_id_str = query.data.split('_')[:2], query.data.split('_')[-1]
        user_id = int(user_id_str)
        action = '_'.join(action)  # Reconstructs "lift_ban", "uphold_ban", or "request_info"

        # Get ban details
        is_job_seeker = db.is_user_banned(user_id=user_id)
        is_employer = not is_job_seeker and db.is_user_banned(employer_id=user_id)

        if not (is_job_seeker or is_employer):
            await query.edit_message_text("⚠️ User is not currently banned")
            return ConversationHandler.END

        # Map actions to status values
        action_status_map = {
            "lift_ban": "ban_lifted",
            "uphold_ban": "ban_upheld",
            "request_info": "info_requested"
        }

        status = action_status_map.get(action)
        if not status:
            await query.edit_message_text("❌ Invalid action")
            return ConversationHandler.END

        # Process the action
        if action == "lift_ban":
            if is_job_seeker:
                db.unban_user(user_id)
            else:
                db.unban_employer(user_id)

            # Notify user
            await context.bot.send_message(
                chat_id=user_id,
                text="🎉 Your ban has been lifted! You can now use the bot normally."
            )

            await query.edit_message_text(f"✅ Successfully lifted ban for user {user_id}")

        elif action == "uphold_ban":
            # Notify user
            await context.bot.send_message(
                chat_id=user_id,
                text="⚠️ Your ban appeal was reviewed but the ban remains in place."
            )

            await query.edit_message_text(f"ℹ️ Ban upheld for user {user_id}")

        elif action == "request_info":
            # Notify user
            await context.bot.send_message(
                chat_id=user_id,
                text="ℹ️ We need more information about your appeal. Please contact the Admins."
            )

            await query.edit_message_text(f"📝 Requested more info from user {user_id}")

        # Update appeal status in database
        db.update_appeal_status(
            user_id=user_id,
            status=status
        )

    except Exception as e:
        logging.error(f"Error in handle_appeal_decision: {e}")
        await query.edit_message_text("❌ Failed to process appeal decision")

    return ConversationHandler.END

#help option
async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)

    # Get a random smart tip
    smart_tips = [
        get_translation(user_id, "tip_portfolio"),
        get_translation(user_id, "tip_communication"),
        get_translation(user_id, "tip_profile_completion"),
        get_translation(user_id, "tip_negotiation")
    ]
    random_tip = random.choice(smart_tips)

    # Create help keyboard
    keyboard = [
        [InlineKeyboardButton("📚 " + get_translation(user_id, "faq_section"), callback_data="help_faq")],
        [InlineKeyboardButton("📩 " + get_translation(user_id, "contact_admin"), callback_data="help_contact")],
        [InlineKeyboardButton("🔙 " + get_translation(user_id, "back_to_main"), callback_data="help_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Build help message with tip
    help_message = (
        f"🌟 {get_translation(user_id, 'help_center_title')}\n\n"
        f"{get_translation(user_id, 'help_intro')}\n\n"
        f"💡 {get_translation(user_id, 'smart_tip')}: {random_tip}\n\n"
        f"{get_translation(user_id, 'help_choose_option')}"
    )

    # Send or update message
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text=help_message,
            reply_markup=reply_markup
        )
    else:
        await context.bot.send_message(
            chat_id=user_id,
            text=help_message,
            reply_markup=reply_markup
        )

    return HELP_MENU


async def help_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = get_user_id(update)
    data = query.data

    if data == "help_faq":
        return await show_faq_category_section(update, context)

    elif data == "help_contact":
        return await show_contact_options(update, context)
    elif data == "help_back":
        return await main_menu(update, context)

    return HELP_MENU




async def show_faq_category_section(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = get_user_id(update)

    # Main FAQ categories
    faq_main_categories = {
        "employer": "👨‍💼 " + get_translation(user_id, "employer_faq"),
        "job_seeker": "👤 " + get_translation(user_id, "job_seeker_faq"),
        "admin": "🔒 " + get_translation(user_id, "admin_faq")
    }

    # Check if we're coming from a sub-category selection
    if query.data.startswith("faq_main_"):  # Changed from "faq_main_" to "faq_main_"
        faq_type = "_".join(query.data.split("_")[2:])

        if faq_type == "employer":
            return await show_faq_section(update, context)
        elif faq_type == "job_seeker":
            return await show_job_seeker_faq(update, context)
        elif faq_type == "admin":
            return await show_admin_faq(update, context)
        else:
            await query.edit_message_text(
                text=get_translation(user_id, "invalid_selection_message")
            )
            return FAQ_SECTION

    # Create inline keyboard buttons for main FAQ categories
    keyboard = [
        [InlineKeyboardButton(category, callback_data=f"faq_main_{key}")]
        for key, category in faq_main_categories.items()
    ]
    # Change the back button's callback_data to "faq_back_help"
    keyboard.append([InlineKeyboardButton(
        "🔙 " + get_translation(user_id, "back_to_help"),
        callback_data="help_back")  # Updated callback data
    ])
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Build FAQ category selection message
    faq_category_message = (
        f"📚 {get_translation(user_id, 'faq_section')}\n\n"
        f"{get_translation(user_id, 'select_faq_category')}"
    )

    await query.edit_message_text(
        text=faq_category_message,
        reply_markup=reply_markup
    )

    return FAQ_SECTION

import random


async def show_faq_section(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)

    # Random helpful tips
    smart_tips = [
        get_translation(user_id, "tip_profile_completion"),
        get_translation(user_id, "tip_post_job"),
        get_translation(user_id, "tip_manage_vacancies"),
        get_translation(user_id, "tip_view_analytics"),
        get_translation(user_id, "tip_change_language")
    ]
    random_tip = random.choice(smart_tips)

    # Organize FAQs into categories for better navigation
    faq_categories = {
        "👤 Profile & Account": [
            ("faq_profile_completion", "faq_profile_strength", "faq_edit_profile", "faq_delete_account"),
        ],
        "💼 Vacancies & Applications": [
            ("faq_active_vacancies", "faq_post_job", "faq_manage_vacancies", "faq_view_applicants"),
        ],
        "📊 Analytics & Performance": [
            ("faq_view_analytics", "faq_export_data"),
        ],
        "🌐 Language & Settings": [
            ("faq_change_language"),
        ],
        "💡 Tips & Suggestions": [
            ("faq_employer_tips"),
        ],
        "🚫 Ban & Appeal": [
            ("js_faq_ban_notification"),("js_faq_appeal_process"),("js_faq_appeal_review"),("js_faq_ban_removal"),("js_faq_appeal_rejection"),("js_faq_admin_ban_criteria"), ("js_faq_ban_reason_visibility"), ("js_faq_admin_ban_tools"),
        ]
    }

    # Create inline keyboard buttons for FAQ categories
    keyboard = [
        [InlineKeyboardButton(f"📂 {category}", callback_data=f"faq_category_{index}")]
        for index, category in enumerate(faq_categories.keys())
    ]
    keyboard.append([InlineKeyboardButton("🔙 " + get_translation(user_id, "back_to_help"), callback_data="help_back")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Build FAQ section message with a random tip
    faq_message = (
        f"📚 {get_translation(user_id, 'faq_section')}\n\n"
        f"{get_translation(user_id, 'faq_intro')}\n\n"
        f"💡 {get_translation(user_id, 'smart_tip')}: {random_tip}\n\n"
        f"{get_translation(user_id, 'choose_faq_category')}"
    )

    # Send or update message
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text=faq_message,
            reply_markup=reply_markup
        )
    else:
        await context.bot.send_message(
            chat_id=user_id,
            text=faq_message,
            reply_markup=reply_markup
        )

    return FAQ_SECTION


async def handle_faq_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = get_user_id(update)
    data = query.data

    try:
        # Remove the manual back button handling
        if data.startswith("faq_category_"):
            category_index = int(data.split("_")[2])
            context.user_data['current_faq_category'] = category_index
        else:
            raise ValueError("Invalid callback_data format")

        # Map category index to FAQ category
        faq_categories = {
            0: "👤 Profile & Account",
            1: "💼 Vacancies & Applications",
            2: "📊 Analytics & Performance",
            3: "🌐 Language & Settings",
            4: "💡 Tips & Suggestions",
            5: "🚫 Ban & Appeal"
        }

        if category_index not in faq_categories:
            raise KeyError(f"Invalid category index: {category_index}")

        selected_category = faq_categories[category_index]

        # Get FAQ questions for selected category
        faq_questions = {
            "👤 Profile & Account": [
                "faq_profile_completion", "faq_profile_strength", "faq_edit_profile", "faq_delete_account"
            ],
            "💼 Vacancies & Applications": [
                "faq_active_vacancies", "faq_post_job", "faq_manage_vacancies", "faq_view_applicants"
            ],
            "📊 Analytics & Performance": [
                "faq_view_analytics", "faq_export_data"
            ],
            "🌐 Language & Settings": [
                "faq_change_language"
            ],
            "💡 Tips & Suggestions": [
                "faq_employer_tips"
            ],
            "🚫 Ban & Appeal": [
                "js_faq_ban_notification",
                "js_faq_appeal_process",
                "js_faq_appeal_review",
                "js_faq_ban_removal",
                "js_faq_appeal_rejection",
                "js_faq_admin_ban_criteria",
                "js_faq_ban_reason_visibility",
                "js_faq_admin_ban_tools"
            ]
        }

        # Create keyboard with FAQ questions
        keyboard = [
            [InlineKeyboardButton(get_translation(user_id, q), callback_data=f"faq_question_{q}")]
            for q in faq_questions[selected_category]
        ]
        keyboard.append([
            InlineKeyboardButton(
                "🔙 " + get_translation(user_id, "back_to_faq"),
                callback_data="faq_category_back"
            )
        ])

        # Build message text
        message = (
            f"📂 {selected_category}\n\n"
            f"{get_translation(user_id, 'faq_category_intro')}\n\n"
            f"{get_translation(user_id, 'choose_faq_question')}"
        )

        await query.edit_message_text(
            text=message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        return FAQ_CATEGORY

    except (ValueError, IndexError) as e:
        error_msg = f"⚠️ Error: {str(e)}\n\n{get_translation(user_id, 'try_again')}"
        await query.edit_message_text(text=error_msg)
        return FAQ_SECTION

    except KeyError as e:
        error_msg = f"⚠️ Error: {str(e)}\n\n{get_translation(user_id, 'invalid_selection')}"
        await query.edit_message_text(text=error_msg)
        return FAQ_SECTION

async def handle_faq_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = get_user_id(update)

    try:
        # Extract question key from callback data
        prefix, action, question_key = query.data.split("_", 2)

        # Validate the prefix and action
        if prefix != "faq" or action != "question":
            raise ValueError("Invalid callback_data format")

        # Get the answer for the selected question
        faq_answers = {
            "faq_profile_completion": "faq_profile_completion_answer",
            "faq_profile_strength": "faq_profile_strength_answer",
            "faq_edit_profile": "faq_edit_profile_answer",
            "faq_delete_account": "faq_delete_account_answer",
            "faq_active_vacancies": "faq_active_vacancies_answer",
            "faq_post_job": "faq_post_job_answer",
            "faq_manage_vacancies": "faq_manage_vacancies_answer",
            "faq_view_applicants": "faq_view_applicants_answer",
            "faq_view_analytics": "faq_view_analytics_answer",
            "faq_export_data": "faq_export_data_answer",
            "faq_change_language": "faq_change_language_answer",
            "faq_employer_tips": "faq_employer_tips_answer",
            "js_faq_ban_notification": "js_faq_ban_notification_answer",
            "js_faq_appeal_process": "js_faq_appeal_process_answer",
            "js_faq_appeal_review": "js_faq_appeal_review_answer",
            "js_faq_ban_removal": "js_faq_ban_removal_answer",
            "js_faq_appeal_rejection": "js_faq_appeal_rejection_answer",
            "js_faq_admin_ban_criteria": "js_faq_admin_ban_criteria_answer",
            "js_faq_ban_reason_visibility": "js_faq_ban_reason_visibility_answer",
            "js_faq_admin_ban_tools": "js_faq_admin_ban_tools_answer"
        }

        # Ensure the question key exists in the FAQ answers
        if question_key not in faq_answers:
            raise KeyError(f"Question key '{question_key}' not found in FAQ answers")

        # Get the translated question and answer
        question = get_translation(user_id, question_key)
        answer = get_translation(user_id, faq_answers[question_key])

        category_index = context.user_data.get('current_faq_category', 0)
        keyboard = [
            [InlineKeyboardButton("🔙 " + get_translation(user_id, "back_to_faq_category"),
                                  callback_data=f"faq_question_back_{category_index}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Build FAQ question message
        faq_question_message = (
            f"❓ {question}\n\n"
            f"✅ {answer}"
        )

        await query.edit_message_text(
            text=faq_question_message,
            reply_markup=reply_markup
        )

        return FAQ_QUESTION

    except ValueError as e:
        # Handle invalid callback_data format
        error_message = f"Error: Invalid callback_data format. Details: {str(e)}"
        await query.edit_message_text(text=error_message)
        return FAQ_CATEGORY

    except KeyError as e:
        # Handle missing question key
        error_message = f"Error: {str(e)}"
        await query.edit_message_text(text=error_message)
        return FAQ_CATEGORY

# job seeker faq
async def show_job_seeker_faq(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)

    # Job seeker specific smart tips
    smart_tips = [
        get_translation(user_id, "js_tip_complete_profile"),
        get_translation(user_id, "js_tip_application_strategy"),
        get_translation(user_id, "js_tip_search_filters"),
        get_translation(user_id, "js_tip_document_upload"),
        get_translation(user_id, "js_tip_profile_visibility")
    ]
    random_tip = random.choice(smart_tips)

    # Organized categories for job seekers
    faq_categories = {
        "📝 Registration & Profile": [
            "js_faq_registration_steps",
            "js_faq_profile_update",
            "js_faq_document_upload",
            "js_faq_optional_fields"
        ],
        "🔍 Job Search & Applications": [
            "js_faq_job_application_process",
            "js_faq_application_status",
            "js_faq_application_outcome",
            "js_faq_application_export"
        ],
        "📂 Search & Filters": [
            "js_faq_job_search",
            "js_faq_advanced_filters",
            "js_faq_search_sorting",
            "js_faq_search_saving"
        ],
        "🔒 Account Management": [
            "js_faq_account_deletion",
            "js_faq_data_visibility"
        ],
        "🚫 Ban & Appeal": [
            "js_faq_ban_notification",
            "js_faq_appeal_process",
            "js_faq_appeal_review",
            "js_faq_ban_removal",
            "js_faq_appeal_rejection",
            "js_faq_admin_ban_criteria",
            "js_faq_ban_reason_visibility",
            "js_faq_admin_ban_tools"
        ],
    }

    keyboard = [
        [InlineKeyboardButton(f"📂 {category}", callback_data=f"js_faq_category_{index}")]
        for index, category in enumerate(faq_categories.keys())
    ]
    keyboard.append(
        [InlineKeyboardButton("🔙 " + get_translation(user_id, "back_to_help"), callback_data="js_faq_back")])

    message = (
        f"📚 {get_translation(user_id, 'js_faq_welcome')}\n\n"
        f"{get_translation(user_id, 'js_faq_intro')}\n\n"
        f"💡 {get_translation(user_id, 'smart_tip')}: {random_tip}\n\n"
        f"{get_translation(user_id, 'choose_faq_category')}"
    )

    if update.callback_query:
        await update.callback_query.edit_message_text(
            text=message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await context.bot.send_message(
            chat_id=user_id,
            text=message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    return JS_FAQ_SECTION


async def handle_job_seeker_faq_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = get_user_id(update)

    faq_categories = {
        0: "📝 Registration & Profile",
        1: "🔍 Job Search & Applications",
        2: "📂 Search & Filters",
        3: "🔒 Account Management",
        4: "🚫 Ban & Appeal"
    }

    try:
        category_index = int(query.data.split("_")[3])
        # Store the current category index in user_data
        context.user_data['current_js_category'] = category_index
        selected_category = faq_categories[category_index]

        category_questions = {
            "📝 Registration & Profile": [
                "js_faq_registration_steps",
                "js_faq_profile_update",
                "js_faq_document_upload",
                "js_faq_optional_fields"
            ],
            "🔍 Job Search & Applications": [
                "js_faq_job_application_process",
                "js_faq_application_status",
                "js_faq_application_outcome",
                "js_faq_application_export"
            ],
            "📂 Search & Filters": [
                "js_faq_job_search",
                "js_faq_advanced_filters",
                "js_faq_search_sorting",
                "js_faq_search_saving"
            ],
            "🔒 Account Management": [
                "js_faq_account_deletion",
                "js_faq_data_visibility"
            ],
            "🚫 Ban & Appeal": [
                "js_faq_ban_notification",
                "js_faq_appeal_process",
                "js_faq_appeal_review",
                "js_faq_ban_removal",
                "js_faq_appeal_rejection",
                "js_faq_admin_ban_criteria",
                "js_faq_ban_reason_visibility",
                "js_faq_admin_ban_tools"
            ]
        }

        keyboard = [
            [InlineKeyboardButton(get_translation(user_id, q), callback_data=f"js_faq_q_{q}")]
            for q in category_questions[selected_category]
        ]
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data=f"js_faq_return_{category_index}")])

        message = (
            f"📂 {selected_category}\n\n"
            f"{get_translation(user_id, 'faq_category_intro')}\n\n"
            f"{get_translation(user_id, 'choose_faq_question')}"
        )

        await query.edit_message_text(
            text=message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        return JS_FAQ_CATEGORY

    except Exception as e:
        await query.edit_message_text(text=f"⚠️ Error: {str(e)}")
        return JS_FAQ_SECTION


async def handle_job_seeker_faq_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = get_user_id(update)

    # Job seeker FAQ answers mapping
    faq_answers = {
        "js_faq_registration_steps": "js_faq_registration_steps_answer",
        "js_faq_profile_update": "js_faq_profile_update_answer",
        "js_faq_document_upload": "js_faq_document_upload_answer",
        "js_faq_optional_fields": "js_faq_optional_fields_answer",
        "js_faq_job_application_process": "js_faq_job_application_process_answer",
        "js_faq_application_status": "js_faq_application_status_answer",
        "js_faq_application_outcome": "js_faq_application_outcome_answer",
        "js_faq_application_export": "js_faq_application_export_answer",
        "js_faq_job_search": "js_faq_job_search_answer",
        "js_faq_advanced_filters": "js_faq_advanced_filters_answer",
        "js_faq_search_sorting": "js_faq_search_sorting_answer",
        "js_faq_search_saving": "js_faq_search_saving_answer",
        "js_faq_account_deletion": "js_faq_account_deletion_answer",
        "js_faq_data_visibility": "js_faq_data_visibility_answer",
        "js_faq_ban_notification": "js_faq_ban_notification_answer",
        "js_faq_appeal_process": "js_faq_appeal_process_answer",
        "js_faq_appeal_review": "js_faq_appeal_review_answer",
        "js_faq_ban_removal": "js_faq_ban_removal_answer",
        "js_faq_appeal_rejection": "js_faq_appeal_rejection_answer",
        "js_faq_admin_ban_criteria": "js_faq_admin_ban_criteria_answer",
        "js_faq_ban_reason_visibility": "js_faq_ban_reason_visibility_answer",
        "js_faq_admin_ban_tools": "js_faq_admin_ban_tools_answer"
    }

    try:
        question_key = query.data.split("_", 3)[3]
        answer_key = faq_answers[question_key]

        question = get_translation(user_id, question_key)
        answer = get_translation(user_id, answer_key)

        keyboard = [
            [InlineKeyboardButton("🔙 Back",
                                  callback_data=f"js_faq_return_{context.user_data.get('current_js_category')}")]
        ]

        message = (
            f"❓ {question}\n\n"
            f"✅ {answer}"
        )

        await query.edit_message_text(
            text=message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        return JS_FAQ_QUESTION

    except Exception as e:
        await query.edit_message_text(text=f"⚠️ Error: {str(e)}")
        return JS_FAQ_CATEGORY


async def show_admin_faq(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)

    # Admin-specific smart tips
    smart_tips = [
        get_translation(user_id, "admin_tip_database_backup"),
        get_translation(user_id, "admin_tip_post_moderation"),
        get_translation(user_id, "admin_tip_broadcast_usage"),
        get_translation(user_id, "admin_tip_ban_management")
    ]
    random_tip = random.choice(smart_tips)

    # Organized categories for admin features
    faq_categories = {
        "🛡️ Admin Panel": [
            "admin_faq_panel_overview",
            "admin_faq_menu_options"
        ],
        "📝 Job Moderation": [
            "admin_faq_job_management",
            "admin_faq_post_sharing",
            "admin_faq_invalid_posts"
        ],
        "📂 Database Management": [
            "admin_faq_database_options",
            "admin_faq_data_deletion"
        ],
        "📢 Communications": [
            "admin_faq_broadcast_feature"
        ],
        "🚫 Ban Management": [
            "admin_faq_ban_process",
            "admin_faq_appeal_review",
            "admin_faq_ban_tools"
        ]
    }

    keyboard = [
        [InlineKeyboardButton(f"📂 {category}", callback_data=f"admin_faq_cat_{index}")]
        for index, category in enumerate(faq_categories.keys())
    ]
    keyboard.append([
        InlineKeyboardButton(
            "🔙 " + get_translation(user_id, "back_to_help"),
            callback_data="admin_faq_back_to_main"  # Correct pattern
        )
    ])
    message = (
        f"🔒 {get_translation(user_id, 'admin_faq_welcome')}\n\n"
        f"{get_translation(user_id, 'admin_faq_intro')}\n\n"
        f"💡 {get_translation(user_id, 'smart_tip')}: {random_tip}\n\n"
        f"{get_translation(user_id, 'choose_faq_category')}"
    )

    if update.callback_query:
        await update.callback_query.edit_message_text(
            text=message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await context.bot.send_message(
            chat_id=user_id,
            text=message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    return ADMIN_FAQ_SECTION


async def handle_admin_faq_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = get_user_id(update)

    # Category index mapping for admin
    faq_categories = {
        0: "🛡️ Admin Panel",
        1: "📝 Job Moderation",
        2: "📂 Database Management",
        3: "📢 Communications",
        4: "🚫 Ban Management"
    }

    try:
        category_index = int(query.data.split("_")[3])
        context.user_data['current_admin_category'] = category_index
        selected_category = faq_categories[category_index]

        # Question mapping for each category
        category_questions = {
            "🛡️ Admin Panel": [
                "admin_faq_panel_overview",
                "admin_faq_menu_options"
            ],
            "📝 Job Moderation": [
                "admin_faq_job_management",
                "admin_faq_post_sharing",
                "admin_faq_invalid_posts"
            ],
            "📂 Database Management": [
                "admin_faq_database_options",
                "admin_faq_data_deletion"
            ],
            "📢 Communications": [
                "admin_faq_broadcast_feature"
            ],
            "🚫 Ban Management": [
                "admin_faq_ban_process",
                "admin_faq_appeal_review",
                "admin_faq_ban_tools"
            ]
        }

        keyboard = [
            [InlineKeyboardButton(get_translation(user_id, q), callback_data=f"admin_faq_q_{q}")]
            for q in category_questions[selected_category]
        ]
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data=f"admin_faq_return_{category_index}")])
        message = (
            f"📂 {selected_category}\n\n"
            f"{get_translation(user_id, 'faq_category_intro')}\n\n"
            f"{get_translation(user_id, 'choose_faq_question')}"
        )

        await query.edit_message_text(
            text=message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        return ADMIN_FAQ_CATEGORY

    except Exception as e:
        await query.edit_message_text(text=f"⚠️ Error: {str(e)}")
        return ADMIN_FAQ_SECTION


async def handle_admin_faq_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = get_user_id(update)

    # Admin FAQ answers mapping
    faq_answers = {
        # Admin Panel
        "admin_faq_panel_overview": "admin_faq_panel_overview_ans",
        "admin_faq_menu_options": "admin_faq_menu_options_ans",

        # Job Moderation
        "admin_faq_job_management": "admin_faq_job_management_ans",
        "admin_faq_post_sharing": "admin_faq_post_sharing_ans",
        "admin_faq_invalid_posts": "admin_faq_invalid_posts_ans",

        # Database Management
        "admin_faq_database_options": "admin_faq_database_options_ans",
        "admin_faq_data_deletion": "admin_faq_data_deletion_ans",

        # Communications
        "admin_faq_broadcast_feature": "admin_faq_broadcast_feature_ans",

        # Ban Management
        "admin_faq_ban_process": "admin_faq_ban_process_ans",
        "admin_faq_appeal_review": "admin_faq_appeal_review_ans",
        "admin_faq_ban_tools": "admin_faq_ban_tools_ans"
    }

    try:
        question_key = query.data.split("_", 3)[3]
        answer_key = faq_answers[question_key]

        question = get_translation(user_id, question_key)
        answer = get_translation(user_id, answer_key)

        # Get category index from user data
        category_index = context.user_data.get('current_admin_category', 0)  # Retrieve category
        keyboard = [
            [InlineKeyboardButton("🔙 Back", callback_data=f"admin_faq_cat_{category_index}")]
        ]

        message = (
            f"❓ {question}\n\n"
            f"✅ {answer}"
        )

        await query.edit_message_text(
            text=message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        return ADMIN_FAQ_QUESTION

    except Exception as e:
        await query.edit_message_text(text=f"⚠️ Error: {str(e)}")
        return ADMIN_FAQ_CATEGORY


async def show_contact_options(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)

    # Get categories from database
    categories = db.get_contact_categories()

    # Create keyboard with categories
    keyboard = []
    for category in categories:
        keyboard.append([
            InlineKeyboardButton(
                f"{category['emoji']} {get_translation(user_id, category['name_key'])}",
                callback_data=f"contact_category_{category['id']}"
            )
        ])

    # Add back button
    keyboard.append([
        InlineKeyboardButton(
            f"🔙 {get_translation(user_id, 'back_to_help')}",
            callback_data="contact_back"
        )
    ])

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Build message with some statistics (if user has previous contacts)
    user_stats = db.get_user_contact_stats(user_id)
    message = (
        f"📩 {get_translation(user_id, 'contact_admin_title')}\n\n"
        f"{get_translation(user_id, 'contact_admin_intro')}\n\n"
    )

    if user_stats:
        message += (
            f"📊 {get_translation(user_id, 'your_contact_stats')}:\n"
            f"  • {get_translation(user_id, 'total_messages')}: {user_stats['total']}\n"
            f"  • {get_translation(user_id, 'pending_messages')}: {user_stats['pending']}\n"
            f"  • {get_translation(user_id, 'answered_messages')}: {user_stats['answered']}\n\n"
        )

    message += get_translation(user_id, 'select_contact_category')

    if update.callback_query:
        await update.callback_query.edit_message_text(
            text=message,
            reply_markup=reply_markup
        )
    else:
        await context.bot.send_message(
            chat_id=user_id,
            text=message,
            reply_markup=reply_markup
        )

    return CONTACT_CATEGORY


async def handle_contact_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = get_user_id(update)

    if query.data == "contact_back":
        return await show_help(update, context)

    # Extract category ID from callback data
    category_id = int(query.data.split("_")[-1])
    context.user_data['contact_category'] = category_id

    # Ask for message priority
    keyboard = [
        [
            InlineKeyboardButton(
                f"🟢 {get_translation(user_id, 'priority_normal')}",
                callback_data="contact_priority_1"
            ),
            InlineKeyboardButton(
                f"🟡 {get_translation(user_id, 'priority_high')}",
                callback_data="contact_priority_2"
            ),
            InlineKeyboardButton(
                f"🔴 {get_translation(user_id, 'priority_urgent')}",
                callback_data="contact_priority_3"
            )
        ],
        [
            InlineKeyboardButton(
                f"🔙 {get_translation(user_id, 'back_to_categories')}",
                callback_data="contact_back_to_categories"
            )
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text=f"{get_translation(user_id, 'select_priority')}\n\n"
             f"ℹ️ {get_translation(user_id, 'priority_explanation')}",
        reply_markup=reply_markup
    )

    return CONTACT_PRIORITY


async def handle_contact_priority(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = get_user_id(update)

    if query.data == "contact_back_to_categories":
        return await show_contact_options(update, context)

    # Store priority in user data
    priority = int(query.data.split("_")[-1])
    context.user_data['contact_priority'] = priority

    # Ask for the actual message
    await query.edit_message_text(
        text=f"✍️ {get_translation(user_id, 'write_your_message')}\n\n"
             f"📝 {get_translation(user_id, 'message_guidelines')}:\n"
             f"- {get_translation(user_id, 'be_specific')}\n"
             f"- {get_translation(user_id, 'include_details')}\n"
             f"- {get_translation(user_id, 'avoid_spam')}\n\n"
             f"⏳ {get_translation(user_id, 'response_time')}: "
             f"{get_translation(user_id, 'within_24_hours')}\n\n"
             f"❌ /cancel - {get_translation(user_id, 'cancel_contact')}"
    )

    return CONTACT_MESSAGE


async def handle_contact_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = get_user_id(update)
    message_text = update.message.text

    # Check for cancel command
    if message_text.lower() == "/cancel":
        await update.message.reply_text(get_translation(user_id, 'contact_cancelled'))
        return await show_help(update, context)

    # Save to database
    category_id = context.user_data.get('contact_category')
    priority = context.user_data.get('contact_priority', 1)

    message_id = db.save_contact_message(
        user_id=user_id,
        category_id=category_id,
        message_text=message_text,
        priority=priority
    )

    # # Function to escape HTML special characters
    # def escape_html(text: str) -> str:
    #     return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    def get_user_profile_link_html(user_id: int) -> str:
        """Creates an HTML-formatted link to the user's profile"""
        return f'<a href="tg://user?id={user_id}">User #{user_id}</a>'

    # Notify admins
    active_admins = get_all_admins()
    category_name = escape_html(db.get_category_name(category_id))
    safe_message_text = escape_html(message_text)
    user_profile_link = get_user_profile_link_html(user_id)
    admin_notification = (
        f"<b>🚨 New Contact Message ({priority_emoji(priority)})</b>\n\n"
        f"👤 <b>User</b>: {user_profile_link}\n"
        f"📋 <b>Category</b>: {category_name}\n"
        f"🔢 <b>Message ID</b>: {message_id}\n\n"
        f"📝 <b>Message</b>:\n<code>{safe_message_text[:500]}</code>"  # Truncate very long messages
    )

    for admin_id in active_admins:
        try:
            keyboard = [
                [InlineKeyboardButton(
                    "📩 Reply",
                    callback_data=f"admin_reply_{message_id}"
                )]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await context.bot.send_message(
                chat_id=admin_id,
                text=admin_notification,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        except Exception as e:
            logging.error(f"Failed to notify admin {admin_id}: {e}")
            # Fallback to plain text if HTML fails
            plain_text = (
                f"New Contact Message ({priority_emoji(priority)})\n\n"
                f"User: {user_profile_link.replace('<', '').replace('>', '')}\n"
                f"Category: {category_name}\n"
                f"Message ID: {message_id}\n\n"
                f"Message:\n{safe_message_text[:500]}"
            )
            await context.bot.send_message(
                chat_id=admin_id,
                text=plain_text,
                reply_markup=reply_markup
            )

    # Confirm to user (using plain text)
    confirmation = (
        f"✅ {get_translation(user_id, 'message_received')}\n\n"
        f"📋 {get_translation(user_id, 'category')}: {category_name}\n"
        f"🔢 {get_translation(user_id, 'ticket_number')}: #{message_id}\n\n"
        f"{get_translation(user_id, 'response_time_notice')}\n\n"
        f"📬 {get_translation(user_id, 'contact_follow_up_info')}"
    )

    await update.message.reply_text(confirmation)

    return await show_help(update, context)
def priority_emoji(priority):
    """Get emoji for priority level"""
    return {1: "🟢", 2: "🟡", 3: "🔴"}.get(priority, "⚪")

def get_user_profile_link(user_id: int) -> str:
    """
    Creates a Markdown-formatted link to the user's profile.
    Format: [User #12345](tg://user?id=12345)
    This will show as a clickable "User #12345" that opens a chat with the user when clicked.
    """
    return f"[User #{user_id}](tg://user?id={user_id})"


async def admin_reply_to_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    admin_id = get_user_id(update)
    user_id = get_user_id(update)
    message_id = int(query.data.split("_")[-1])

    # Get message details
    message = db.get_contact_message(message_id)
    if not message:
        await query.edit_message_text("❌ Message not found")
        return

    # Store in context
    context.user_data['admin_reply_message_id'] = message_id
    context.user_data['admin_reply_user_id'] = message['user_id']

    def get_user_profile_link_html(user_id: int) -> str:
        """Creates an HTML-formatted link to the user's profile"""
        return f'<a href="tg://user?id={user_id}">User #{user_id}</a>'
    user_profile_link = get_user_profile_link_html(user_id)

    # Show message details and ask for reply
    await query.edit_message_text(
        text=f"📩 Replying to message #{message_id}\n\n"
              f"👤 <b>User</b>: {user_profile_link}\n"
             f"📋 Category: {message['category_name']}\n"
             f"📝 Original message:\n{message['message_text']}\n\n"
             f"✍️ Please write your reply:",
        parse_mode="Markdown"
    )

    return ADMIN_REPLY_STATE


async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('admin_reply'):
        await update.message.reply_text("❌ No message to reply to. Start over.")
        return ConversationHandler.END

    reply_text = update.message.text
    message_id = context.user_data['admin_reply']['message_id']
    user_id = context.user_data['admin_reply']['user_id']
    admin_id = get_user_id(update)

    try:
        # Send to user
        await context.bot.send_message(
            chat_id=user_id,
            text=f"💌 Admin reply to your message #{message_id}:\n\n{reply_text}"
        )

        # Update database
        db.update_contact_message(
            message_id=message_id,
            admin_id=admin_id,
            response=reply_text,
            status='answered'
        )

        # Confirm to admin
        await update.message.reply_text(
            f"✅ Reply sent to user successfully!\n"
            f"Message ID: #{message_id}"
        )

    except Exception as e:
        logging.error(f"Failed to send admin reply: {e}")
        await update.message.reply_text("❌ Failed to send reply. Please try again.")

    # Clean up
    context.user_data.pop('admin_reply', None)
    return ConversationHandler.END


async def handle_admin_reply_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # Extract message ID from callback data (format: "admin_reply_123")
    try:
        message_id = int(query.data.split('_')[-1])
    except (IndexError, ValueError):
        await query.edit_message_text("❌ Invalid message reference")
        return

    # Get the original contact message from database
    contact_message = db.get_contact_message(message_id)
    if not contact_message:
        await query.edit_message_text("❌ Message not found in database")
        return

    # Store in context for the reply flow
    context.user_data['admin_reply'] = {
        'message_id': message_id,
        'user_id': contact_message['user_id'],
        'original_text': contact_message['message_text']
    }

    user_id = get_user_id(update)

    def get_user_profile_link_html(user_id: int) -> str:
        """Creates an HTML-formatted link to the user's profile"""
        return f'<a href="tg://user?id={user_id}">User #{user_id}</a>'
    user_profile_link = get_user_profile_link_html(user_id)

    # Ask admin for their reply text
    await query.edit_message_text(
        text=f"✍️ Replying to message #{message_id}\n\n"
             f"👤 <b>User</b>: {user_profile_link}\n"
             f"📝 Original message:\n{contact_message['message_text']}\n\n"
             f"Please write your reply below:",
        parse_mode="Markdown"
    )

    return ADMIN_REPLY_STATE

async def cancel_contact_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the contact request process and return to help menu"""
    user_id = get_user_id(update)

    # Clear any stored contact data
    context.user_data.pop('contact_category', None)
    context.user_data.pop('contact_priority', None)

    await update.message.reply_text(
        get_translation(user_id, 'contact_cancelled'),
        reply_markup=ReplyKeyboardRemove()
    )
    return await show_help(update, context)


async def cancel_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the admin reply process"""
    admin_id = get_user_id(update)

    # Clear admin reply data
    message_id = context.user_data.pop('admin_reply_message_id', None)
    context.user_data.pop('admin_reply_user_id', None)

    if message_id:
        await update.message.reply_text(
            f"❌ Reply to message #{message_id} cancelled.",
            reply_markup=ReplyKeyboardRemove()
        )
    else:
        await update.message.reply_text(
            "Reply process cancelled.",
            reply_markup=ReplyKeyboardRemove()
        )

    return ConversationHandler.END


async def show_contact_management_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id

    # Get statistics for dashboard
    stats = db.get_contact_stats()

    # Create interactive buttons
    buttons = [
        [
            InlineKeyboardButton("📥 Inbox", callback_data="contact_inbox"),
            InlineKeyboardButton("📤 Outbox", callback_data="contact_outbox")
        ],
        [
            InlineKeyboardButton("🔄 Pending", callback_data="contact_pending"),
            InlineKeyboardButton("✅ Answered", callback_data="contact_answered")
        ],
        [
            InlineKeyboardButton("🔍 Search", callback_data="contact_search"),
            InlineKeyboardButton("📊 Stats", callback_data="contact_stats")
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data="contact_back_to_menu")
        ]
    ]

    reply_markup = InlineKeyboardMarkup(buttons)

    dashboard_message = (
        f"📨 <b>Contact Management</b>\n\n"
        f"📊 <i>Message Statistics:</i>\n"
        f"  • 📥 Inbox: {stats['total']}\n"
        f"  • 🔄 Pending: {stats['pending']}\n"
        f"  • ✅ Answered: {stats['answered']}\n"
        f"  • ⏳ Avg Response: {stats['avg_response_time']} hrs\n\n"
        f"Select an option to manage messages:"
    )

    # Check if this is a callback query or a new message
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            text=dashboard_message,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
    else:
        await context.bot.send_message(
            chat_id=user_id,
            text=dashboard_message,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )

    return CONTACT_MANAGEMENT


async def show_contact_inbox(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    # Get paginated messages (10 per page)
    page = context.user_data.get('contact_page', 1)
    messages = db.get_paginated_messages(status='all', page=page)

    # Build message list with action buttons
    message_text = "📥 <b>Inbox</b>\n\n"
    buttons = []

    for msg in messages:
        # Safely retrieve priority with a default value of 1
        priority_icon = {1: "🟢", 2: "🟡", 3: "🔴"}.get(msg.get('priority', 1), "⚪")

        # Safely retrieve status and assign an icon
        status = msg.get('status', 'unknown')  # Default to 'unknown' if status is missing
        status_icon = "🔄" if status == 'pending' else "✅"

        # Safely retrieve category with a default value of "Unknown"
        category = msg.get('category', "Unknown")

        # Append the button with all details
        buttons.append([
            InlineKeyboardButton(
                f"{priority_icon} #{msg['id']} - {category} - {status_icon} {status}",
                callback_data=f"contact_view_{msg['id']}"
            )
        ])

    # Add pagination controls
    pagination_row = []
    if page > 1:
        pagination_row.append(
            InlineKeyboardButton("⬅️ Previous", callback_data=f"contact_page_{page - 1}")
        )
    if len(messages) == 10:  # Assuming 10 items per page
        pagination_row.append(
            InlineKeyboardButton("Next ➡️", callback_data=f"contact_page_{page + 1}")
        )

    if pagination_row:
        buttons.append(pagination_row)

    buttons.append([
        InlineKeyboardButton("🔙 Back", callback_data="contact_back_to_dashboard")
    ])

    reply_markup = InlineKeyboardMarkup(buttons)

    await query.edit_message_text(
        text=message_text + f"Page {page}\nSelect a message to view:",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )

    return CONTACT_INBOX


async def view_contact_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    message_id = int(query.data.split('_')[-1])
    message = db.get_contact_message_details(message_id)

    # Prepare action buttons
    buttons = []
    if message['status'] == 'pending':
        buttons.append([
            InlineKeyboardButton("✍️ Reply", callback_data=f"contact_reply_{message_id}"),
            InlineKeyboardButton("✅ Mark Answered", callback_data=f"contact_close_{message_id}")
        ])
    else:
        buttons.append([
            InlineKeyboardButton("🗑️ Delete", callback_data=f"contact_delete_{message_id}"),
            InlineKeyboardButton("📝 Follow Up", callback_data=f"contact_followup_{message_id}")
        ])

    buttons.append([
        InlineKeyboardButton("🔙 Back", callback_data="contact_back_to_inbox")
    ])

    reply_markup = InlineKeyboardMarkup(buttons)

    user_id = get_user_id(update)

    def get_user_profile_link_html(user_id: int) -> str:
        """Creates an HTML-formatted link to the user's profile"""
        return f'<a href="tg://user?id={user_id}">User #{user_id}</a>'

    user_profile_link = get_user_profile_link_html(user_id)

    message_details = (
        f"📄 <b>Message #{message_id}</b>\n\n"
         f"👤 <b>User</b>: {user_profile_link}\n"
        f"📋 <b>Category:</b> {message['category']}\n"
        f"⏱️ <b>Received:</b> {message['created_at']}\n"
        f"🏷️ <b>Status:</b> {message['status']}\n\n"
        f"📝 <b>Message:</b>\n{message['text']}\n\n"
    )

    if message['status'] == 'answered':
        message_details += (
            f"👨‍💼 <b>Answered by:</b> {message['admin']}\n"
            f"⏱️ <b>Answered at:</b> {message['answered_at']}\n"
            f"📝 <b>Response:</b>\n{message['response']}\n"
        )

    await query.edit_message_text(
        text=message_details,
        reply_markup=reply_markup,
        parse_mode="HTML"
    )

    return CONTACT_VIEW_MESSAGE


async def show_contact_outbox(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    page = context.user_data.get('contact_page', 1)
    messages = db.get_paginated_messages(status='answered', page=page)

    message_text = "📤 <b>Outbox (Answered Messages)</b>\n\n"
    buttons = []

    for msg in messages:
        # Safely retrieve priority with a default value of 1
        priority_icon = {1: "🟢", 2: "🟡", 3: "🔴"}.get(msg.get('priority', 1), "⚪")

        # Safely retrieve category with a default value of "Unknown"
        category = msg.get('category', "Unknown")

        # Safely retrieve created_at with a default value of None
        created_at = msg.get('created_at')
        formatted_date = format_date(created_at) if created_at else "Unknown Date"

        # Append the button with all details
        buttons.append([
            InlineKeyboardButton(
                f"{priority_icon} #{msg['id']} - {category} - {formatted_date}",
                callback_data=f"contact_view_{msg['id']}"
            )
        ])

    # Add pagination controls
    buttons = add_pagination_buttons(buttons, page)
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="contact_back_to_dashboard")])

    await query.edit_message_text(
        text=message_text + f"Page {page}\nSelect a message to view:",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="HTML"
    )

    return CONTACT_OUTBOX


def add_pagination_buttons(buttons, current_page):
    """Add pagination controls to button list"""
    pagination_row = []
    if current_page > 1:
        pagination_row.append(
            InlineKeyboardButton("⬅️ Previous", callback_data=f"contact_page_{current_page - 1}")
        )
    pagination_row.append(
        InlineKeyboardButton(f"Page {current_page}", callback_data="current_page")
    )
    pagination_row.append(
        InlineKeyboardButton("Next ➡️", callback_data=f"contact_page_{current_page + 1}")
    )

    buttons.append(pagination_row)
    return buttons


def format_date(timestamp):
    """Format timestamp for display"""
    if not timestamp:
        return "N/A"
    return datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S").strftime("%b %d, %H:%M")




async def show_contact_pending(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    page = context.user_data.get('contact_page', 1)
    messages = db.get_paginated_messages(status='pending', page=page)

    message_text = "🔄 <b>Pending Messages</b>\n\n"
    buttons = []

    for msg in messages:
        # Safely retrieve priority with a default value of 1
        priority_icon = {1: "🟢", 2: "🟡", 3: "🔴"}.get(msg.get('priority', 1), "⚪")

        # Safely retrieve category with a default value of "Unknown"
        category = msg.get('category', "Unknown")

        # Append the button with all details
        buttons.append([
            InlineKeyboardButton(
                f"{priority_icon} #{msg.get('id', 'Unknown')} - {category}",
                callback_data=f"contact_view_{msg.get('id', 'Unknown')}"
            )
        ])

    # Add pagination buttons outside the loop
    buttons = add_pagination_buttons(buttons, page)
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="contact_back_to_dashboard")])

    await query.edit_message_text(
        text=message_text + f"Page {page}\nSelect a message to view:",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="HTML"
    )

    return CONTACT_PENDING


async def show_contact_answered(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    page = context.user_data.get('contact_page', 1)
    messages = db.get_paginated_messages(status='answered', page=page)

    message_text = "✅ <b>Answered Messages</b>\n\n"
    buttons = []

    for msg in messages:
        # Safely retrieve priority with a default value of 1
        priority_icon = {1: "🟢", 2: "🟡", 3: "🔴"}.get(msg.get('priority', 1), "⚪")

        # Safely retrieve category with a default value of "Unknown"
        category = msg.get('category', "Unknown")

        # Append the button with all details
        buttons.append([
            InlineKeyboardButton(
                f"{priority_icon} #{msg.get('id', 'Unknown')} - {category}",
                callback_data=f"contact_view_{msg.get('id', 'Unknown')}"
            )
        ])

    buttons = add_pagination_buttons(buttons, page)
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="contact_back_to_dashboard")])

    await query.edit_message_text(
        text=message_text + f"Page {page}\nSelect a message to view:",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="HTML"
    )

    return CONTACT_ANSWERED


async def show_contact_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    stats = db.get_contact_stats()
    category_stats = db.get_category_stats()

    stats_message = (
        "📊 <b>Contact Statistics</b>\n\n"
        f"📥 <b>Total Messages:</b> {stats['total']}\n"
        f"🔄 <b>Pending:</b> {stats['pending']}\n"
        f"✅ <b>Answered:</b> {stats['answered']}\n"
        f"⏱️ <b>Avg Response Time:</b> {stats['avg_response_time']} hours\n\n"
        "<b>By Category:</b>\n"
    )

    for cat in category_stats:
        stats_message += (
            f"  • {cat['emoji']} {cat['name']}: "
            f"{cat['count']} ({cat['percentage']}%)\n"
        )

    buttons = [[InlineKeyboardButton("🔙 Back", callback_data="contact_back_to_dashboard")]]

    await query.edit_message_text(
        text=stats_message,
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="HTML"
    )

    return CONTACT_STATS


async def start_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    message_id = int(query.data.split('_')[-1])
    message = db.get_contact_message_details(message_id)

    context.user_data['admin_reply'] = {
        'message_id': message_id,
        'user_id': message['user_id']
    }
    user_id = get_user_id(update)

    def get_user_profile_link_html(user_id: int) -> str:
        """Creates an HTML-formatted link to the user's profile"""
        return f'<a href="tg://user?id={user_id}">User #{user_id}</a>'

    user_profile_link = get_user_profile_link_html(user_id)

    await query.edit_message_text(
        text=f"✍️ <b>Replying to message #{message_id}</b>\n\n"
             f"👤 <b>User</b>: {user_profile_link}\n"
             f"📝 Original message:\n{message['text']}\n\n"
             f"Please write your reply below:\n\n"
             f"<i>Type /cancel to abort</i>",
        parse_mode="HTML"
    )

    return ADMIN_REPLY_STATE


async def close_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    message_id = int(query.data.split('_')[-1])
    admin_id = get_user_id(update)

    if db.update_contact_message(
            message_id=message_id,
            admin_id=admin_id,
            status='answered',
            response="Closed without reply"  # Changed from answer_text to response
    ):
        await query.edit_message_text(
            text=f"✅ Ticket #{message_id} marked as answered",
            parse_mode="HTML"
        )
    else:
        await query.edit_message_text(
            text=f"❌ Failed to update ticket #{message_id}",
            parse_mode="HTML"
        )

    return await show_contact_inbox(update, context)


async def delete_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    message_id = int(query.data.split('_')[-1])

    # First get message details for confirmation
    message = db.get_contact_message_details(message_id)

    context.user_data['delete_confirmation'] = {
        'message_id': message_id,
        'message_text': message['text']
    }

    buttons = [
        [InlineKeyboardButton("❗ Confirm Delete", callback_data=f"contact_confirm_delete_{message_id}")],
        [InlineKeyboardButton("🔙 Cancel", callback_data=f"contact_view_{message_id}")]
    ]
    user_id = get_user_id(update)

    def get_user_profile_link_html(user_id: int) -> str:
        """Creates an HTML-formatted link to the user's profile"""
        return f'<a href="tg://user?id={user_id}">User #{user_id}</a>'

    user_profile_link = get_user_profile_link_html(user_id)
    await query.edit_message_text(
        text=f"🗑️ <b>Confirm Deletion</b>\n\n"
             f"Message #{message_id}\n"
             f"From: {user_profile_link}\n\n"
             f"<b>Message content:</b>\n{message['text'][:300]}...\n\n"
             f"<i>This action cannot be undone!</i>",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="HTML"
    )

    return CONTACT_CONFIRM_DELETE


async def follow_up_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    message_id = int(query.data.split('_')[-1])
    message = db.get_contact_message_details(message_id)

    context.user_data['admin_reply'] = {
        'message_id': message_id,
        'user_id': message['user_id'],
        'is_followup': True
    }

    await query.edit_message_text(
        text=f"✍️ <b>Follow-up on message #{message_id}</b>\n\n"
             f"👤 User: {get_user_profile_link(message['user_id'])}\n"
             f"📝 Original message:\n{message['text']}\n\n"
             f"💬 Previous response:\n{message['response']}\n\n"
             f"Please write your follow-up message below:\n\n"
             f"<i>Type /cancel to abort</i>",
        parse_mode="HTML"
    )

    return ADMIN_REPLY_STATE


async def confirm_delete_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    message_id = int(query.data.split('_')[-1])
    delete_data = context.user_data.get('delete_confirmation', {})

    if delete_data.get('message_id') != message_id:
        await query.edit_message_text("❌ Invalid delete confirmation")
        return await show_contact_inbox(update, context)

    # Actually delete from database
    success = db.delete_contact_message(message_id)

    if success:
        await query.edit_message_text(
            text=f"🗑️ Message #{message_id} deleted successfully",
            parse_mode="HTML"
        )
    else:
        await query.edit_message_text(
            text=f"❌ Failed to delete message #{message_id}",
            parse_mode="HTML"
        )

    # Clear delete context
    context.user_data.pop('delete_confirmation', None)
    return await show_contact_inbox(update, context)


async def handle_pagination_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    page = int(query.data.split('_')[-1])
    context.user_data['contact_page'] = page

    # Determine which view we're in based on current state
    current_state = context.user_data.get('current_state')

    if current_state == CONTACT_OUTBOX:
        return await show_contact_outbox(update, context)
    elif current_state == CONTACT_PENDING:
        return await show_contact_pending(update, context)
    elif current_state == CONTACT_ANSWERED:
        return await show_contact_answered(update, context)
    else:  # Default to inbox
        return await show_contact_inbox(update, context)


# Rating
from datetime import date
today = date.today().isoformat()


async def show_rate_options(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show enhanced rating menu with visual improvements"""
    user_id = get_user_id(update)

    # Check rating capabilities with progress indicators
    rating_stats = db.get_user_rating_stats(user_id)
    can_rate_bot = True
    can_rate_users = db.has_any_application(user_id)

    # Build dynamic menu with visual indicators
    menu_text = "🌟 <b>Rating Center</b> 🌟\n\n"
    menu_text += f"📊 Your Rating Stats:\n"
    menu_text += f"• Given Reviews by You: {rating_stats['total_reviews']}\n"
    menu_text += f"• Avg Rating Given: {rating_stats['average_rating']:.1f}⭐\n\n"
    menu_text += "Choose an option:"

    keyboard = [
        [InlineKeyboardButton("⭐ Rate Our Bot", callback_data="rate_bot")] if can_rate_bot else [],
        [InlineKeyboardButton("👥 Rate Users", callback_data="rate_user")] if can_rate_users else [],
        [InlineKeyboardButton("📊 My Review History", callback_data="my_reviews")],
        [InlineKeyboardButton("🔍 Explore Reviews", callback_data="search_reviews")],
        [InlineKeyboardButton("⚙️ Privacy Settings", callback_data="review_settings")],
        [InlineKeyboardButton("📈 Rating Statistics", callback_data="rating_stats")],
        [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
    ]

    # Remove any empty rows
    keyboard = [row for row in keyboard if row]

    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.edit_message_text(
            text=menu_text,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text(
            text=menu_text,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )

    return RATE_OPTIONS


async def start_rate_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle rating initiation with alert-style duplicate checks"""
    query = update.callback_query
    await query.answer()

    try:
        user_id = get_user_id(update)

        # Get rateable users first
        rateable_users = db.get_rateable_users(user_id)

        if not rateable_users:
            await query.edit_message_text(
                "ℹ️ You need to interact with users before rating them.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Back", callback_data="back_to_rate_menu")]
                ])
            )
            return RATE_OPTIONS

        # Filter out already-rated users today
        rateable_users = [
            user for user in rateable_users
            if not db.has_user_reviewed(user_id, user['id'], user['type'])
        ]

        if not rateable_users:
            await query.edit_message_text(
                "⏳ You've already rated all available users today.\nPlease try again tomorrow.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Back to Rating Menu", callback_data="back_to_rate_menu")]
                ])
            )
            return RATE_OPTIONS

        # Store rateable users in context
        context.user_data["rateable_users"] = rateable_users

        # Show user selection interface
        keyboard = []
        for user in rateable_users:
            button_text = f"{user['name']} ({user['type'].replace('_', ' ')})"
            callback_data = f"select_to_rate_{user['id']}_{user['type']}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])

        keyboard.append([InlineKeyboardButton("Back", callback_data="back_to_rate_menu")])

        await query.edit_message_text(
            "Select a user to rate:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return SELECT_USER_FOR_RATING

    except Exception as e:
        logging.error(f"Rating initiation error: {str(e)}")
        await query.answer(
            "⚠️ Couldn't start rating process. Please try again.",
            show_alert=True
        )
        return RATE_OPTIONS


async def handle_user_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle when a user is selected for rating"""
    query = update.callback_query
    await query.answer()

    try:
        # Parse callback data (format: select_to_rate_123_employer)
        parts = query.data.split('_')
        if len(parts) != 5 or parts[0] != 'select' or parts[1] != 'to' or parts[2] != 'rate':
            raise ValueError("Invalid selection format")

        target_id = int(parts[3])
        target_type = parts[4]

        # Validate target type
        if target_type not in ['employer', 'job_seeker']:
            raise ValueError(f"Invalid user type: {target_type}")

        # Check if already rated today
        user_id = get_user_id(update)
        if db.has_user_reviewed(user_id, target_id, target_type):
            await query.edit_message_text(
                "⏳ You've already reviewed this user today!\nPlease try again tomorrow.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Back to Selection", callback_data="back_to_rate_menu")]
                ])
            )
            return RATE_OPTIONS

        # Set up rating dimensions based on type
        rating_dimensions = {
            'employer': {
                'professionalism': 'Professionalism',
                'communication': 'Communication',
                'hiring_process': 'Hiring Process'
            },
            'job_seeker': {
                'reliability': 'Reliability',
                'skills': 'Skill Match',
                'communication': 'Communication'
            }
        }

        # Store in context
        context.user_data.update({
            'review_target': target_id,
            'target_type': target_type,
            'rating_dimensions': rating_dimensions[target_type]
        })

        # Start with first dimension
        first_dim = next(iter(rating_dimensions[target_type]))
        await show_dimension_rating(update, context, first_dim)
        return RATE_DIMENSION

    except Exception as e:
        logging.error(f"User selection error: {str(e)}")
        await query.edit_message_text(
            "⚠️ Error selecting user. Please try again.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Back to Selection", callback_data="back_to_rate_menu")]
            ])
        )
        return RATE_OPTIONS


async def show_user_search_interface(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show advanced user search interface"""
    keyboard = [
        [InlineKeyboardButton("🔍 Search by Name", callback_data="search_by_name")],
        [InlineKeyboardButton("🏢 Employers Only", callback_data="filter_reviews_employer")],  # Add "reviews_"
        [InlineKeyboardButton("👤 Job Seekers Only", callback_data="filter_reviews_job_seeker")],  # Add "reviews_"
        [InlineKeyboardButton("⭐ Top Rated", callback_data="sort_reviews_top")],  # Change to "sort_reviews_top"
        [InlineKeyboardButton("🔄 Most Recent", callback_data="sort_reviews_recent")],  # Add "reviews_"
        [InlineKeyboardButton("🔙 Back", callback_data="back_to_rate_menu")]
    ]

    await update.callback_query.edit_message_text(
        text="Search for user to rate:\n\n"
             "You can rate:\n"
             "- Employers you've applied to\n"
             "- Job seekers you've interacted with",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def show_rating_interface(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show the actual rating interface with multi-dimensional options"""
    query = update.callback_query
    target_id = int(query.data.split("_")[-1])
    target_type = context.user_data["target_type"]

    # Store in context
    context.user_data["review_target"] = target_id
    context.user_data["target_type"] = target_type

    # Build rating dimensions based on target type
    if target_type == "bot":
        dimensions = {
            "ease_of_use": "Ease of Use",
            "features": "Feature Completeness",
            "support": "Support Quality"
        }
    elif target_type == "employer":
        dimensions = {
            "professionalism": "Professionalism",
            "communication": "Communication",
            "hiring_process": "Hiring Process"
        }
    else:  # job_seeker
        dimensions = {
            "reliability": "Reliability",
            "skills": "Skill Match",
            "communication": "Communication"
        }

    context.user_data["rating_dimensions"] = dimensions

    # Show first rating dimension
    first_dim = next(iter(dimensions))
    await show_dimension_rating(update, context, first_dim)
    return RATE_DIMENSION


async def show_dimension_rating(update: Update, context: ContextTypes.DEFAULT_TYPE, dimension: str):
    """Show rating interface for a specific dimension"""
    dimensions = context.user_data["rating_dimensions"]

    await update.callback_query.edit_message_text(
        text=f"How would you rate for {dimensions[dimension]}?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⭐" * i, callback_data=f"rate_{dimension}_{i}")
             for i in range(1, 6)],
            [InlineKeyboardButton("Skip", callback_data=f"skip_{dimension}")]
        ])
    )


async def handle_rating_submission(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Finalize review submission with all checks"""
    query = update.callback_query
    await query.answer()
    user_id = get_user_id(update)

    try:
        # Verify required data exists
        if not all(key in context.user_data for key in ["review_target", "target_type"]):
            raise KeyError("Missing review data in context")

        # Anti-abuse checks
        if not db.can_user_review(
                user_id,
                context.user_data["review_target"],
                context.user_data["target_type"]
        ):
            await query.answer("You've reached your daily review limit", show_alert=True)
            return await show_rate_options(update, context)

        # Compile all ratings
        ratings = context.user_data.get("dimension_ratings", {})
        if not ratings:
            await query.answer("Please complete at least one rating dimension", show_alert=True)
            return RATE_DIMENSION

        overall = sum(ratings.values()) / len(ratings)
        context.user_data["overall_rating"] = overall

        # Build confirmation message
        confirmation_text = "📝 Review Summary\n\n"
        confirmation_text += "\n".join(
            f"{dim.capitalize()}: {'⭐' * rating}"
            for dim, rating in ratings.items()
        )
        confirmation_text += f"\n\nOverall Rating: {overall:.1f}⭐"

        await query.edit_message_text(
            text=confirmation_text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Confirm", callback_data="confirm_review")],
                [InlineKeyboardButton("✏️ Edit Review", callback_data="edit_review")],
                [InlineKeyboardButton("🔙 Back", callback_data="back_to_rate_menu")]
            ])
        )
        return CONFIRM_REVIEW

    except Exception as e:
        logging.error(f"Error in rating submission: {str(e)}")
        await query.edit_message_text(
            "⚠️ Error processing your review. Please try again.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Try Again", callback_data="rate_menu")]
            ])
        )
        return RATE_OPTIONS


async def finalize_review(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Finalize review with complete context validation"""
    try:
        # Validate all required context data
        required_keys = ["review_target", "target_type", "overall_rating", "dimension_ratings"]
        if not all(key in context.user_data for key in required_keys):
            missing = [k for k in required_keys if k not in context.user_data]
            raise ValueError(f"Missing review data in context: {missing}")

        # Prepare review data
        review_data = {
            "reviewer_id": get_user_id(update),
            "target_id": context.user_data["review_target"],
            "target_type": context.user_data["target_type"],
            "rating": round(context.user_data["overall_rating"]),
            "comment": context.user_data.get("review_comment", ""),
            "dimension_ratings": context.user_data["dimension_ratings"]
        }

        # Check if this is an edit
        if "editing_review" in context.user_data:
            review_id = context.user_data["editing_review"]
            if not db.update_review(review_id, review_data):
                raise ValueError("Failed to update review in database")
            success_text = "✅ Review updated successfully!"
        else:
            if not db.add_review(**review_data):
                raise ValueError("Failed to save review to database")
            success_text = "✅ Review submitted successfully!"

        # Success message
        target_name = "the bot" if review_data["target_type"] == "bot" else db.get_user_name(review_data["target_id"])
        text = (
            f"{success_text}\n\n"
            f"Review of {target_name}\n"
            f"Rating: {'⭐' * review_data['rating']}\n"
        )

        # Add dimension ratings if available
        if review_data["dimension_ratings"]:
            text += "\nDetailed Ratings:\n"
            for dim, rating in review_data["dimension_ratings"].items():
                if rating > 0:  # Only show rated dimensions
                    dim_name = dim.replace('_', ' ').title()
                    text += f"{dim_name}: {'⭐' * rating}\n"

        if review_data["comment"]:
            text += f"\nYour comment: {review_data['comment']}"

        # Navigation buttons
        keyboard = [
            [InlineKeyboardButton("📊 View My Reviews", callback_data="post_review_my_reviews")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="post_review_main_menu")]
        ]

        if update.callback_query:
            await update.callback_query.edit_message_text(
                text=text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await update.message.reply_text(
                text=text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        # Clear context
        for key in required_keys + ["editing_review"]:
            context.user_data.pop(key, None)

        return POST_REVIEW

    except Exception as e:
        logging.error(f"Error finalizing review: {e}")
        error_msg = "⚠️ Failed to process review. Please try again."
        if update.callback_query:
            await update.callback_query.edit_message_text(error_msg)
        else:
            await update.message.reply_text(error_msg)
        return RATE_OPTIONS


async def start_rate_bot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Initialize bot rating process with alert-style duplicate check"""
    query = update.callback_query
    await query.answer()

    try:
        user_id = get_user_id(update)

        # Check if already rated
        if db.has_user_reviewed(user_id, "bot", "bot"):
            await query.edit_message_text(
                "⏳ You've already reviewed the bot today.\nPlease try again tomorrow.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Back to Rating Menu", callback_data="back_to_rate_menu")]
                ])
            )
            return RATE_OPTIONS
        context.user_data.update({
            "target_type": "bot",
            "review_target": "bot",
            "rating_dimensions": {
                "ease_of_use": "Ease of Use",
                "features": "Feature Completeness",
                "support": "Support Quality"
            }
        })

        await show_dimension_rating(update, context, "ease_of_use")
        return RATE_DIMENSION

    except Exception as e:
        logging.error(f"Bot rating initiation error: {str(e)}")
        await query.answer(
            "⚠️ Couldn't start bot rating process. Please try again.",
            show_alert=True
        )
        return RATE_OPTIONS


async def show_review_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show review search interface"""
    keyboard = [
        [InlineKeyboardButton("🔍 Search by Name", callback_data="search_by_name")],
        [InlineKeyboardButton("🏢 Employers Only", callback_data="filter_employers")],
        [InlineKeyboardButton("👤 Job Seekers Only", callback_data="filter_jobseekers")],
        [InlineKeyboardButton("⭐ Top Rated", callback_data="sort_top_rated")],
        [InlineKeyboardButton("🔄 Most Recent", callback_data="sort_recent")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_to_rate_menu")]
    ]

    await update.callback_query.edit_message_text(
        text="Search reviews by:\n\n"
             "Filter by user type or sort order",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return SEARCH_REVIEWS


async def filter_employers(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Filter to show only employers"""
    query = update.callback_query
    await query.answer()

    context.user_data["current_filter"] = "employer"
    rateable_users = [u for u in context.user_data.get("rateable_users", [])
                      if u.get("type") == "employer"]

    if not rateable_users:
        await query.edit_message_text(
            text="No employers found.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="back_to_search")]
            ])
        )
        return SELECT_USER_FOR_RATING

    keyboard = [
        [InlineKeyboardButton(f"{u['name']} (ID: {u['id']})", callback_data=f"select_user_{u['id']}")]
        for u in rateable_users
    ]
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_search")])

    await query.edit_message_text(
        text="Select an employer to rate:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return SELECT_USER_FOR_RATING


async def filter_jobseekers(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Filter to show only job seekers"""
    query = update.callback_query
    await query.answer()

    context.user_data["current_filter"] = "job_seeker"
    rateable_users = [u for u in context.user_data.get("rateable_users", [])
                      if u.get("type") == "job_seeker"]

    if not rateable_users:
        await query.edit_message_text(
            text="No job seekers found.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="back_to_search")]
            ])
        )
        return SELECT_USER_FOR_RATING

    keyboard = [
        [InlineKeyboardButton(f"{u['name']} (ID: {u['id']})", callback_data=f"select_user_{u['id']}")]
        for u in rateable_users
    ]
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_search")])

    await query.edit_message_text(
        text="Select a job seeker to rate:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return SELECT_USER_FOR_RATING

async def sort_top_rated(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Sort users by their average rating"""
    rateable_users = context.user_data["rateable_users"]

    # Add average rating to each user (pseudo-code - implement db.get_user_avg_rating)
    for user in rateable_users:
        user["avg_rating"] = db.get_user_avg_rating(user["id"])

    # Sort descending by rating
    sorted_users = sorted(rateable_users, key=lambda x: x["avg_rating"], reverse=True)

    keyboard = [
        [InlineKeyboardButton(
            f"{u['name']} (⭐{u['avg_rating']:.1f})",
            callback_data=f"select_user_{u['id']}"
        )]
        for u in sorted_users
    ]
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_search")])

    await update.callback_query.edit_message_text(
        text="Top rated users:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return SELECT_USER_FOR_RATING


async def sort_recent(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Sort users by most recently interacted with"""
    user_id = get_user_id(update)
    rateable_users = db.get_recently_interacted_users(user_id)  # Implement this DB function

    context.user_data["rateable_users"] = rateable_users

    keyboard = [
        [InlineKeyboardButton(f"{u['name']}", callback_data=f"select_user_{u['id']}")]
        for u in rateable_users
    ]
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_search")])

    await update.callback_query.edit_message_text(
        text="Recently interacted users:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return SELECT_USER_FOR_RATING


async def handle_dimension_rating(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store rating for a specific dimension and proceed to next"""
    query = update.callback_query
    await query.answer()

    try:
        parts = query.data.split('_')
        if parts[0] not in ['rate', 'edit_rate']:  # Handle both cases
            raise ValueError("Invalid callback prefix")

        dimension = '_'.join(parts[1:-1])
        rating_value = int(parts[-1])

        # Store in context
        if "dimension_ratings" not in context.user_data:
            context.user_data["dimension_ratings"] = {}
        context.user_data["dimension_ratings"][dimension] = rating_value

        # Rest of your existing flow...

        # Calculate overall rating (average of non-zero ratings)
        ratings = [v for v in context.user_data["dimension_ratings"].values() if v > 0]
        context.user_data["overall_rating"] = sum(ratings) / len(ratings) if ratings else 0

        # Get next unrated dimension
        dimensions = context.user_data["rating_dimensions"]
        remaining_dims = [d for d in dimensions if d not in context.user_data["dimension_ratings"]]

        if remaining_dims:
            await show_dimension_rating(update, context, remaining_dims[0])
            return RATE_DIMENSION
        else:
            await query.edit_message_text(
                text="Would you like to add an optional comment?",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Yes", callback_data="add_comment")],
                    [InlineKeyboardButton("❌ No", callback_data="skip_comment")]
                ])
            )
            return ADD_COMMENT_OPTIONAL

    except Exception as e:
        logging.error(f"Error processing rating: {str(e)}")
        await query.edit_message_text(
            "⚠️ Sorry, there was an error processing your rating.\n\n"
            "Please try rating again or use /cancel to exit.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Try Again", callback_data="back_to_rate_menu")]
            ])
        )
        return RATE_OPTIONS


async def skip_dimension_rating(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Skip rating for current dimension with proper parsing"""
    query = update.callback_query
    await query.answer()

    try:
        # Extract dimension being skipped (format: skip_dimension_name)
        parts = query.data.split("_")
        dimension = "_".join(parts[1:])  # Handle multi-word dimensions

        # Mark as skipped (0 rating)
        if "dimension_ratings" not in context.user_data:
            context.user_data["dimension_ratings"] = {}
        context.user_data["dimension_ratings"][dimension] = 0

        # Get next dimension to rate
        dimensions = context.user_data["rating_dimensions"]
        rated_dims = set(context.user_data["dimension_ratings"].keys())
        remaining_dims = [d for d in dimensions if d not in rated_dims]

        if remaining_dims:
            next_dim = remaining_dims[0]
            await show_dimension_rating(update, context, next_dim)
            return RATE_DIMENSION
        else:
            # All dimensions processed (some may be skipped)
            ratings = [v for v in context.user_data["dimension_ratings"].values() if v > 0]
            if ratings:  # Only calculate if we have at least one rating
                context.user_data["overall_rating"] = sum(ratings) / len(ratings)
            else:
                await query.answer("Please rate at least one dimension", show_alert=True)
                return RATE_DIMENSION

            await query.edit_message_text(
                text="Would you like to add an optional comment?",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Yes", callback_data="add_comment")],
                    [InlineKeyboardButton("No", callback_data="skip_comment")]
                ])
            )
            return ADD_COMMENT_OPTIONAL

    except Exception as e:
        logging.error(f"Error skipping dimension: {e}")
        await query.answer("Error processing your request", show_alert=True)
        return RATE_DIMENSION


async def show_review_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Display review privacy settings with message change detection"""
    user_id = get_user_id(update)
    privacy_settings = db.get_review_privacy_settings(user_id)

    # Generate content
    text = "🔒 Review Privacy Settings\n\n"
    text += f"• Show Your Name: {'✅ ON' if privacy_settings['show_name'] else '❌ OFF'}\n"
    text += f"• Show Contact Info: {'✅ ON' if privacy_settings['show_contact'] else '❌ OFF'}\n\n"

    keyboard = [
        [InlineKeyboardButton("Toggle Name Visibility", callback_data="toggle_anonymous")],
        [InlineKeyboardButton("Toggle Contact Visibility", callback_data="toggle_contact_visible")],
        [InlineKeyboardButton("Back", callback_data="back_to_rate_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Check if message needs updating
    current_hash = hash((text, str(reply_markup)))
    if context.user_data.get("settings_msg_hash") == current_hash:
        return REVIEW_SETTINGS  # No changes needed

    try:
        await update.callback_query.edit_message_text(
            text=text,
            reply_markup=reply_markup
        )
        context.user_data["settings_msg_hash"] = current_hash
    except BadRequest as e:
        if "not modified" not in str(e):
            raise  # Only suppress "not modified" errors

    return REVIEW_SETTINGS


async def toggle_privacy_setting(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Toggle privacy setting with error handling"""
    try:
        query = update.callback_query
        await query.answer()

        setting = query.data.split("_")[-1]  # "anonymous" or "contact_visible"
        user_id = get_user_id(update)

        if setting == "anonymous":
            db.toggle_setting(user_id, "show_name")
        elif setting == "contact_visible":
            db.toggle_setting(user_id, "show_contact")

        # Clear message hash to force update
        context.user_data.pop("settings_msg_hash", None)

        return await show_review_settings(update, context)
    except Exception as e:
        logging.error(f"Error toggling setting: {e}")
        await query.edit_message_text("⚠️ Error updating settings. Please try again.")
        return REVIEW_SETTINGS

async def handle_user_search_for_rating(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle user search query for rating"""
    search_term = update.message.text.strip()
    user_id = get_user_id(update)

    try:
        # Search both employers and job seekers
        results = db.search_users(
            search_term,
            user_type=context.user_data.get("current_filter")  # Respect current filter
        )

        if not results:
            await context.bot.send_message(
                chat_id=user_id,
                text="No matching users found. Try a different search term."
            )
            return await show_user_search_interface(update, context)

        # Store for pagination
        context.user_data["search_results"] = results
        context.user_data["current_page"] = 1

        # Show first page
        return await display_search_results_page(update, context)

    except Exception as e:
        logging.error(f"User search error: {str(e)}")
        await context.bot.send_message(
            chat_id=user_id,
            text="An error occurred during search. Please try again."
        )
        return await show_rate_options(update, context)


async def display_search_results_page(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Display a page of search results"""
    results = context.user_data["search_results"]
    current_page = context.user_data["current_page"]
    per_page = 5
    start_idx = (current_page - 1) * per_page
    page_results = results[start_idx:start_idx + per_page]

    keyboard = []
    for user in page_results:
        btn_text = f"{user['name']} ({user['type'].capitalize()})"
        if user.get("avg_rating"):
            btn_text += f" ⭐{user['avg_rating']:.1f}"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"select_user_{user['id']}")])

    # Add pagination controls if needed
    if len(results) > per_page:
        pagination_row = []
        if current_page > 1:
            pagination_row.append(InlineKeyboardButton("◀️ Prev", callback_data="prev_page"))
        if len(results) > current_page * per_page:
            pagination_row.append(InlineKeyboardButton("Next ▶️", callback_data="next_page"))
        keyboard.append(pagination_row)

    keyboard.append([InlineKeyboardButton("Back to Search", callback_data="back_to_search")])

    text = f"Search Results (Page {current_page}):"
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await context.bot.send_message(
            chat_id=get_user_id(update),
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    return SELECT_USER_FOR_RATING


async def prompt_for_comment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Prompt user to enter an optional comment"""
    try:
        await update.callback_query.edit_message_text(
            text="📝 Optional Review Comment\n\n"
                 "Please share your experience (500 chars max):\n"
                 "• What stood out?\n"
                 "• What could improve?\n"
                 "• Any specific feedback?\n\n"
                 "Or click below to skip:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⏩ Skip Comment", callback_data="skip_comment")]
            ])
        )
        return PROMPT_FOR_COMMENT
    except Exception as e:
        logging.error(f"Error in prompt_for_comment: {e}")
        await update.callback_query.answer("Error loading comment prompt", show_alert=True)
        return RATE_DIMENSION  # Fallback to previous state


async def submit_comment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle submitted comment"""
    try:
        comment = update.message.text.strip()
        if len(comment) > 500:
            await update.message.reply_text(
                "❌ Comment too long (max 500 characters). Please shorten it:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Skip Comment", callback_data="skip_comment")]
                ])
            )
            return PROMPT_FOR_COMMENT

        context.user_data["review_comment"] = comment
        return await finalize_review(update, context)

    except Exception as e:
        logging.error(f"Error submitting comment: {e}")
        await update.message.reply_text(
            "⚠️ Error processing your comment. Please try again:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Skip Comment", callback_data="skip_comment")]
            ])
        )
        return PROMPT_FOR_COMMENT


async def skip_comment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle skipping comment"""
    await update.callback_query.answer("Skipping comment")
    context.user_data["review_comment"] = None
    return await finalize_review(update, context)


async def cancel_comment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel comment entry"""
    await update.message.reply_text("Comment entry cancelled.")
    return await show_rate_options(update, context)


async def edit_review(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Allow user to edit their review before submission"""
    # Reset to first dimension
    dimensions = context.user_data["rating_dimensions"]
    first_dim = next(iter(dimensions))
    context.user_data["dimension_ratings"] = {}

    await show_dimension_rating(update, context, first_dim)
    return RATE_DIMENSION


async def show_my_reviews(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Display all reviews written by the current user"""
    user_id = get_user_id(update)
    reviews = db.get_user_reviews(user_id)

    if not reviews:
        await update.callback_query.edit_message_text(
            text="You haven't written any reviews yet.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Back", callback_data="back_to_rate_menu")]
            ])
        )
        return MY_REVIEWS

    keyboard = []
    for review in reviews:
        target_name = db.get_user_name(review['target_id']) if review['target_type'] != 'bot' else "JobBot"
        btn_text = f"{'⭐' * review['rating']} {target_name}"
        if review['comment']:
            btn_text += " 💬"
        keyboard.append([
            InlineKeyboardButton(btn_text, callback_data=f"review_{review['id']}")
        ])

    keyboard.append([InlineKeyboardButton("Back", callback_data="back_to_rate_menu")])

    await update.callback_query.edit_message_text(
        text="Your Reviews:\n\nSelect one to view details",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return MY_REVIEWS


async def show_review_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show detailed view of a specific review"""
    try:
        review_id = int(update.callback_query.data.split('_')[1])
        review = db.get_review_details(review_id)

        if not review:
            await update.callback_query.answer("Review not found", show_alert=True)
            return await show_my_reviews(update, context)

        target_name = db.get_user_name(review['target_id']) if review['target_type'] != 'bot' else "JobBot"

        # Parse date string if needed
        created_at = review['created_at']
        if isinstance(created_at, str):
            from datetime import datetime
            created_at = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")

        text = (
            f"Review of {target_name}\n"
            f"Rating: {'⭐' * review['rating']}\n"
            f"Date: {created_at.strftime('%Y-%m-%d')}\n\n"
            f"{review['comment'] or 'No comment provided'}"
        )

        keyboard = [
            [InlineKeyboardButton("✏️ Edit", callback_data=f"edit_review_{review_id}")],
            [InlineKeyboardButton("🗑️ Delete", callback_data=f"delete_review_{review_id}")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_to_my_reviews")]
        ]

        await update.callback_query.edit_message_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return REVIEW_DETAILS

    except Exception as e:
        logging.error(f"Error showing review details: {e}")
        await update.callback_query.answer("Error loading review", show_alert=True)
        return await show_my_reviews(update, context)


async def delete_review(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle review deletion with confirmation"""
    review_id = int(update.callback_query.data.split('_')[2])
    context.user_data["review_to_delete"] = review_id

    await update.callback_query.edit_message_text(
        text="Are you sure you want to delete this review?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Yes, delete", callback_data="confirm_delete")],
            [InlineKeyboardButton("❌ Cancel", callback_data=f"review_{review_id}")]
        ])
    )
    return REVIEW_DETAILS


async def confirm_delete_review(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle confirmed review deletion"""
    try:
        review_id = context.user_data.get("review_to_delete")
        if not review_id:
            raise ValueError("No review to delete in context")

        if db.delete_review(review_id):
            await update.callback_query.edit_message_text(
                text="✅ Review deleted successfully!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Back to Rating ", callback_data="back_to_rate_menu")]
                ])
            )
        else:
            raise Exception("Failed to delete review from database")

        return MY_REVIEWS

    except Exception as e:
        logging.error(f"Error deleting review: {e}")
        await update.callback_query.edit_message_text(
            "⚠️ Failed to delete review. Please try again.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Back", callback_data="back_to_my_reviews")]
            ])
        )
        return MY_REVIEWS


async def edit_existing_review(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start editing an existing review with all dimensions"""
    review_id = int(update.callback_query.data.split('_')[2])
    review = db.get_review_details(review_id)

    # Store original data in context
    context.user_data.update({
        "editing_review": review_id,
        "target_type": review['target_type'],
        "review_target": review['target_id'],
        "dimension_ratings": {}  # Start fresh
    })

    # Set up rating dimensions based on type
    rating_dimensions = {
        'employer': {
            'professionalism': 'Professionalism',
            'communication': 'Communication',
            'hiring_process': 'Hiring Process'
        },
        'job_seeker': {
            'reliability': 'Reliability',
            'skills': 'Skill Match',
            'communication': 'Communication'
        },
        'bot': {
            'ease_of_use': 'Ease of Use',
            'features': 'Feature Completeness',
            'support': 'Support Quality'
        }
    }

    context.user_data["rating_dimensions"] = rating_dimensions[review['target_type']]

    # Start with first dimension
    first_dim = next(iter(context.user_data["rating_dimensions"]))
    await show_dimension_rating(update, context, first_dim)
    return RATE_DIMENSION


async def handle_review_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle search query for reviews"""
    try:
        if update.message:  # Handle text message
            search_term = update.message.text.strip()
            user_id = update.message.from_user.id
            message_func = context.bot.send_message
        else:  # Handle callback query
            query = update.callback_query
            await query.answer()
            search_term = query.data.split('_', 1)[1] if '_' in query.data else ""
            user_id = query.from_user.id
            message_func = query.edit_message_text

        current_filter = context.user_data.get("review_filter", "all")
        sort_method = context.user_data.get("review_sort", "recent")

        results = db.search_reviews(
            search_term=search_term,
            target_type=current_filter if current_filter != "all" else None,
            sort_by=sort_method
        )

        if not results:
            await message_func(
                chat_id=user_id,
                text="No reviews found matching your search."
            )
            return await show_review_search(update, context)

        context.user_data["review_results"] = results
        context.user_data["current_review_page"] = 0

        return await display_review_results(update, context)

    except Exception as e:
        logging.error(f"Review search error: {e}")
        await context.bot.send_message(
            chat_id=user_id,
            text="An error occurred during search. Please try again."
        )
        return await show_rate_options(update, context)

async def filter_reviews(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Apply filter to review search"""
    query = update.callback_query
    await query.answer()

    # Determine filter type based on callback data
    if query.data == "filter_employers":
        context.user_data["review_filter"] = "employer"
    elif query.data == "filter_jobseekers":
        context.user_data["review_filter"] = "job_seeker"
    else:
        # Handle unexpected cases
        await query.edit_message_text("Invalid filter option")
        return SEARCH_REVIEWS

    # Refresh the display if we have existing results
    if "review_results" in context.user_data:
        return await display_review_results(update, context)
    else:
        return await show_review_search(update, context)


async def sort_reviews(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Change sorting method for reviews"""
    query = update.callback_query
    await query.answer()

    # Determine sort method based on callback data
    if query.data == "sort_top_rated":
        sort_method = "top"
    elif query.data == "sort_recent":
        sort_method = "recent"
    else:
        # Handle unexpected cases
        await query.edit_message_text("Invalid sort option")
        return SEARCH_REVIEWS

    context.user_data["review_sort"] = sort_method

    # Refresh the display if we have existing results
    if "review_results" in context.user_data:
        # Re-sort existing results
        if sort_method == "recent":
            context.user_data["review_results"].sort(key=lambda x: x['created_at'], reverse=True)
        elif sort_method == "top":
            context.user_data["review_results"].sort(key=lambda x: x['rating'], reverse=True)
        # Add other sort methods if needed

        return await display_review_results(update, context)
    else:
        return await show_review_search(update, context)

async def flag_review(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle flagging of inappropriate reviews"""
    review_id = int(update.callback_query.data.split('_')[-1])
    context.user_data["review_to_flag"] = review_id

    await update.callback_query.edit_message_text(
        text="Please select a reason for flagging this review:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Inappropriate Content", callback_data="flag_reason_inappropriate")],
            [InlineKeyboardButton("False Information", callback_data="flag_reason_false")],
            [InlineKeyboardButton("Conflict of Interest", callback_data="flag_reason_conflict")],
            [InlineKeyboardButton("Cancel", callback_data=f"review_{review_id}")]
        ])
    )
    return REVIEW_DETAILS


async def display_review_results(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Display paginated review search results"""
    results = context.user_data["review_results"]
    page = context.user_data["current_review_page"]
    per_page = 5
    start_idx = page * per_page
    page_results = results[start_idx:start_idx + per_page]
    keyboard = []

    for review in page_results:
        target_name = db.get_user_name(review['target_id']) if review['target_type'] != 'bot' else "JobBot"
        reviewer_name = "Anonymous" if review['is_anonymous'] else db.get_user_name(review['reviewer_id'])
        btn_text = f"{'⭐' * review['rating']} {target_name} by {reviewer_name}"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"view_review_{review['id']}")])

    # Pagination controls
    pagination_row = []
    if page > 0:
        pagination_row.append(InlineKeyboardButton("◀️ Previous", callback_data="prev_review_page"))
    if len(results) > (page + 1) * per_page:
        pagination_row.append(InlineKeyboardButton("Next ▶️", callback_data="next_review_page"))
    if pagination_row:
        keyboard.append(pagination_row)

    # Filter/sort controls
    keyboard.append([
        InlineKeyboardButton("Filter", callback_data="review_filter_menu"),
        InlineKeyboardButton("Sort", callback_data="review_sort_menu")
    ])
    keyboard.append([InlineKeyboardButton("Back", callback_data="back_to_rate_menu")])

    await update.callback_query.edit_message_text(
        text=f"Review Results (Page {page + 1}):",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return SEARCH_REVIEWS

async def next_page(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle next page in search results"""
    context.user_data["current_page"] += 1
    return await display_search_results_page(update, context)

async def previous_page(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle previous page in search results"""
    context.user_data["current_page"] = max(1, context.user_data["current_page"] - 1)
    return await display_search_results_page(update, context)

async def handle_search_by_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Prompt user to enter name for search"""
    await update.callback_query.edit_message_text(
        text="Please enter the name you want to search for:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="back_to_search")]
        ])
    )
    return SEARCH_REVIEWS  # or a new state if you prefer

#error handling
import traceback
from typing import Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes


async def advanced_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Advanced error handler with logging and admin notifications"""
    # Prepare error details
    error = context.error
    tb_list = traceback.format_exception(None, error, error.__traceback__)
    tb_string = "".join(tb_list)

    # Extract user and chat information if available
    user_id: Optional[int] = None
    chat_id: Optional[int] = None
    command: Optional[str] = None

    if update and hasattr(update, 'effective_user'):
        user_id = update.effective_user.id
    if update and hasattr(update, 'effective_chat'):
        chat_id = update.effective_chat.id
    if update and hasattr(update, 'message') and update.message and update.message.text:
        command = update.message.text.split()[0] if update.message.text else None

    # Prepare error data for database
    error_data = {
        "user_id": user_id,
        "chat_id": chat_id,
        "command": command,
        "error_type": error.__class__.__name__,
        "error_message": str(error),
        "traceback": tb_string,
        "context_data": dict(context.user_data) if context.user_data else None,
        "update_data": update.to_dict() if update and hasattr(update, 'to_dict') else None
    }

    # Log error to database
    error_id = db.log_error(error_data)

    # Notify user (if possible)
    if user_id:
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text="⚠️ An unexpected error occurred. Our team has been notified and will fix it soon."
            )
        except Exception as e:
            logging.error(f"Could not notify user about error: {e}")

    # Notify all admins
    await notify_admins_about_error(context, error_id, error_data)


async def notify_admins_about_error(context: ContextTypes.DEFAULT_TYPE, error_id: str, error_data: dict) -> None:
    """Notify all admins about the error with action buttons"""
    admin_ids = get_all_admins()
    if not admin_ids:
        return

    # Safely get error message
    error_message = str(error_data.get('error_message', 'Unknown error'))
    short_error = f"{error_data.get('error_type', 'Error')}: {error_message[:200]}"

    keyboard = [
        [InlineKeyboardButton("View Details", callback_data=f"view_error_{error_id}"),
         InlineKeyboardButton("Mark as Fixed", callback_data=f"resolve_error_{error_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    for admin_id in admin_ids:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=f"🚨 New Bot Error ({error_id[:8]}):\n\n{short_error}",
                reply_markup=reply_markup
            )
        except Exception as e:
            logging.error(f"Could not notify admin {admin_id} about error: {str(e)}")


async def view_system_errors(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show list of system errors"""
    query = update.callback_query
    await query.answer()

    errors = db.get_errors(limit=10)

    if not errors:
        await query.edit_message_text(text="No errors found in the system.")
        return DATABASE_MANAGEMENT

    keyboard = []
    for error in errors:
        # Format timestamp
        try:
            timestamp = datetime.fromisoformat(error.get('timestamp', ''))
            time_display = timestamp.strftime('%m/%d %H:%M')
        except (ValueError, TypeError):
            time_display = "Unknown time"

        short_msg = f"{error.get('error_type', 'Error')}: {error.get('error_message', '')[0:30]}..."
        btn = InlineKeyboardButton(
            f"{time_display} - {short_msg}",
            callback_data=f"error_detail_{error.get('error_id', '')}"
        )
        keyboard.append([btn])

    keyboard.append([InlineKeyboardButton("Back", callback_data="back_to_database_menu")])

    await query.edit_message_text(
        text="Recent System Errors:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return VIEW_ERRORS

import html
async def handle_error_detail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show detailed error information with expandable traceback"""
    query = update.callback_query
    await query.answer()

    error_id = query.data.split("_")[-1]
    error = db.get_error_by_id(error_id)

    if not error:
        await query.edit_message_text(text="Error details not found.")
        return VIEW_ERRORS

    # Format basic error info
    try:
        timestamp = datetime.fromisoformat(error['timestamp'])
        time_display = timestamp.strftime('%Y-%m-%d %H:%M:%S')
    except (ValueError, KeyError):
        time_display = "Unknown time"

    basic_info = (
        f"🚨 <b>Error ID</b>: <code>{html.escape(str(error.get('error_id', 'Unknown')))}</code>\n"
        f"⏰ <b>Time</b>: {html.escape(time_display)}\n"
        f"👤 <b>User</b>: <code>{html.escape(str(error.get('user_id', 'N/A')))}</code>\n"
        f"📝 <b>Command</b>: <code>{html.escape(str(error.get('command', 'N/A')))}</code>\n"
        f"🔧 <b>Status</b>: {html.escape(error.get('status', 'unresolved'))}\n\n"
        f"💥 <b>Error Type</b>: <code>{html.escape(str(error.get('error_type', 'Unknown')))}</code>\n"
        f"📄 <b>Message</b>:\n<code>{html.escape(str(error.get('error_message', 'No message')))}</code>\n\n"
    )

    # Prepare context info
    context_info = "<b>🔍 Context</b>:\n"
    if error.get('context_data'):
        # Convert context data to JSON and escape it for HTML
        context_data = json.dumps(error.get('context_data'), indent=2)[:1000]
        escaped_context_data = html.escape(context_data)
        context_info += f"<pre>{escaped_context_data}</pre>\n\n"
    else:
        context_info += "No context data\n\n"

    # Prepare traceback info
    traceback_info = ""
    if error.get('traceback'):
        traceback_lines = error['traceback'].split('\n')
        short_traceback = "\n".join(traceback_lines[:10])  # Show first 10 lines initially
        traceback_info = (
            f"<b>🔎 Traceback (first 10 lines):</b>\n"
            f"<pre>{html.escape(short_traceback)}</pre>\n\n"
            f"<i>Full traceback available below</i>\n\n"
        )

    # Create keyboard with expand/collapse options
    keyboard = [
        [InlineKeyboardButton("📜 Show Full Traceback", callback_data=f"show_traceback_{error_id}")],
        [InlineKeyboardButton("📋 Show Update Data", callback_data=f"show_update_{error_id}")],
        [
            InlineKeyboardButton("✅ Mark Fixed", callback_data=f"resolve_error_{error_id}"),
            InlineKeyboardButton("🔙 Back to List", callback_data="view_system_errors")
        ]
    ]

    # Send initial message
    await query.edit_message_text(
        text=basic_info + context_info + traceback_info,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )
    return ERROR_DETAIL


async def show_full_traceback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show full error traceback"""
    query = update.callback_query
    await query.answer()

    error_id = query.data.split("_")[-1]
    error = db.get_error_by_id(error_id)

    if not error or not error.get('traceback'):
        await query.answer("No traceback available")
        return ERROR_DETAIL

    # Escape HTML special characters
    full_traceback = html.escape(error['traceback'])

    # Split into multiple messages if too long
    if len(full_traceback) > 4000:
        parts = [full_traceback[i:i + 4000] for i in range(0, len(full_traceback), 4000)]
        for part in parts:
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=f"<pre>{part}</pre>",
                parse_mode="HTML"
            )
        await query.answer("Sent full traceback in multiple messages")
    else:
        await query.edit_message_text(
            text=f"<b>Full Traceback:</b>\n<pre>{full_traceback}</pre>",
            parse_mode="HTML"
        )

    return ERROR_DETAIL


async def show_update_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the 'Show Update Data' button press"""
    query = update.callback_query
    await query.answer()

    error_id = query.data.split('_')[-1]  # Extract error_id from callback_data

    try:
        # 1. Get error details from database
        error = db.get_error_by_id(error_id)
        if not error or not error.get('update_data'):
            await query.answer("⚠️ No update data available", show_alert=True)
            return ERROR_DETAIL

        # 2. Format the JSON data
        update_data = error['update_data']
        if isinstance(update_data, str):
            try:
                update_data = json.loads(update_data)
            except json.JSONDecodeError:
                pass

        pretty_data = json.dumps(update_data, indent=2, ensure_ascii=False)

        # 3. Send the data (split if too large)
        if len(pretty_data) > 4000:
            await query.answer("Sending large update data in parts...")
            for i in range(0, len(pretty_data), 4000):
                part = pretty_data[i:i + 4000]
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=f"<pre>{html.escape(part)}</pre>",
                    parse_mode="HTML"
                )
        else:
            await query.edit_message_text(
                text=f"📋 <b>Update Data for Error {error_id[:8]}:</b>\n<pre>{html.escape(pretty_data)}</pre>",
                parse_mode="HTML"
            )

    except Exception as e:
        logging.error(f"Error showing update data: {str(e)}")
        await query.answer("❌ Failed to load update data", show_alert=True)

    return ERROR_DETAIL

async def resolve_error(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Mark an error as resolved"""
    query = update.callback_query
    await query.answer()

    error_id = query.data.split("_")[-1]
    success = db.update_error_status(error_id, "fixed")

    if success:
        await query.edit_message_text(text=f"✅ Error {error_id[:8]} marked as fixed.")
    else:
        await query.edit_message_text(text="❌ Failed to update error status.")

    return DATABASE_MANAGEMENT

# Conversation Handler
def main():
    application = Application.builder().token("7567203189:AAEu1NDdQ0-b8dI39zOwFIdoQ8SUyF5K5p0").build()

    # Conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start),
            CommandHandler("admin", admin_start),
            CommandHandler("review_appeal", review_appeal)],
        states={
            LANGUAGE: [CallbackQueryHandler(set_language)],
            MOBILE: [MessageHandler(filters.CONTACT, save_mobile)],
            REGISTRATION_TYPE: [CallbackQueryHandler(registration_type)],
            JOB_SEEKER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, job_seeker_full_name),
            ],
            JOB_SEEKER_DOB: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, job_seeker_dob),
            ],
            JOB_SEEKER_GENDER: [
                CallbackQueryHandler(job_seeker_gender, pattern="^(male|female)$"),
            ],
            JOB_SEEKER_CONTACT_NUMBERS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, job_seeker_contact_numbers),
            ],
            JOB_SEEKER_LANGUAGES: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, job_seeker_languages),
            ],
            JOB_SEEKER_QUALIFICATION: [
                CallbackQueryHandler(job_seeker_qualification,
                                     pattern="^(certificate|diploma|degree|ma|phd|other|skip)$"),
            ],
            JOB_SEEKER_FIELD_OF_STUDY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, job_seeker_field_of_study),
                CallbackQueryHandler(job_seeker_field_of_study, pattern="^(skip)$"),
            ],
            JOB_SEEKER_CGPA: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, job_seeker_cgpa),
                CallbackQueryHandler(job_seeker_cgpa, pattern="^(skip)$"),
            ],
            JOB_SEEKER_SKILLS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, job_seeker_skills),
                CallbackQueryHandler(job_seeker_skills, pattern="^(skip)$"),
            ],
            JOB_SEEKER_PROFILE_SUMMARY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, job_seeker_profile_summary),
                CallbackQueryHandler(job_seeker_profile_summary, pattern="^(skip)$"),
            ],
            JOB_SEEKER_SUPPORTING_DOCUMENTS: [
                MessageHandler(filters.Document.ALL, job_seeker_supporting_documents),
                CallbackQueryHandler(job_seeker_supporting_documents, pattern="^(skip)$"),
            ],
            JOB_SEEKER_PORTFOLIO_LINK: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, job_seeker_portfolio_link),
                CallbackQueryHandler(job_seeker_portfolio_link, pattern="^(skip)$"),
            ],
            MAIN_MENU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_main_menu),
            ],
            PROFILE_MENU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_profile_actions),
            ],
            VIEW_PROFILE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, view_profile),
            ],
            EDIT_PROFILE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, display_edit_menu),
            ],
            CONFIRM_DELETE_ACCOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_delete_confirmation),
            ],
            CONFIRM_CHANGE_LANGUAGE: [
                CallbackQueryHandler(change_language_confirmed, pattern="^change_language_confirmed$"),
                CallbackQueryHandler(cancel_change_language, pattern="^cancel_change_language$")
            ],
            SELECT_LANGUAGE: [
                CallbackQueryHandler(handle_language_selection)
            ],
            EDIT_PROFILE: [
                CallbackQueryHandler(handle_field_selection)
            ],
            SAVE_EDITED_FIELD: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_edited_field)],
            EDIT_FIELD_VALUE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_edited_field),
                MessageHandler(filters.Document.ALL, save_edited_field)
            ],
            EMPLOYER_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_employer_name)
            ],
            EMPLOYER_LOCATION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_employer_location)
            ],
            EMPLOYER_TYPE: [
                CallbackQueryHandler(save_employer_type)
            ],
            ABOUT_COMPANY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_about_company),
                CallbackQueryHandler(save_about_company, pattern="^(skip)$")
            ],
            VERIFICATION_DOCUMENTS: [
                MessageHandler(filters.Document.ALL, upload_verification_documents),
                CallbackQueryHandler(upload_verification_documents, pattern="^(skip)$")
            ],
            EMPLOYER_MAIN_MENU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_employer_main_menu),

                CallbackQueryHandler(
                    handle_vacancy_actions,
                    pattern=r"^(view_apps|close|resubmit|stats|renew)_\d+$"
                ),
                CallbackQueryHandler(
                    view_analytics,
                    pattern="^view_analytics$"
                )
            ],
            EMPLOYER_PROFILE_MENU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_employer_profile_actions),
            ],
            CONFIRM_DELETE_MY_ACCOUNT: [MessageHandler(filters.TEXT, handle_my_delete_confirmation)],
            SELECT_EMPLOYER_LANGUAGE: [CallbackQueryHandler(handle_employer_language_selection)],
            CONFIRM_CHANGE_EMPLOYER_LANGUAGE: [CallbackQueryHandler(change_employer_language_confirmed)],

            SELECT_JOB_TO_MANAGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, select_job_to_manage)
            ],

            HANDLE_JOB_ACTIONS: [
                CallbackQueryHandler(handle_job_actions, pattern=r"^(view_apps|close|stats|renew)_\d+$")
            ],

            VIEW_APPLICATIONS: [
                CallbackQueryHandler(fetch_and_display_applicants, pattern=r"^view_apps_"),
                CallbackQueryHandler(export_to_excel, pattern=r"^export_excel_"),
                CallbackQueryHandler(handle_applicant_review, pattern=r"^review_\d+$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, select_applicant)
            ],
            ACCEPT_REJECT_CONFIRMATION: [
                CallbackQueryHandler(handle_accept_reject, pattern="^accept_applicant$|^reject_applicant$"),
                CallbackQueryHandler(handle_cv_download, pattern=r"^download_cv_\d+$")
            ],
            REJECTION_REASON_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_rejection_reason_application)
            ],
            EMPLOYER_MESSAGE_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_employer_message)
            ],

            CONFIRM_CLOSE: [
                MessageHandler(filters.Regex("^(Yes|No)$"), handle_close_confirmation)
            ],
            RESUBMIT_CONFIRMATION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_resubmit)
            ],
            RENEW_VACANCY: [
                CallbackQueryHandler(handle_renew_duration, pattern=r"^renew_(30|60|custom)$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_custom_renew_duration)
            ],
            CONFIRM_RENEWAL: [
                CallbackQueryHandler(process_renewal_confirmation, pattern="^(confirm|cancel)_renew$")
            ],
            EDIT_EMPLOYER_PROFILE: [
                CallbackQueryHandler(handle_edit_employer_field)
            ],
            EDIT_EMPLOYER_FIELD_VALUE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_updated_employer_field),
                MessageHandler(filters.Document.ALL, save_updated_employer_field)
            ],
            #  new states for analytics
            ANALYTICS_VIEW: [
                CallbackQueryHandler(
                    handle_analytics_actions,
                    pattern=r"^(analytics_trends|analytics_demographics|analytics_response|analytics_benchmark|analytics_export|analytics_back|go_to_employer_main_menu)$"
                )
            ],
            ANALYTICS_TRENDS: [
                CallbackQueryHandler(
                    handle_analytics_back,
                    pattern="^back_to_analytics$"
                )
            ],
            ANALYTICS_DEMOGRAPHICS: [
                CallbackQueryHandler(
                    handle_analytics_back,
                    pattern="^back_to_analytics$"
                )
            ],
            ANALYTICS_RESPONSE: [
                CallbackQueryHandler(
                    handle_analytics_back,
                    pattern="^back_to_analytics$"
                )
            ],
            ANALYTICS_BENCHMARK: [
                CallbackQueryHandler(
                    handle_analytics_back,
                    pattern="^back_to_analytics$"
                )
            ],
            ANALYTICS_EXPORT: [
                CallbackQueryHandler(
                    handle_export_format,
                    pattern=r"^export_(csv|pdf|excel)$"
                ),
                CallbackQueryHandler(
                    handle_analytics_back,
                    pattern="^back_to_analytics$"
                )
            ],
            HELP_MENU: [
                CallbackQueryHandler(help_button_handler, pattern="^help_"),
                CallbackQueryHandler(handle_admin_reply_callback, pattern="^admin_reply_"),
            ],


            # New FAQ states
            FAQ_SECTION: [
                CallbackQueryHandler(show_faq_category_section, pattern="^faq_main_"),
                # Handles all main FAQ categories
                CallbackQueryHandler(handle_faq_category, pattern=r"^faq_category_\d+"),
                CallbackQueryHandler(show_help, pattern=r"^help_back$")  # New handler
            ],
            FAQ_CATEGORY: [
                CallbackQueryHandler(handle_faq_question, pattern="^faq_question_"),
                CallbackQueryHandler(show_faq_section, pattern="^faq_category_back$"),  # Back to FAQ Categories
            ],
            FAQ_QUESTION: [
                CallbackQueryHandler(handle_faq_category, pattern=r"^faq_question_back_\d+$"),
            ],
            # Job seeker FAQ states
            JS_FAQ_SECTION: [
                CallbackQueryHandler(handle_job_seeker_faq_category, pattern=r"^js_faq_category_\d+"),
                CallbackQueryHandler(show_faq_category_section, pattern=r"^js_faq_back$")
            ],
            JS_FAQ_CATEGORY: [
                CallbackQueryHandler(handle_job_seeker_faq_question, pattern=r"^js_faq_q_"),
                CallbackQueryHandler(show_job_seeker_faq, pattern=r"^js_faq_return_\d+$")
            ],
            JS_FAQ_QUESTION: [
                CallbackQueryHandler(handle_job_seeker_faq_category, pattern=r"^js_faq_return_\d+$")
            ],
            ADMIN_FAQ_SECTION: [
                CallbackQueryHandler(handle_admin_faq_category, pattern=r"^admin_faq_cat_\d+"),
                CallbackQueryHandler(show_faq_category_section, pattern=r"^admin_faq_back_to_main")
            ],
            ADMIN_FAQ_CATEGORY: [
                CallbackQueryHandler(handle_admin_faq_question, pattern=r"^admin_faq_q_"),
                CallbackQueryHandler(show_admin_faq, pattern=r"^admin_faq_return_\d+")  # Matches category back button
            ],
            ADMIN_FAQ_QUESTION: [
                CallbackQueryHandler(handle_admin_faq_category, pattern=r"^admin_faq_cat_\d+")
            ],
            RATE_OPTIONS: [
                CallbackQueryHandler(show_rate_options, pattern="^back_to_rate_menu$"),
                CallbackQueryHandler(start_rate_bot, pattern="^rate_bot$"),
                CallbackQueryHandler(start_rate_user, pattern="^rate_user$"),
                CallbackQueryHandler(show_my_reviews, pattern="^my_reviews$"),
                CallbackQueryHandler(show_review_search, pattern="^search_reviews$"),
                CallbackQueryHandler(show_review_settings, pattern="^review_settings$"),
                CallbackQueryHandler(main_menu, pattern="^back_to_main$")
            ],

            SEARCH_USER_FOR_RATING: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_review_search),
                CallbackQueryHandler(filter_employers, pattern="^filter_employers$"),
                CallbackQueryHandler(filter_jobseekers, pattern="^filter_jobseekers$"),
                CallbackQueryHandler(sort_top_rated, pattern="^sort_top_rated$"),
                CallbackQueryHandler(sort_recent, pattern="^sort_recent$"),
                CallbackQueryHandler(show_rate_options, pattern="^back_to_rate_menu$"),
                CallbackQueryHandler(handle_search_by_name, pattern="^search_by_name$"),
                CallbackQueryHandler(previous_page, pattern="^prev_page$"),
                CallbackQueryHandler(next_page, pattern="^next_page$")
            ],

            SELECT_USER_FOR_RATING: [
                CallbackQueryHandler(handle_user_selection, pattern=r"^select_user_\d+$"),
                CallbackQueryHandler(start_rate_user, pattern="^back_to_rate_menu$")
            ],

            RATE_DIMENSION: [
                CallbackQueryHandler(handle_dimension_rating, pattern=r"^rate_[a-z_]+_\d$"),
                CallbackQueryHandler(skip_dimension_rating, pattern=r"^skip_[a-z_]+$"),
                CallbackQueryHandler(show_rate_options, pattern="^cancel_rating$")
            ],
            PROMPT_FOR_COMMENT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, submit_comment),
                CallbackQueryHandler(skip_comment, pattern="^skip_comment$"),
                CommandHandler("cancel", cancel_comment)
            ],

            ADD_COMMENT_OPTIONAL: [
                CallbackQueryHandler(prompt_for_comment, pattern="^add_comment$"),
                CallbackQueryHandler(skip_comment, pattern="^skip_comment$")
            ],

            CONFIRM_REVIEW: [
                CallbackQueryHandler(finalize_review, pattern="^confirm_review$"),
                CallbackQueryHandler(edit_review, pattern="^edit_review$"),
                CallbackQueryHandler(show_rate_options, pattern="^cancel_review$")
            ],

            REVIEW_SETTINGS: [
                CallbackQueryHandler(toggle_privacy_setting, pattern=r"^toggle_(anonymous|contact_visible)$"),
                CallbackQueryHandler(show_rate_options, pattern="^back_to_rate_menu$")
            ],

            MY_REVIEWS: [
                CallbackQueryHandler(show_review_details, pattern=r"^review_\d+$"),
                CallbackQueryHandler(delete_review, pattern=r"^delete_review_\d+$"),
                CallbackQueryHandler(edit_existing_review, pattern=r"^edit_review_\d+$"),
                CallbackQueryHandler(show_rate_options, pattern="^back_to_rate_menu$")
            ],

            REVIEW_DETAILS: [
                CallbackQueryHandler(show_review_details, pattern=r"^review_\d+$"),
                CallbackQueryHandler(edit_existing_review, pattern=r"^edit_review_\d+$"),
                CallbackQueryHandler(delete_review, pattern=r"^delete_review_\d+$"),
                CallbackQueryHandler(confirm_delete_review, pattern="^confirm_delete$"),  # Add this
                CallbackQueryHandler(flag_review, pattern="^flag_review$"),
                CallbackQueryHandler(show_my_reviews, pattern="^back_to_my_reviews$")
            ],

            SEARCH_REVIEWS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_review_search),
                CallbackQueryHandler(filter_reviews, pattern=r"^filter_employers$"),
                CallbackQueryHandler(filter_reviews, pattern=r"^filter_jobseekers$"),
                CallbackQueryHandler(sort_reviews, pattern=r"^sort_top_rated$"),
                CallbackQueryHandler(sort_reviews, pattern=r"^sort_recent$"),
                CallbackQueryHandler(show_rate_options, pattern="^back_to_rate_menu$"),
                CallbackQueryHandler(handle_search_by_name, pattern="^search_by_name$")  # Add this new handler
            ],
            POST_REVIEW: [
                CallbackQueryHandler(show_my_reviews, pattern="^post_review_my_reviews$"),
                CallbackQueryHandler(show_rate_options, pattern="^post_review_main_menu$"),
                CallbackQueryHandler(show_rate_options, pattern="^post_review_back$")
            ],
            # ===== NEW CONTACT ADMIN STATES =====
            CONTACT_CATEGORY: [
                CallbackQueryHandler(handle_contact_category, pattern=r"^contact_category_\d+$"),
                CallbackQueryHandler(show_help, pattern=r"^contact_back$"),
            ],
            CONTACT_PRIORITY: [
                CallbackQueryHandler(handle_contact_priority, pattern=r"^contact_priority_[123]$"),
                CallbackQueryHandler(show_contact_options, pattern=r"^contact_back_to_categories$"),
            ],
            CONTACT_MESSAGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_contact_message),
                CommandHandler("cancel", cancel_contact_request),
            ],

            # Admin reply state
            ADMIN_REPLY_STATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_reply),
                CommandHandler("cancel", cancel_admin_reply),
            ],


            #Admin STates
            ADMIN_LOGIN: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, check_admin_credentials)
            ],
            ADMIN_MAIN_MENU: [
                # Handle admin menu choices (Manage Job Posts, Share Job Posts, etc.)
                MessageHandler(
                    filters.Regex("^(Manage Job Posts|View Reports|Broadcast|Database Management|Contact Management|Cancel|Share Job Posts)$"),
                    handle_admin_menu_choice),

                # Handle callback queries for approving or rejecting job posts
                CallbackQueryHandler(handle_admin_job_approval, pattern="^approve_|^reject_"),
            ],
            #contact feature
            CONTACT_MANAGEMENT: [
                CallbackQueryHandler(show_contact_inbox, pattern=r"^contact_inbox$"),
                CallbackQueryHandler(show_contact_outbox, pattern=r"^contact_outbox$"),
                CallbackQueryHandler(show_contact_pending, pattern=r"^contact_pending$"),
                CallbackQueryHandler(show_contact_answered, pattern=r"^contact_answered$"),
                CallbackQueryHandler(show_contact_stats, pattern=r"^contact_stats$"),
                CallbackQueryHandler(show_admin_menu, pattern=r"^contact_back_to_menu$"),
            ],

            CONTACT_CONFIRM_DELETE: [
                CallbackQueryHandler(confirm_delete_message, pattern=r"^contact_confirm_delete_\d+$"),
                CallbackQueryHandler(view_contact_message, pattern=r"^contact_view_\d+$"),
            ],

            CONTACT_INBOX: [
                CallbackQueryHandler(handle_pagination_contact, pattern=r"^contact_page_\d+$"),
                CallbackQueryHandler(show_contact_management_dashboard, pattern=r"^contact_back_to_dashboard$"),
                CallbackQueryHandler(view_contact_message, pattern=r"^contact_view_\d+$"),

            ],

            CONTACT_VIEW_MESSAGE: [
                CallbackQueryHandler(start_admin_reply, pattern=r"^contact_reply_\d+$"),
                CallbackQueryHandler(close_ticket, pattern=r"^contact_close_\d+$"),
                CallbackQueryHandler(delete_message, pattern=r"^contact_delete_\d+$"),
                CallbackQueryHandler(follow_up_message, pattern=r"^contact_followup_\d+$"),
                CallbackQueryHandler(show_contact_inbox, pattern=r"^contact_back_to_inbox$"),
                CallbackQueryHandler(show_contact_outbox, pattern=r"^contact_back_to_outbox$"),
                CallbackQueryHandler(show_contact_pending, pattern=r"^contact_back_to_pending$"),
                CallbackQueryHandler(show_contact_answered, pattern=r"^contact_back_to_answered$"),
            ],
            CONTACT_OUTBOX: [
                CallbackQueryHandler(handle_pagination_contact, pattern=r"^contact_page_\d+$"),
                CallbackQueryHandler(show_contact_management_dashboard, pattern=r"^contact_back_to_dashboard$"),
                CallbackQueryHandler(view_contact_message, pattern=r"^contact_view_\d+$"),
            ],
            CONTACT_PENDING: [
                CallbackQueryHandler(handle_pagination_contact, pattern=r"^contact_page_\d+$"),
                CallbackQueryHandler(show_contact_management_dashboard, pattern=r"^contact_back_to_dashboard$"),
                CallbackQueryHandler(view_contact_message, pattern=r"^contact_view_\d+$"),
            ],

            CONTACT_ANSWERED: [
                CallbackQueryHandler(handle_pagination_contact, pattern=r"^contact_page_\d+$"),
                CallbackQueryHandler(show_contact_management_dashboard, pattern=r"^contact_back_to_dashboard$"),
                CallbackQueryHandler(view_contact_message, pattern=r"^contact_view_\d+$"),
            ],

            CONTACT_STATS: [
                CallbackQueryHandler(show_contact_management_dashboard, pattern="^contact_back_to_dashboard$"),
            ],
            REJECT_JOB_REASON: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_rejection_reason)
            ],
            SELECT_JOB_POSTS_TO_SHARE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_share_job_posts),
            ],

            BROADCAST_TYPE: [
                CallbackQueryHandler(select_broadcast_type, pattern="^(job_seekers|employers|cancel)$")
            ],
            BROADCAST_MESSAGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_broadcast_message)
            ],
            CONFIRM_BROADCAST: [
                CallbackQueryHandler(confirm_broadcast, pattern="^(confirm|cancel)$")
            ],
            POST_JOB_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, post_job_title)],
            POST_EMPLOYMENT_TYPE: [CallbackQueryHandler(post_employment_type)],
            POST_GENDER: [CallbackQueryHandler(post_gender)],
            POST_QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, post_quantity)],
            POST_LEVEL: [CallbackQueryHandler(post_level)],
            POST_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, post_description)],
            POST_QUALIFICATION: [CallbackQueryHandler(post_qualification)],
            POST_SKILLS: [MessageHandler(filters.TEXT & ~filters.COMMAND, post_skills)],
            POST_SALARY: [MessageHandler(filters.TEXT & ~filters.COMMAND, post_salary)],
            POST_BENEFITS: [MessageHandler(filters.TEXT & ~filters.COMMAND, post_benefits)],
            POST_DEADLINE: [MessageHandler(filters.TEXT & ~filters.COMMAND, post_deadline)],
            JOB_PREVIEW: [MessageHandler(filters.TEXT & ~filters.COMMAND, job_preview)],
            CONFIRM_POST: [CallbackQueryHandler(confirm_post)],
            DISPLAY_VACANCIES: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, select_vacancy)
            ],
            SELECT_VACANCY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, select_vacancy)
            ],
            CONFIRM_SELECTION: [
                CallbackQueryHandler(confirm_selection, pattern="^(confirm|cancel)$")
            ],
            WRITE_COVER_LETTER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, write_cover_letter)
            ],
            CONFIRM_SUBMISSION: [
                CallbackQueryHandler(handle_confirmation, pattern="^confirm$|^cancel$")
            ],

            MANAGE_USERS: [
                CallbackQueryHandler(ban_job_seekers, pattern="^ban_job_seekers$"),
                CallbackQueryHandler(ban_employers, pattern="^ban_employers$"),
                CallbackQueryHandler(unban_users_menu, pattern="^unban_users_menu$"),                CallbackQueryHandler(view_banned_users, pattern="^view_banned_users$"),
                CallbackQueryHandler(remove_job_seekers, pattern="^remove_job_seekers$"),
                CallbackQueryHandler(remove_employers, pattern="^remove_employers$"),
                CallbackQueryHandler(remove_applications, pattern="^remove_applications$"),
                CallbackQueryHandler(export_job_seekers, pattern="^export_job_seekers$"),
                CallbackQueryHandler(export_employers, pattern="^export_employers$"),
                CallbackQueryHandler(export_applications, pattern="^export_applications$"),
                CallbackQueryHandler(back_to_admin_menu, pattern="^back_to_admin_menu$")
            ],
            UNBAN_USERS_MENU: [
                CallbackQueryHandler(unban_by_selection, pattern="^unban_by_selection$"),
                CallbackQueryHandler(confirm_unban_all, pattern="^unban_all_confirmation$"),
                CallbackQueryHandler(back_to_manage_users, pattern="^back_to_manage_users$"),
            ],
            UNBAN_SELECTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_unban_selection),
                CallbackQueryHandler(unban_users_menu, pattern="^unban_users_menu$"),
            ],
            UNBAN_ALL_CONFIRMATION: [
                CallbackQueryHandler(execute_unban_all, pattern="^execute_unban_all$"),
                CallbackQueryHandler(unban_users_menu, pattern="^unban_users_menu$"),
            ],
            BAN_JOB_SEEKERS: [MessageHandler(filters.TEXT, handle_job_seeker_ban_search)],
            BAN_EMPLOYERS: [MessageHandler(filters.TEXT, handle_employer_ban_search)],
            BAN_EMPLOYERS_PAGINATED: [
                CallbackQueryHandler(handle_pagination, pattern=r"^(next|prev)_employer_ban_\d+$"),
                CallbackQueryHandler(confirm_ban_employer, pattern=r"^ban_employer_\d+$"),
            ],
            SEARCH_JOB_SEEKERS_FOR_BAN: [MessageHandler(filters.TEXT, handle_job_seeker_ban_search)],
            BAN_JOB_SEEKERS_PAGINATED: [
                CallbackQueryHandler(handle_pagination, pattern=r"^(next|prev)_job_seeker_\d+$"),
                CallbackQueryHandler(confirm_ban_job_seeker, pattern=r"^ban_job_seeker_\d+$"),
            ],
            REASON_FOR_BAN_JOB_SEEKER: [MessageHandler(filters.TEXT, apply_ban_job_seeker)],            SEARCH_EMPLOYERS_FOR_BAN: [MessageHandler(filters.TEXT, handle_employer_ban_search)],
            REASON_FOR_BAN_EMPLOYER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, apply_ban_employer)
            ],
            UNBAN_USERS: [
                CallbackQueryHandler(handle_unban, pattern=r"^unban_(user|employer)_\d+$"),
                CallbackQueryHandler(back_to_database_menu, pattern="^back_to_database_menu$"),
            ],
            VIEW_BANNED_USERS: [CallbackQueryHandler(handle_appeal_decision, pattern="^review_appeals$")],
            REASON_FOR_BAN: [MessageHandler(filters.TEXT, apply_ban)],

            # Appeal system states
            BANNED_STATE: [
                CallbackQueryHandler(start_ban_appeal, pattern="^appeal_start$"),
            ],
            APPEAL_START: [
                CallbackQueryHandler(start_ban_appeal, pattern="^appeal_start$"),
            ],
            APPEAL_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_appeal_input),
                # CommandHandler("cancel", cancel_appeal),
            ],
            APPEAL_REVIEW: [
                CallbackQueryHandler(handle_appeal_decision, pattern=r"^lift_ban_\d+$"),
                CallbackQueryHandler(handle_appeal_decision, pattern=r"^uphold_ban_\d+$"),
                CallbackQueryHandler(handle_appeal_decision, pattern=r"^request_info_\d+$"),
            ],

            REMOVE_JOB_SEEKERS: [CallbackQueryHandler(confirm_removal)],
            REMOVE_EMPLOYERS: [CallbackQueryHandler(confirm_removal)],
            REMOVE_APPLICATIONS: [CallbackQueryHandler(confirm_removal)],
            CONFIRM_REMOVAL: [CallbackQueryHandler(perform_removal)],
            CLEAR_CONFIRMATION: [CallbackQueryHandler(perform_clear)],

            DATABASE_MANAGEMENT: [
                CallbackQueryHandler(manage_users, pattern="^manage_users$"),
                CallbackQueryHandler(manage_jobs, pattern="^manage_jobs$"),
                CallbackQueryHandler(ad_manage_vacancies, pattern="^ad_manage_vacancies$"),  # Fixed pattern
                CallbackQueryHandler(manage_applications, pattern="^manage_applications$"),
                CallbackQueryHandler(export_data, pattern="^export_data$"),
                CallbackQueryHandler(clear_data, pattern="^clear_data$"),
                CallbackQueryHandler(view_system_errors, pattern="^view_system_errors$"),
                CallbackQueryHandler(back_to_admin_menu, pattern="^back_to_admin_menu$")
            ],
            MANAGE_JOBS: [
                CallbackQueryHandler(list_jobs, pattern="^list_jobs$"),
                CallbackQueryHandler(remove_jobs, pattern="^remove_jobs$"),
                CallbackQueryHandler(export_jobs, pattern="^export_jobs$"),
                CallbackQueryHandler(back_to_database_menu, pattern="^back_to_database_menu$")
            ],
            VIEW_ERRORS: [
                CallbackQueryHandler(handle_error_detail, pattern=r"^error_detail_"),
                CallbackQueryHandler(show_database_menu, pattern="^back_to_database_menu$")
            ],
            ERROR_DETAIL: [
                CallbackQueryHandler(show_full_traceback, pattern=r"^show_traceback_"),
                CallbackQueryHandler(show_update_data, pattern=r"^show_update_"),
                CallbackQueryHandler(resolve_error, pattern=r"^resolve_error_"),
                CallbackQueryHandler(view_system_errors, pattern="^view_system_errors$")
            ],
            SEARCH_JOBS: [
                MessageHandler(filters.TEXT, handle_job_search)
            ],
            REMOVE_JOBS_PAGINATED: [
                CallbackQueryHandler(handle_pagination, pattern=r"^(next|prev)_job_\d+$"),
                CallbackQueryHandler(confirm_removal, pattern=r"^remove_job_\d+$"),
            ],
            AD_MANAGE_VACANCIES: [
                CallbackQueryHandler(list_vacancies, pattern="^list_vacancies$"),
                CallbackQueryHandler(remove_vacancies, pattern="^remove_vacancies$"),
                CallbackQueryHandler(export_vacancies, pattern="^export_vacancies$"),
                CallbackQueryHandler(back_to_database_menu, pattern="^back_to_database_menu$")
            ],
            SEARCH_VACANCIES: [
                MessageHandler(filters.TEXT, handle_vacancy_search)
            ],
            LIST_VACANCIES_PAGINATED: [
                CallbackQueryHandler(handle_pagination, pattern=r"^(next|prev)_vacancy_\d+$"),            ],
            REMOVE_VACANCIES_PAGINATED: [
                CallbackQueryHandler(handle_pagination, pattern=r"^(next|prev)_vacancy_remove_\d+$"),
                CallbackQueryHandler(confirm_removal, pattern=r"^remove_vacancy_\d+$"),
            ],
            SEARCH_JOB_SEEKERS: [MessageHandler(filters.TEXT, handle_job_seeker_search)],
            REMOVE_JOB_SEEKERS_PAGINATED: [
                CallbackQueryHandler(handle_pagination, pattern=r"^(next|prev)_job_seeker_\d+$"),
                CallbackQueryHandler(confirm_removal, pattern=r"^remove_seeker_\d+$"),
            ],
            SEARCH_EMPLOYERS: [MessageHandler(filters.TEXT, handle_employer_search)],
            REMOVE_EMPLOYERS_PAGINATED: [
                CallbackQueryHandler(handle_pagination, pattern=r"^(next|prev)_employer_\d+$"),
                CallbackQueryHandler(confirm_removal, pattern=r"^remove_employer_\d+$"),
            ],
            SEARCH_APPLICATIONS: [MessageHandler(filters.TEXT, handle_application_search)],
            REMOVE_APPLICATIONS_PAGINATED: [
                CallbackQueryHandler(handle_pagination, pattern=r"^(next|prev)_application_\d+$"),
                CallbackQueryHandler(confirm_removal, pattern=r"^remove_application_\d+$")
            ],
            MANAGE_APPLICATIONS: [
                CallbackQueryHandler(list_applications, pattern="^list_applications$"),
                CallbackQueryHandler(remove_applications, pattern="^remove_applications$"),
                CallbackQueryHandler(export_applications, pattern="^export_applications$"),
                CallbackQueryHandler(back_to_database_menu, pattern="^back_to_database_menu$")
            ],
            LIST_APPLICATIONS_PAGINATED: [
                CallbackQueryHandler(handle_pagination, pattern=r"^(next|prev)_application_list_\d+$")
            ],
            EXPORT_DATA: [
                CallbackQueryHandler(export_job_seekers, pattern="^export_job_seekers$"),
                CallbackQueryHandler(export_employers, pattern="^export_employers$"),
                CallbackQueryHandler(export_applications, pattern="^export_applications$"),
                CallbackQueryHandler(export_all_data, pattern="^export_all_data$"),
                CallbackQueryHandler(back_to_database_menu, pattern="^back_to_database_menu$")
            ],
            #search vaccancy
            SEARCH_OPTIONS: [
                CallbackQueryHandler(handle_search_options)
            ],
            KEYWORD_SEARCH: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_keyword_search)
            ],
            ADVANCED_FILTERS: [
                CallbackQueryHandler(handle_advanced_filters)
            ],
            FILTER_JOB_TYPE: [
                CallbackQueryHandler(handle_job_type_filter)
            ],
            FILTER_SALARY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_salary_filter)
            ],
            FILTER_EXPERIENCE: [
                CallbackQueryHandler(handle_experience_filter)
            ],
            SEARCH_RESULTS: [
                CallbackQueryHandler(handle_search_results)
            ],
            VIEW_JOB_DETAILS: [
                CallbackQueryHandler(handle_job_details)
            ],
            VIEWING_APPLICATIONS: [
                CallbackQueryHandler(handle_application_actions)
            ],
            APPLICATION_DETAILS: [
                CallbackQueryHandler(handle_application_actions)
            ],
            EXPORTING_APPLICATIONS: [
                CallbackQueryHandler(handle_export_request)
            ]


        },

        #fallbacks=[CommandHandler('cancel', lambda update, context: update.message.reply_text("Canceled."))]
        fallbacks=[
            CommandHandler('start', start),  # Allow /start to reset the conversation
        ],
        allow_reentry=True  # Optional: Allows re-entry into the conversation

    )

    # Add the conversation handler to the application
    application.add_handler(conv_handler)
    application.add_error_handler(advanced_error_handler)
    application.add_handler(
        CallbackQueryHandler(
            handle_appeal_decision,
            pattern=r"^(lift_ban|uphold_ban|request_info)_\d+$"
        )
    )

    # Add the job with coalesce enabled and a longer interval
    application.job_queue.run_repeating(
        handle_notifications,
        interval=30,  # Increased interval
        first=0
    )

    # Start the notification handler
    application.job_queue.run_repeating(handle_notifications, interval=30, first=0)

    # Start polling and run the bot
    application.run_polling()


if __name__ == "__main__":
    main()


