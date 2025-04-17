import json
import sqlite3
import logging
import random
import sys
import traceback

from utils.validation import validate_job_post, validate_job_post_data
from datetime import datetime, timedelta
from datetime import date
today = date.today().isoformat()

from datetime import datetime
from typing import Optional, List
from uuid import uuid4
from pydantic import BaseModel
import logging

# class BotError(BaseModel):
#     error_id: str
#     timestamp: datetime
#     user_id: Optional[int]
#     chat_id: Optional[int]
#     command: Optional[str]
#     error_type: str
#     error_message: str
#     traceback: str
#     status: str = "unresolved"  # unresolved, investigating, fixed
#     context_data: Optional[dict]
#     update_data: Optional[dict]

import os
import sqlite3


class Database:
    def __init__(self, db_path=None):
        if db_path is None:
            # Get absolute path to the database file
            base_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(base_dir, "db", "database.db")

        # Debugging: Print the resolved path
        print(f"[DEBUG] Database path resolved to: {db_path}")
        print(f"[DEBUG] Absolute path: {os.path.abspath(db_path)}")
        print(f"[DEBUG] Directory exists: {os.path.exists(os.path.dirname(db_path))}")

        # Ensure directory exists
        try:
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            print(f"[DEBUG] Successfully ensured directory exists")
        except Exception as e:
            print(f"[ERROR] Failed to create directory: {e}")
            raise

        try:
            self.connection = sqlite3.connect(db_path)
            print("[DEBUG] Successfully connected to database")
        except sqlite3.Error as e:
            print(f"[ERROR] Failed to connect to database: {e}")
            print("[DEBUG] Current working directory:", os.getcwd())
            raise

        # rest of your code...
        self.connection.row_factory = sqlite3.Row
        self.cursor = self.connection.cursor()
        self.create_tables()
        self.add_status_column_to_vacancies()  # Ensure the 'status' column exists on initialization
        self.set_default_status_for_existing_jobs()  # Set default status for existing jobs
        self.add_reason_for_rejection_column()
        # self.add_job_summary_column()
        # self.add_min_requirements_column()
        self.add_missing_vacancies_columns()
        self.add_status_column_to_applications()
        self.add_status_column_to_job_posts()
        self.add_registration_type_column()
        self.remove_job_summary_and_min_requirements_columns()
        # self.add_employer_id_column()  # Ensure employer_id column exists
        self.add_reason_for_rejection_column()

        # Ensure 'source' columns exist in both tables
        self.add_source_column_to_job_posts()
        # self.add_source_column_to_vacancies()


        # Normalize data to ensure consistency
        self.normalize_job_post_statuses()
        self.normalize_vacancy_statuses()
        self.normalize_application_statuses()
        self.fix_invalid_job_post_statuses()
        self.normalize_registration_type()
        self.normalize_user_profiles()
        self.normalize_application_statuses()
        self.normalize_job_post_sources()
        self.normalize_vacancy_sources()

        # Set default values for existing rows
        self.normalize_reason_for_rejection()

    def get_user_language(self, user_id):
        """Retrieve the user's language preference from the database."""
        self.cursor.execute("""
              SELECT language FROM users WHERE user_id = ?
          """, (user_id,))
        result = self.cursor.fetchone()
        if result:
            return result[0]  # Return the language
        return "english"  # Default language if not found

    def create_tables(self):
        # Users table
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            language TEXT DEFAULT 'english',
            full_name TEXT,
            contact_number TEXT,
            dob TEXT,
            gender TEXT,
            languages TEXT,
            qualification TEXT,
            field_of_study TEXT,
            cgpa REAL,
            skills_experience TEXT,
            profile_summary TEXT,
            cv_path TEXT,
            portfolio_link TEXT,
            registration_type TEXT DEFAULT NULL
        )
        """)


        # Employers table
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS employers (
            employer_id INTEGER PRIMARY KEY,
            company_name TEXT,
            city TEXT,
            contact_number TEXT,
            employer_type TEXT,
            about_company TEXT,
            verification_docs TEXT,
            FOREIGN KEY (employer_id) REFERENCES users(user_id) ON DELETE CASCADE  -- Add foreign key
        )
        """)

        # Vacancies Table (Used for approved/open jobs)
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS vacancies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employer_id INTEGER NOT NULL,
            job_title TEXT NOT NULL,
            employment_type TEXT NOT NULL,
            gender TEXT NOT NULL CHECK (gender IN ('Male', 'Female', 'Any')),
            quantity INTEGER NOT NULL CHECK (quantity > 0),
            level TEXT NOT NULL,
            description TEXT NOT NULL,
            qualification TEXT NOT NULL,
            skills TEXT NOT NULL,
            salary TEXT,
            benefits TEXT,
            application_deadline TEXT NOT NULL ,
            status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'closed', 'expired')),
            source TEXT DEFAULT 'vacancy',
            FOREIGN KEY (employer_id) REFERENCES employers(employer_id) ON DELETE CASCADE
        )
        """)

        # Job Posts Table (Used for pending jobs)
        self.cursor.execute("""
               CREATE TABLE IF NOT EXISTS job_posts (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   employer_id INTEGER NOT NULL,
                   job_title TEXT NOT NULL,
                   employment_type TEXT NOT NULL,
                   gender TEXT NOT NULL CHECK (gender IN ('Male', 'Female', 'Any')),
                   quantity INTEGER NOT NULL CHECK (quantity > 0),
                   level TEXT NOT NULL,
                   description TEXT NOT NULL,
                   qualification TEXT NOT NULL,
                   skills TEXT NOT NULL,
                   salary TEXT,
                   benefits TEXT,
                   deadline TEXT NOT NULL ,
                   status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'closed')),
                   reason_for_rejection TEXT DEFAULT 'Not applicable',
                    source TEXT DEFAULT 'job_post',
                   FOREIGN KEY (employer_id) REFERENCES employers(employer_id) ON DELETE CASCADE
               )
               """)
        # appeals table
        self.cursor.execute("""
                    CREATE TABLE IF NOT EXISTS appeals (
                        appeal_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        content TEXT,
                        status TEXT DEFAULT 'pending',
                        review_date TEXT DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                    )
                    """)

        self.cursor.execute("""
                    CREATE TABLE IF NOT EXISTS bans (
                        ban_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        employer_id INTEGER,
                        reason TEXT NOT NULL,
                        ban_date TEXT DEFAULT CURRENT_TIMESTAMP,
                        unban_date TEXT, -- Optional: For temporary bans with an expiration date
                        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                    )
                    """)

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS application_decisions (
            decision_id INTEGER PRIMARY KEY AUTOINCREMENT,
            application_id INTEGER NOT NULL,
            decision TEXT NOT NULL CHECK (decision IN ('approved', 'rejected')),
            rejection_reason TEXT,
            employer_message TEXT,
            decision_date TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (application_id) REFERENCES applications(application_id) ON DELETE CASCADE
        )
        """)

        # Create the 'contact_categories' table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS contact_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name_key TEXT UNIQUE NOT NULL,
                emoji TEXT NOT NULL,
                is_active BOOLEAN DEFAULT 1
            )
        """)


        # Create the 'contact_messages' table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS contact_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                category_id INTEGER NOT NULL,
                message_text TEXT NOT NULL,
                status TEXT DEFAULT 'pending', -- pending/answered/closed
                priority INTEGER DEFAULT 1, -- 1=normal, 2=high, 3=urgent
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                admin_id INTEGER, -- who answered
                answer_text TEXT,
                answered_at TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES contact_categories(id),
                FOREIGN KEY (admin_id) REFERENCES admins(id)
            )
        """)

        # New table for tracking account metadata
        self.cursor.execute("""
           CREATE TABLE IF NOT EXISTS account_metadata (
               user_id INTEGER PRIMARY KEY,
               account_type TEXT NOT NULL CHECK (account_type IN ('employer', 'job_seeker')),
               created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
               last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
               FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
           )
           """)

        # Rating Privacy Settings
        self.cursor.execute("""
               CREATE TABLE IF NOT EXISTS rating_privacy (
                   user_id INTEGER PRIMARY KEY,
                   show_name BOOLEAN DEFAULT TRUE,
                   show_contact BOOLEAN DEFAULT FALSE,
                   FOREIGN KEY (user_id) REFERENCES users(user_id)
               )
           """)

        # Review Metadata (for analytics)
        self.cursor.execute("""
               CREATE TABLE IF NOT EXISTS review_metadata (
                   review_id INTEGER PRIMARY KEY,
                   helpful_count INTEGER DEFAULT 0,
                   flags_count INTEGER DEFAULT 0,
                   admin_approved BOOLEAN DEFAULT FALSE,
                   last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                   FOREIGN KEY (review_id) REFERENCES reviews(id)
               )
           """)

        # User Review Limits (anti-abuse)
        self.cursor.execute("""
               CREATE TABLE IF NOT EXISTS review_limits (
                   user_id INTEGER,
                   date DATE,
                   count INTEGER DEFAULT 0,
                   PRIMARY KEY (user_id, date)
               )
           """)

        # Review Responses
        self.cursor.execute("""
               CREATE TABLE IF NOT EXISTS review_responses (
                   id INTEGER PRIMARY KEY,
                   review_id INTEGER NOT NULL,
                   responder_id INTEGER NOT NULL,
                   response_text TEXT NOT NULL,
                   created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                   FOREIGN KEY (review_id) REFERENCES reviews(id)
               )
           """)

        # Admin Notifications
        self.cursor.execute("""
               CREATE TABLE IF NOT EXISTS admin_notifications (
                   id INTEGER PRIMARY KEY,
                   notification_type TEXT NOT NULL,  -- 'flagged_review', 'new_review'
                   related_id INTEGER NOT NULL,      -- review_id or user_id
                   message TEXT NOT NULL,
                   is_resolved BOOLEAN DEFAULT FALSE,
                   created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
               )
           """)

        # Create index for faster queries
        self.cursor.execute("""
           CREATE INDEX IF NOT EXISTS idx_account_metadata_user ON account_metadata(user_id)
           """)

        class Database:
            def __init__(self, db_path):
                self.connection = sqlite3.connect(db_path)
                self.cursor = self.connection.cursor()
                self.create_tables()

            def create_tables(self):
                # Create a table for job posts
                self.cursor.execute("""
                    CREATE TABLE IF NOT EXISTS job_posts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        employer_id INTEGER NOT NULL,
                        job_title TEXT NOT NULL,
                        employment_type TEXT NOT NULL,
                        gender TEXT NOT NULL CHECK (gender IN ('Male', 'Female', 'Any')),
                        quantity INTEGER NOT NULL CHECK (quantity > 0),
                        level TEXT NOT NULL,
                        description TEXT NOT NULL,
                        qualification TEXT NOT NULL,
                        skills TEXT NOT NULL,
                        salary TEXT NOT NULL,
                        benefits TEXT NOT NULL,
                        deadline TEXT NOT NULL CHECK ,
                        status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'closed'))
                        reason_for_rejection TEXT DEFAULT 'Not applicable',
                         source TEXT DEFAULT 'job_post',
                        FOREIGN KEY (employer_id) REFERENCES employers(employer_id) ON DELETE CASCADE
                    )
                """)
                self.connection.commit()


        # Applications table
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            application_id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_seeker_id INTEGER NOT NULL,
            id INTEGER NOT NULL,
            additional_docs TEXT,
            cover_letter TEXT NOT NULL,
            application_date TEXT DEFAULT (datetime('now')),
            status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'reviewed', 'approved', 'rejected', 'withdrawn')),
            rejection_reason TEXT,
            FOREIGN KEY (job_seeker_id) REFERENCES users(user_id) ON DELETE CASCADE,
            FOREIGN KEY (id) REFERENCES vacancies(id) ON DELETE CASCADE
        )
        """)


        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reviewer_id INTEGER NOT NULL,
                target_id INTEGER NOT NULL,
                 target_type TEXT NOT NULL,  -- 'bot', 'employer', or 'job_seeker'
                  rating INTEGER NOT NULL,
                 comment TEXT,
                is_anonymous BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (reviewer_id) REFERENCES users(user_id)
            )
        """)
        self.connection.commit()

        # New table: Contact Categories
        self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS contact_categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name_key TEXT UNIQUE NOT NULL,
                    emoji TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT 1
                )
                """)

        # New table: Contact Messages
        self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS contact_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    category_id INTEGER NOT NULL,
                    message_text TEXT NOT NULL,
                    status TEXT DEFAULT 'pending', -- pending/answered/closed
                    priority INTEGER DEFAULT 1, -- 1=normal, 2=high, 3=urgent
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    admin_id INTEGER, -- Optional for now (remove if admins table doesn't exist)
                    answer_text TEXT,
                    answered_at TIMESTAMP,
                    FOREIGN KEY (category_id) REFERENCES contact_categories(id)
                    FOREIGN KEY (admin_id) REFERENCES admins(id) -- Uncomment once admins table exists
                )
                """)

        # Insert default categories into contact_categories
        default_categories = [
            ("contact_tech_issue", "🛠️"),
            ("contact_payment", "💳"),
            ("contact_account", "👤"),
            ("contact_suggestion", "💡"),
            ("contact_other", "❓")
        ]

        self.cursor.executemany("""
                INSERT OR IGNORE INTO contact_categories (name_key, emoji) 
                VALUES (?, ?)
                """, default_categories)

        # Commit all changes to the database
        self.connection.commit()

        # Create errors table
        self.cursor.execute("""
           CREATE TABLE IF NOT EXISTS bot_errors (
               error_id TEXT PRIMARY KEY,
               timestamp TEXT NOT NULL,
               user_id INTEGER,
               chat_id INTEGER,
               command TEXT,
               error_type TEXT NOT NULL,
               error_message TEXT NOT NULL,
               traceback TEXT NOT NULL,
               status TEXT DEFAULT 'unresolved',
               context_data TEXT,
               update_data TEXT
           )
           """)
        self.connection.commit()

        self.cursor.execute("""
                        CREATE TABLE IF NOT EXISTS notifications (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            user_id INTEGER NOT NULL,
                            action TEXT NOT NULL,
                            timestamp TEXT DEFAULT (datetime('now'))
                        )
                    """)
        self.connection.commit()






        # Create indexes for better search performance
        self.cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_vacancies_status ON vacancies(status)
        """)
        self.cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_vacancies_employment_type ON vacancies(employment_type)
        """)
        self.cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_vacancies_level ON vacancies(level)
        """)
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_applications_id ON applications(application_id)")


        # Commit all changes
        self.connection.commit()

    def user_exists(self, user_id):
        """Check if a user exists in the database."""
        self.cursor.execute("SELECT COUNT(*) FROM users WHERE user_id = ?", (user_id,))
        return self.cursor.fetchone()[0] > 0

    def get_employer_details(self, user_id):
        """Fetch employer details for a given user_id."""
        self.cursor.execute("""
        SELECT company_name, city, contact_number, employer_type, about_company, verification_docs
        FROM employers
        WHERE employer_id = ?
        """, (user_id,))
        return self.cursor.fetchone()

    def get_user_contact_number(self, user_id):
        """Retrieve the contact number of a user from the database."""
        self.cursor.execute("SELECT contact_number FROM users WHERE user_id = ?", (user_id,))
        result = self.cursor.fetchone()
        return result[0] if result else None

    def insert_user(self, user_id, language="english"):
        """Insert a new user into the database with default language or update if exists."""
        # Check if the user already exists
        self.cursor.execute("""
            SELECT user_id FROM users WHERE user_id = ?
        """, (user_id,))
        result = self.cursor.fetchone()

        if result:
            # If user exists, update their language
            self.cursor.execute("""
                UPDATE users SET language = ? WHERE user_id = ?
            """, (language, user_id))
        else:
            # If user does not exist, insert a new user
            self.cursor.execute("""
                INSERT INTO users (user_id, language) VALUES (?, ?)
            """, (user_id, language))

        self.connection.commit()

    def update_user_profile(self, user_id, **kwargs):
        """Update user profile details."""
        if not kwargs:
            raise ValueError("No fields provided for update.")

        # Construct the SQL query
        query = "UPDATE users SET " + ", ".join(f"{key} = ?" for key in kwargs.keys()) + " WHERE user_id = ?"
        try:
            self.cursor.execute(query, (*kwargs.values(), user_id))
            self.connection.commit()
        except Exception as e:
            print(f"Database error: {e}")
            raise

    def insert_employer(self, employer_data):
        """Insert a new employer."""
        self.cursor.execute("""
        INSERT INTO employers (company_name, city, contact_number, employer_type, about_company, verification_docs)
        VALUES (?, ?, ?, ?, ?, ?)
        """, employer_data)
        self.connection.commit()

    def insert_vacancy(self, vacancy_data):
        """
        Insert a new vacancy with default values for missing fields.
        """
        default_values = {
            "employer_id": None,
            "job_title": "Not provided",
            "employment_type": "Not provided",
            "gender": "Any",
            "quantity": 1,
            "level": "Not provided",
            "description": "Not provided",
            "qualification": "Not provided",
            "skills": "Not provided",
            "salary": "Not provided",
            "benefits": "Not provided",
            "deadline": "Not provided",
            "status": "approved",
            "source": "vacancy"
        }
        final_data = {**default_values, **vacancy_data}

        self.cursor.execute("""
            INSERT INTO vacancies (
                employer_id, job_title, employment_type, gender, quantity, level,
                description, qualification, skills, salary, benefits, application_deadline, status, source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            final_data["employer_id"], final_data["job_title"], final_data["employment_type"],
            final_data["gender"], final_data["quantity"], final_data["level"],
            final_data["description"], final_data["qualification"], final_data["skills"],
            final_data["salary"], final_data["benefits"], final_data["deadline"],
            # Map 'deadline' to 'application_deadline'
            final_data["status"], final_data["source"]
        ))
        self.connection.commit()

    def insert_application(self, application_data):
        """Insert a job application with a default status of 'pending'."""
        # Ensure the status is always set to 'pending' if not provided
        if len(application_data) == 4:  # Check if status is missing
            application_data = (*application_data, "pending")  # Append default status

        self.cursor.execute("""
        INSERT INTO applications (job_seeker_id, id, additional_docs, cover_letter, application_date, status)
        VALUES (?, ?, ?, ?, ?, ?)
        """, application_data)
        self.connection.commit()

    def fetch_open_vacancies(self):
        """Fetch all approved vacancies"""
        self.cursor.execute("""
        SELECT v.id, v.job_title, v.employment_type, v.salary, v.application_deadline, e.company_name
        FROM vacancies v
        JOIN employers e ON v.employer_id = e.employer_id
        WHERE v.status = 'approved'
        """)
        return self.cursor.fetchall()

    def fetch_applications_by_employer(self, employer_id):
        """Fetch applications for a specific employer's vacancies."""
        self.cursor.execute("""
        SELECT a.application_id, a.job_seeker_id, a.cover_letter, a.application_date, u.full_name
        FROM applications a
        JOIN users u ON a.job_seeker_id = u.user_id
        JOIN vacancies v ON a.id = v.id
        WHERE v.employer_id = ?
        """, (employer_id,))
        return self.cursor.fetchall()

    def close(self):
        self.connection.close()

    def save_user_document(self, user_id, job_seeker_file_id):
        self.cursor.execute("""
            UPDATE users
            SET cv_path = ?
            WHERE user_id = ?
        """, (job_seeker_file_id, user_id))
        self.connection.commit()

    def save_employer_document(self, employer_id, employer_file_id):
        self.cursor.execute("""
            UPDATE employers
            SET verification_docs = ?
            WHERE employer_id = ?
        """, (employer_file_id, employer_id))
        self.connection.commit()

    def get_user_profile(self, user_id):
        """Fetch the user's profile data from the database as a dictionary."""
        self.cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        result = self.cursor.fetchone()
        if result:
            columns = [column[0] for column in self.cursor.description]
            return dict(zip(columns, result))  # Convert the tuple into a dictionary
        return None

    def save_employer_profile(self, user_id, company_name, location, employer_type, about_company, verification_docs):
        contact_number = self.get_user_contact_number(user_id)
        if not contact_number:
            raise ValueError(f"Contact number not found for user ID {user_id}")

        # Check if the employer already exists
        self.cursor.execute("SELECT employer_id FROM employers WHERE employer_id = ?", (user_id,))
        employer_exists = self.cursor.fetchone()

        if employer_exists:
            # Update the existing employer record
            self.cursor.execute("""
                UPDATE employers
                SET company_name = ?, city = ?, contact_number = ?, employer_type = ?, about_company = ?, verification_docs = ?
                WHERE employer_id = ?
            """, (company_name, location, contact_number, employer_type, about_company, verification_docs, user_id))
        else:
            # Insert a new employer record
            self.cursor.execute("""
                INSERT INTO employers (employer_id, company_name, city, contact_number, employer_type, about_company, verification_docs)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, company_name, location, contact_number, employer_type, about_company, verification_docs))

        self.connection.commit()

    def get_employer_profile(self, user_id):
        """Fetch the employer's profile from the database and return it as a dictionary."""
        self.cursor.execute("""
            SELECT employer_id, company_name, city, contact_number, employer_type, about_company, verification_docs
            FROM employers
            WHERE employer_id = ?
        """, (user_id,))

        row = self.cursor.fetchone()
        if row:
            return {
                "employer_id": row[0],
                "company_name": row[1],
                "city": row[2],
                "contact_number": row[3],
                "employer_type": row[4],
                "about_company": row[5],
                "verification_docs": row[6]
            }
        return None  # Return None if employer profile does not exist

    def get_employer_profile_by_user_id(self, user_id):
        self.cursor.execute("""
            SELECT employer_id FROM employers WHERE employer_id = ?
        """, (user_id,))
        result = self.cursor.fetchone()
        return {"employer_id": result[0]} if result else None

    def get_employer_with_registration_type(self, employer_id):
        """Fetch employer details along with their registration type."""
        self.cursor.execute("""
        SELECT e.company_name, e.city, e.contact_number, e.employer_type, e.about_company, e.verification_docs, u.registration_type
        FROM employers e
        JOIN users u ON e.employer_id = u.user_id
        WHERE e.employer_id = ?
        """, (employer_id,))
        return self.cursor.fetchone()

    def save_pending_job_post(self, job_post):
        try:
            # Exclude the 'id' field if it exists
            job_post_data = {k: v for k, v in job_post.items() if k != "id"}

            # Debugging: Log the job post data being saved
            logging.info(f"Saving job post data: {job_post_data}")

            # Insert into the job_posts table
            self.cursor.execute("""
                INSERT INTO job_posts (
                    employer_id, job_title, employment_type, gender, quantity, level,
                    description, qualification, skills, salary, benefits, deadline, status, source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job_post_data.get("employer_id"),
                job_post_data.get("job_title"),
                job_post_data.get("employment_type"),
                job_post_data.get("gender"),
                job_post_data.get("quantity"),
                job_post_data.get("level"),
                job_post_data.get("description"),
                job_post_data.get("qualification"),
                job_post_data.get("skills"),
                job_post_data.get("salary"),
                job_post_data.get("benefits"),
                job_post_data.get("deadline"),
                job_post_data.get("status", "pending"),
                job_post_data.get("source", "job_post")
            ))

            # Commit the transaction and log the newly inserted ID
            self.connection.commit()
            job_post["id"] = self.cursor.lastrowid  # Store the generated ID back into the job_post
            logging.info(f"Job post saved successfully with ID: {job_post['id']}")
        except sqlite3.Error as e:
            logging.error(f"Database error saving job post: {e}")
            raise ValueError("Failed to save job post") from e

    def insert_job_post(self, job_data):
        """Save a pending job post"""
        self.cursor.execute("""
        INSERT INTO job_posts (employer_id, job_title, employment_type, gender, quantity, level, 
            description, qualification, skills, salary, benefits, deadline, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
        """, (
            job_data["employer_id"], job_data["job_title"], job_data["employment_type"], job_data["gender"],
            job_data["quantity"], job_data["level"], job_data["description"], job_data["qualification"],
            job_data["skills"], job_data["salary"], job_data["benefits"], job_data["deadline"]
        ))
        self.connection.commit()

    def get_open_job_posts(self):
        """
        Fetch approved job posts from vacancies that are not expired.
        """
        self.cursor.execute("""
            SELECT id, job_title, employment_type, gender, quantity, level, description, 
                   qualification, skills, salary, benefits, application_deadline, employer_id, status
            FROM vacancies 
            WHERE status = 'approved'
        """)
        rows = self.cursor.fetchall()

        # Filter out expired jobs at the application level
        open_jobs = []
        current_date = datetime.now().date()
        for row in rows:
            try:
                deadline = datetime.strptime(row["application_deadline"], "%Y-%m-%d").date()
                if deadline >= current_date:
                    open_jobs.append(row)
            except ValueError:
                logging.warning(f"Invalid date format for application_deadline: {row['application_deadline']}")

        return open_jobs
    def approve_job_post(self, job_id):
        """Move an approved job_post to vacancies with the correct status."""
        self.cursor.execute("""
        SELECT employer_id, job_title, employment_type, gender, quantity, level, 
               description, qualification, skills, salary, benefits, deadline
        FROM job_posts
        WHERE id = ? AND status = 'pending'
        """, (job_id,))
        job_post = self.cursor.fetchone()

        if job_post:
            # Insert into vacancies with 'approved' status instead of 'open'
            self.cursor.execute("""
            INSERT INTO vacancies (employer_id, job_title, employment_type, gender, quantity, level, 
                description, qualification, skills, salary, benefits, application_deadline, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'approved')
            """, job_post)

            # Delete from job_posts
            self.cursor.execute("DELETE FROM job_posts WHERE id = ?", (job_id,))
            self.connection.commit()
#before
    def fetch_approved_vacancies(self):
        """Fetch all approved vacancies."""
        try:
            self.cursor.execute("""
                SELECT v.id AS job_id, v.job_title, v.employment_type, v.gender, v.quantity, v.level,
                       v.description, v.qualification, v.skills, v.salary, v.benefits,
                       v.application_deadline AS deadline,  -- Normalize column name here
                       e.company_name, v.employer_id, v.status, 'vacancy' AS source
                FROM vacancies v
                JOIN employers e ON v.employer_id = e.employer_id
                WHERE v.status = 'approved'
            """)
            rows = self.cursor.fetchall()
            return [dict(row) for row in rows]  # Convert rows to dictionaries
        except sqlite3.Error as e:
            logging.error(f"Database error fetching approved vacancies: {e}")
            return []

    def get_job_by_id(self, job_id: int):
        """
        Fetch a job post by its ID from either the vacancies or job_posts table.
        """
        try:
            # Attempt to fetch the job from the vacancies table (approved jobs)
            self.cursor.execute("""
                SELECT v.id AS job_id, v.job_title, v.employment_type, v.gender, v.quantity, v.level,
                       v.description, v.qualification, v.skills, v.salary, v.benefits, v.application_deadline,
                       e.company_name AS employer_name, v.employer_id, v.status, 'vacancy' AS source
                FROM vacancies v
                JOIN employers e ON v.employer_id = e.employer_id
                WHERE v.id = ? AND v.status = 'approved'
            """, (job_id,))
            job = self.cursor.fetchone()

            if job:
                columns = [column[0] for column in self.cursor.description]
                return dict(zip(columns, job))

            # If not found in vacancies, attempt to fetch from job_posts (pending jobs)
            self.cursor.execute("""
                SELECT jp.id AS job_id, jp.job_title, jp.employment_type, jp.gender, jp.quantity, jp.level,
                       jp.description, jp.qualification, jp.skills, jp.salary, jp.benefits, jp.deadline AS application_deadline,
                       e.company_name AS employer_name, jp.employer_id, jp.status, 'job_post' AS source
                FROM job_posts jp
                JOIN employers e ON jp.employer_id = e.employer_id
                WHERE jp.id = ?
            """, (job_id,))
            job = self.cursor.fetchone()

            if job:
                columns = [column[0] for column in self.cursor.description]
                return dict(zip(columns, job))

            return None  # Return None if the job is not found

        except sqlite3.Error as e:
            logging.error(f"Database error fetching job by ID {job_id}: {e}")
            return None

    def reject_job_post(self, job_id: int, reason: str = "Not specified"):
        """
        Reject a job post and provide a reason for rejection.
        """
        self.cursor.execute(
            "UPDATE job_posts SET status = ?, reason_for_rejection = ? WHERE id = ?",
            ("rejected", reason, job_id)  # Set the rejection reason
        )
        self.connection.commit()

    def close(self):
        self.connection.close()
#before
    def get_job_posts_by_employer(self, employer_id):
        try:
            self.cursor.execute("""
                SELECT 
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
                    reason_for_rejection, 
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
                        reason_for_rejection, 
                        'job_post' AS source
                    FROM job_posts
                    WHERE employer_id = ? AND status IN ('pending', 'closed')
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
                       application_deadline AS deadline, 
                        status, 
                        '' AS reason_for_rejection, 
                        'vacancy' AS source
                    FROM vacancies
                    WHERE employer_id = ? AND status IN ('approved', 'closed')
                )
            """, (employer_id, employer_id))

            rows = self.cursor.fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error as e:
            logging.error(f"Database error fetching job posts by employer: {e}")
            return []

    def get_pending_job_posts_by_employer(self, employer_id):
        try:
            self.cursor.execute("""
                SELECT id AS job_id, employer_id, job_title, employment_type, gender, quantity, level,
                       description, qualification, skills, salary, benefits, deadline, status,
                       reason_for_rejection, 'job_post' AS source
                FROM job_posts
                WHERE employer_id = ? AND status = 'pending'
            """, (employer_id,))
            rows = self.cursor.fetchall()
            return [dict(zip([desc[0] for desc in self.cursor.description], row)) for row in rows]
        except sqlite3.Error as e:
            logging.error(f"Database error fetching pending job posts by employer: {e}")
            return []

    def close_job_post(self, job_id: int):
        """
        Close a job post by setting its status to 'closed'.
        """
        self.cursor.execute("SELECT status FROM job_posts WHERE id = ?", (job_id,))
        current_status = self.cursor.fetchone()
        if not current_status:
            raise ValueError(f"Job post with ID {job_id} does not exist.")
        current_status = current_status[0]
        if current_status == "closed":
            print(f"Warning: Job post with ID {job_id} is already closed.")
            return

        if current_status not in ["approved", "open"]:
            raise ValueError(f"Cannot close job post with ID {job_id}. Status must be 'approved' or 'open'.")

        self.cursor.execute("""
        UPDATE job_posts 
        SET status = ? 
        WHERE id = ?
        """, ("closed", job_id))
        self.connection.commit()

    def resubmit_job_post(self, job_id: int):
        """
        Resubmit a rejected job post for admin approval.
        """
        self.cursor.execute("SELECT status FROM job_posts WHERE id = ?", (job_id,))
        current_status = self.cursor.fetchone()
        if not current_status:
            raise ValueError(f"Job post with ID {job_id} does not exist.")
        current_status = current_status[0]

        if current_status != "rejected":
            raise ValueError(f"Cannot resubmit job post with ID {job_id}. Status must be 'rejected'.")

        self.cursor.execute(
            "UPDATE job_posts SET status = ?, reason_for_rejection = ? WHERE id = ?",
            ("pending", None, job_id)  # Reset status and clear rejection reason
        )
        self.connection.commit()

    def get_applications_for_job(self, job_id: int):
        """
        Fetch all applications for a specific job, including user details.
        """
        try:
            self.cursor.execute("""
                SELECT 
                    a.application_id, 
                    a.job_seeker_id, 
                    u.full_name, 
                    a.cover_letter, 
                    a.application_date, 
                    a.status,
                    u.cv_path AS additional_docs, 
                    u.portfolio_link, 
                    u.gender, 
                    u.contact_number, 
                    u.languages, 
                    u.qualification, 
                    u.field_of_study, 
                    u.cgpa, 
                    u.skills_experience AS skills, 
                    u.profile_summary,
                    a.id AS job_id  -- Add this to alias 'id' to 'job_id'
                FROM applications a
                INNER JOIN users u ON a.job_seeker_id = u.user_id 
                WHERE a.id = ? AND a.status != 'withdrawn'  -- Exclude withdrawn applications
            ORDER BY a.application_date DESC;  -- Optional: Order by application date
            """, (job_id,))
            return [dict(row) for row in self.cursor.fetchall()]
        except sqlite3.Error as e:
            logging.error(f"Database error fetching applications: {e}")
            return []

    def get_applications_for_job_with_title(self, job_id: int):
        """
        Fetch all applications for a specific job, including user details and job title.
        Returns a list of dictionaries with all application data including job_title.
        """
        try:
            self.cursor.execute("""
                SELECT 
                    a.application_id, 
                    a.job_seeker_id, 
                    u.full_name, 
                    a.cover_letter, 
                    a.application_date, 
                    a.status,
                    u.cv_path AS additional_docs, 
                    u.portfolio_link, 
                    u.gender, 
                    u.contact_number, 
                    u.languages, 
                    u.qualification, 
                    u.field_of_study, 
                    u.cgpa, 
                    u.skills_experience AS skills, 
                    u.profile_summary,
                    a.id AS job_id,
                    COALESCE(v.job_title, jp.job_title) AS job_title  -- Get job title from either vacancies or job_posts
                FROM applications a
                INNER JOIN users u ON a.job_seeker_id = u.user_id
                LEFT JOIN vacancies v ON a.id = v.id
                LEFT JOIN job_posts jp ON a.id = jp.id
                WHERE a.id = ?
            """, (job_id,))

            # Convert rows to dictionaries
            columns = [column[0] for column in self.cursor.description]
            return [dict(zip(columns, row)) for row in self.cursor.fetchall()]
        except sqlite3.Error as e:
            logging.error(f"Database error fetching applications with job title: {e}")
            return []

    def get_complete_application_details(self, application_id: int) -> dict:
        """Get all application details with guaranteed dict return"""
        try:
            self.cursor.execute("""
                SELECT 
                    a.application_id,
                    a.job_seeker_id,
                    a.id AS job_id,
                    a.cover_letter,
                    a.application_date,
                    a.status,
                    u.full_name,
                    u.contact_number,
                    u.dob,
                    u.gender,
                    u.languages,
                    u.qualification,
                    u.field_of_study,
                    u.cgpa,
                    u.skills_experience,
                    u.profile_summary,
                    u.cv_path,
                    u.portfolio_link,
                    COALESCE(v.job_title, jp.job_title) AS job_title,
                    v.description AS job_description,
                    e.company_name
                FROM applications a
                INNER JOIN users u ON a.job_seeker_id = u.user_id
                LEFT JOIN vacancies v ON a.id = v.id
                LEFT JOIN job_posts jp ON a.id = jp.id
                LEFT JOIN employers e ON v.employer_id = e.employer_id OR jp.employer_id = e.employer_id
                WHERE a.application_id = ?
            """, (application_id,))

            if row := self.cursor.fetchone():
                columns = [col[0] for col in self.cursor.description]
                return {col: val for col, val in zip(columns, row) if val is not None}
            return {}  # Return empty dict instead of None

        except sqlite3.Error as e:
            logging.error(f"Database error for application {application_id}: {e}")
            return {}


    # def get_vacancy_with_stats(self, id: int) -> dict:
    #     """
    #     Get vacancy details with application statistics
    #     Works with existing schema (no updated_at column required)
    #     """
    #     try:
    #         # First get basic vacancy info
    #         self.cursor.execute("""
    #             SELECT * FROM vacancies
    #             WHERE id = ?
    #         """, (id,))
    #         vacancy = dict(self.cursor.fetchone()) if self.cursor.rowcount else None
    #         if not vacancy:
    #             return None
    #
    #         # Then get application stats in a separate query
    #         self.cursor.execute("""
    #             SELECT
    #                 COUNT(*) AS application_count,
    #                 COUNT(CASE WHEN status = 'pending' THEN 1 END) AS pending_count,
    #                 COUNT(CASE WHEN status = 'approved' THEN 1 END) AS approved_count,
    #                 COUNT(CASE WHEN status = 'rejected' THEN 1 END) AS rejected_count
    #             FROM applications
    #             WHERE id = ?
    #         """, (id,))
    #         stats = dict(self.cursor.fetchone()) if self.cursor.rowcount else {}
    #
    #         # Calculate expiration status
    #         current_date = datetime.now().strftime('%Y-%m-%d')
    #         if vacancy['status'] == 'approved' and vacancy['application_deadline'] < current_date:
    #             vacancy['display_status'] = 'expired'
    #         else:
    #             vacancy['display_status'] = vacancy['status'].lower()
    #
    #         # Merge results
    #         return {**vacancy, **stats}
    #
    #     except sqlite3.Error as e:
    #         logging.error(f"Database error in get_vacancy_with_stats: {e}")
    #         return None

    def get_vacancy_with_stats(self, id: int) -> dict:
        """
        Get vacancy details with application statistics
        Returns comprehensive vacancy data with application counts
        """
        try:
            # Get basic vacancy info
            self.cursor.execute("""
                SELECT 
                    v.*,
                    COUNT(a.application_id) AS total_applications,
                    COUNT(CASE WHEN a.status = 'pending' THEN 1 END) AS pending_count,
                    COUNT(CASE WHEN a.status = 'approved' THEN 1 END) AS approved_count,
                    COUNT(CASE WHEN a.status = 'rejected' THEN 1 END) AS rejected_count
                FROM vacancies v
                LEFT JOIN applications a ON v.id = a.id
                WHERE v.id = ?
                GROUP BY v.id
            """, (id,))

            result = self.cursor.fetchone()
            if not result:
                return None

            vacancy = dict(result)

            # Calculate expiration status
            current_date = datetime.now().strftime('%Y-%m-%d')
            if vacancy['status'] == 'approved' and vacancy['application_deadline'] < current_date:
                vacancy['display_status'] = 'expired'
            else:
                vacancy['display_status'] = vacancy['status'].lower()

            return vacancy

        except sqlite3.Error as e:
            logging.error(f"Database error in get_vacancy_with_stats: {e}")
            return None

    def can_resubmit_job_post(self, job_id):
        self.cursor.execute("SELECT status FROM job_posts WHERE id = ?", (job_id,))
        result = self.cursor.fetchone()
        return result and result[0] == "rejected"

    def job_post_belongs_to_employer(self, job_id: int, employer_id: int):
        """Check if a job post belongs to the specified employer."""
        self.cursor.execute("SELECT COUNT(*) FROM job_posts WHERE id = ? AND employer_id = ?", (job_id, employer_id))
        return self.cursor.fetchone()[0] > 0

    # Add these to your Database class
    def get_pending_applications_count(self, user_id: int) -> int:
        """Get count of pending applications for a user."""
        try:
            self.cursor.execute("""
                SELECT COUNT(*) FROM applications 
                WHERE job_seeker_id = ? AND status = 'pending'
            """, (user_id,))
            result = self.cursor.fetchone()
            return result[0] if result else 0
        except sqlite3.Error as e:
            logging.error(f"Database error in get_pending_applications_count: {e}")
            return 0

    def get_approved_applications_count(self, user_id: int) -> int:
        """Get count of pending applications for a user."""
        try:
            self.cursor.execute("""
                SELECT COUNT(*) FROM applications 
                WHERE job_seeker_id = ? AND status = 'approved'
            """, (user_id,))
            result = self.cursor.fetchone()
            return result[0] if result else 0
        except sqlite3.Error as e:
            logging.error(f"Database error in get_approved_applications_count: {e}")
            return 0

    def get_user_applications(self, user_id: int) -> list:
        """Get all applications with job details"""
        self.cursor.execute("""
            SELECT 
                a.application_id,
                a.status,
                a.application_date,
                a.cover_letter,
                v.job_title,
                v.employment_type,
                e.company_name,
                v.application_deadline
            FROM applications a
            JOIN vacancies v ON a.id = v.id
            JOIN employers e ON v.employer_id = e.employer_id
            WHERE a.job_seeker_id = ?
            ORDER BY a.application_date DESC
        """, (user_id,))
        return [dict(row) for row in self.cursor.fetchall()]

    def get_application_details(self, application_id: int) -> dict:
        """Get full application details including CV file_id"""
        self.cursor.execute("""
            SELECT 
                a.*,
                v.job_title,
                v.description,
                e.company_name,
                u.cv_path
            FROM applications a
            JOIN vacancies v ON a.id = v.id
            JOIN employers e ON v.employer_id = e.employer_id
            JOIN users u ON a.job_seeker_id = u.user_id
            WHERE a.application_id = ?
        """, (application_id,))
        return dict(self.cursor.fetchone())

    def get_active_vacancies_count(self, employer_id: int) -> int:
        """
        Get count of active (approved) vacancies for an employer.
        Includes only vacancies that are approved and not closed, with deadline not passed.
        """
        try:
            current_date = datetime.now().strftime('%Y-%m-%d')

            self.cursor.execute("""
                SELECT COUNT(*) 
                FROM vacancies 
                WHERE employer_id = ? 
                AND status = 'approved'
                AND application_deadline >= ?
            """, (employer_id, current_date))

            result = self.cursor.fetchone()
            return result[0] if result else 0

        except sqlite3.Error as e:
            logging.error(f"Database error in get_active_vacancies_count: {e}")
            return 0

    def get_new_applications_count(self, employer_id: int) -> int:
        """
        Get count of new/pending applications for all of employer's active vacancies.
        Only counts applications that haven't been reviewed yet.
        """
        try:
            current_date = datetime.now().strftime('%Y-%m-%d')

            self.cursor.execute("""
                SELECT COUNT(a.application_id)
                FROM applications a
                JOIN vacancies v ON a.id = v.id
                WHERE v.employer_id = ?
                AND v.status = 'approved'
                AND v.application_deadline >= ?
                AND a.status = 'pending'
                AND a.application_date >= date('now', '-30 days')  -- Only recent applications
            """, (employer_id, current_date))

            result = self.cursor.fetchone()
            return result[0] if result else 0

        except sqlite3.Error as e:
            logging.error(f"Database error in get_new_applications_count: {e}")
            return 0

    def get_active_vacancies_with_applications(self, employer_id: int) -> dict:
        """
        Enhanced version that returns both active vacancies count and new applications count in one query.
        More efficient than making two separate database calls.
        """
        try:
            current_date = datetime.now().strftime('%Y-%m-%d')

            self.cursor.execute("""
                SELECT 
                    COUNT(DISTINCT v.id) AS active_vacancies,
                    COUNT(a.application_id) AS new_applications
                FROM vacancies v
                LEFT JOIN applications a ON v.id = a.id 
                    AND a.status = 'pending'
                    AND a.application_date >= date('now', '-30 days')
                WHERE v.employer_id = ?
                AND v.status = 'approved'
                AND v.application_deadline >= ?
            """, (employer_id, current_date))

            result = self.cursor.fetchone()
            return {
                'active_vacancies': result[0] if result else 0,
                'new_applications': result[1] if result else 0
            }

        except sqlite3.Error as e:
            logging.error(f"Database error in get_active_vacancies_with_applications: {e}")
            return {'active_vacancies': 0, 'new_applications': 0}

    def get_total_applications_count(self, employer_id: int) -> int:
        """Count all applications received for employer's vacancies"""
        try:
            self.cursor.execute("""
                SELECT COUNT(a.application_id)
                FROM applications a
                JOIN vacancies v ON a.id = v.id
                WHERE v.employer_id = ?
            """, (employer_id,))
            return self.cursor.fetchone()[0] or 0
        except sqlite3.Error as e:
            logging.error(f"Database error in get_total_applications_count: {e}")
            return 0

    def get_employer_hire_rate(self, employer_id: int) -> float:
        """Calculate percentage of applications that resulted in hires"""
        try:
            self.cursor.execute("""
                SELECT 
                    (COUNT(CASE WHEN a.status = 'approved' THEN 1 END) * 100.0) / 
                    NULLIF(COUNT(a.application_id), 0)
                FROM applications a
                JOIN vacancies v ON a.id = v.id
                WHERE v.employer_id = ?
            """, (employer_id,))
            result = self.cursor.fetchone()[0]
            return round(result, 1) if result else 0.0
        except sqlite3.Error as e:
            logging.error(f"Database error in get_employer_hire_rate: {e}")
            return 0.0

    def get_avg_response_time(self, employer_id: int) -> float:
        """Calculate average response time using application_date as both start and end"""
        try:
            self.cursor.execute("""
                SELECT AVG(
                    julianday('now') - julianday(a.application_date)
                )
                FROM applications a
                JOIN vacancies v ON a.id = v.id
                WHERE v.employer_id = ?
                AND a.status != 'pending'
            """, (employer_id,))
            result = self.cursor.fetchone()[0]
            return round(result, 1) if result else 0.0
        except sqlite3.Error as e:
            logging.error(f"Database error in get_avg_response_time: {e}")
            return 0.0

    def get_member_since_date(self, user_id: int) -> str:
        """Get account creation date in human-readable format"""
        try:
            self.cursor.execute("""
            SELECT strftime('%Y-%m-%d', created_at)
            FROM account_metadata
            WHERE user_id = ?
            """, (user_id,))
            result = self.cursor.fetchone()
            return result[0] if result else "Unknown"
        except sqlite3.Error as e:
            logging.error(f"Database error in get_member_since_date: {e}")
            return "Unknown"

    def record_user_creation(self, user_id: int, account_type: str):
        """Record when a new user account is created"""
        try:
            self.cursor.execute("""
            INSERT INTO account_metadata (user_id, account_type)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO NOTHING
            """, (user_id, account_type))
            self.connection.commit()
        except sqlite3.Error as e:
            logging.error(f"Error recording user creation: {e}")
            self.connection.rollback()

    def update_last_active(self, user_id: int):
        """Update the last active timestamp for a user"""
        try:
            self.cursor.execute("""
            UPDATE account_metadata
            SET last_active = CURRENT_TIMESTAMP
            WHERE user_id = ?
            """, (user_id,))
            self.connection.commit()
        except sqlite3.Error as e:
            logging.error(f"Error updating last active time: {e}")
            self.connection.rollback()

    def get_jobs_with_stats(self, employer_id):
        """
        Get all jobs with application counts and status.
        :param employer_id: The ID of the employer.
        :return: A list of dictionaries containing job details, application counts, and display status.
        """
        try:
            self.cursor.execute("""
                SELECT v.*, 
                       COUNT(a.application_id) as application_count,
                       CASE WHEN v.application_deadline < DATE('now') THEN 'expired'
                            ELSE v.status END as display_status
                FROM vacancies v
                LEFT JOIN applications a ON v.id = a.id
                WHERE v.employer_id = ?
                GROUP BY v.id
                ORDER BY v.application_deadline ASC
            """, (employer_id,))
            return [dict(row) for row in self.cursor.fetchall()]
        except sqlite3.Error as e:
            logging.error(f"Database error in get_jobs_with_stats: {e}")
            return []

    def get_vacancy_stats(self, job_id: int) -> dict:
        """
        Get comprehensive stats for a vacancy.
        :param job_id: The ID of the vacancy.
        :return: A dictionary containing vacancy statistics.
        """
        try:
            self.cursor.execute("""
                SELECT 
                    COUNT(*) AS total_applications,
                    COUNT(CASE WHEN status = 'approved' THEN 1 END) AS hires,
                    COUNT(CASE WHEN status = 'pending' THEN 1 END) AS pending,
                    AVG(julianday('now') - julianday(application_date)) AS avg_response_days
                FROM applications
                WHERE id = ?
            """, (job_id,))
            row = self.cursor.fetchone()
            return dict(row) if row else {}
        except sqlite3.Error as e:
            logging.error(f"Database error in get_vacancy_stats: {e}")
            return {}

    def renew_vacancy(self, job_id: int, new_deadline: str):
        """Update vacancy deadline and status"""
        self.cursor.execute("""
            UPDATE vacancies
            SET application_deadline = ?, status = 'approved'
            WHERE id = ?
        """, (new_deadline, job_id))
        self.connection.commit()

    def get_vacancy_title(self, job_id: int) -> str:
        """Get job title for confirmation messages"""
        self.cursor.execute("SELECT job_title FROM vacancies WHERE id = ?", (job_id,))
        result = self.cursor.fetchone()
        return result[0] if result else "Unnamed Position"

    def update_vacancy_status(self, id: int, new_status: str) -> bool:
        """
        Update the status of a specific vacancy in the vacancies table.

        :param id: The ID of the vacancy to update.
        :param new_status: The new status to set (must be one of 'pending', 'approved', 'rejected', 'closed', 'expired').
        :return: True if the update was successful, False otherwise.
        """
        # Validate the new status
        allowed_statuses = {'pending', 'approved', 'rejected', 'closed', 'expired'}
        if new_status.lower() not in allowed_statuses:
            logging.error(f"Invalid status provided: {new_status}")
            return False

        try:
            # Update the status in the database
            self.cursor.execute("""
                UPDATE vacancies
                SET status = ?
                WHERE id = ?
            """, (new_status.lower(), id))

            # Check if the update was successful
            if self.cursor.rowcount == 0:
                logging.warning(f"No vacancy found with ID {id}")
                return False

            # Commit the transaction
            self.connection.commit()
            logging.info(f"Updated vacancy {id} status to {new_status}")
            return True

        except sqlite3.Error as e:
            logging.error(f"Database error updating vacancy status: {e}")
            return False

    def get_employer_analytics(self, employer_id: int) -> dict:
        """Get comprehensive analytics for an employer with fixed approved/rejected counts"""
        try:
            # Basic metrics
            active_vacancies = self.get_active_vacancies_count(employer_id)
            total_applications = self.get_total_applications_count(employer_id)
            hire_rate = self.get_employer_hire_rate(employer_id)
            avg_response_time = self.get_avg_response_time(employer_id)
            member_since = self.get_member_since_date(employer_id)

            # Application status counts
            pending_applications = self.get_pending_applications_count(employer_id)
            reviewed_applications = self.get_reviewed_applications_count(employer_id)

            # Fixed approved/rejected counts using direct queries
            self.cursor.execute("""
                SELECT COUNT(*) FROM applications a
                JOIN vacancies v ON a.id = v.id
                WHERE v.employer_id = ? AND a.status = 'approved'
            """, (employer_id,))
            approved_applications = self.cursor.fetchone()[0] or 0

            self.cursor.execute("""
                SELECT COUNT(*) FROM applications a
                JOIN vacancies v ON a.id = v.id
                WHERE v.employer_id = ? AND a.status = 'rejected'
            """, (employer_id,))
            rejected_applications = self.cursor.fetchone()[0] or 0

            # Recent activity
            recent_activity = self.get_recent_activity(employer_id, limit=5)

            return {
                'active_vacancies': active_vacancies,
                'total_applications': total_applications,
                'hire_rate': hire_rate,
                'avg_response_time': avg_response_time,
                'member_since': member_since,
                'pending_applications': pending_applications,
                'reviewed_applications': reviewed_applications,
                'approved_applications': approved_applications,  # Now using direct query count
                'rejected_applications': rejected_applications,  # Now using direct query count
                'recent_activity': recent_activity
            }

        except sqlite3.Error as e:
            logging.error(f"Database error in get_employer_analytics: {e}")
            return {
                'active_vacancies': 0,
                'total_applications': 0,
                'hire_rate': 0,
                'avg_response_time': 0,
                'member_since': "N/A",
                'pending_applications': 0,
                'reviewed_applications': 0,
                'approved_applications': 0,
                'rejected_applications': 0,
                'recent_activity': []
            }

    def get_reviewed_applications_count(self, employer_id: int) -> int:
        """Get count of reviewed (non-pending) applications"""
        try:
            self.cursor.execute("""
                SELECT COUNT(*) 
                FROM applications a
                JOIN vacancies v ON a.id = v.id
                WHERE v.employer_id = ? 
                AND a.status != 'pending'
            """, (employer_id,))
            return self.cursor.fetchone()[0] or 0
        except sqlite3.Error as e:
            logging.error(f"Database error in get_reviewed_applications_count: {e}")
            return 0

    def get_rejected_applications_count(self, employer_id: int) -> int:
        """Get count of rejected applications"""
        try:
            self.cursor.execute("""
                SELECT COUNT(*) 
                FROM applications a
                JOIN vacancies v ON a.id = v.id
                WHERE v.employer_id = ? 
                AND a.status = 'rejected'
            """, (employer_id,))
            return self.cursor.fetchone()[0] or 0
        except sqlite3.Error as e:
            logging.error(f"Database error in get_rejected_applications_count: {e}")
            return 0

    def get_recent_activity(self, employer_id: int, limit: int = 5) -> list:
        """Get recent activity without relying on status_changed_at"""
        try:
            # Get recent application activity
            self.cursor.execute("""
                SELECT 
                    'application' AS type,
                    strftime('%Y-%m-%d', a.application_date) AS date,
                    'New application for: ' || v.job_title AS description
                FROM applications a
                JOIN vacancies v ON a.id = v.id
                WHERE v.employer_id = ?
                ORDER BY a.application_date DESC
                LIMIT ?
            """, (employer_id, limit))

            applications = self.cursor.fetchall()

            # Get recent status changes (using application_date as fallback)
            self.cursor.execute("""
                SELECT 
                    CASE 
                        WHEN a.status = 'approved' THEN 'approval'
                        WHEN a.status = 'rejected' THEN 'rejection'
                        ELSE 'review'
                    END AS type,
                    strftime('%Y-%m-%d', a.application_date) AS date,
                    v.job_title || ' application ' || a.status AS description
                FROM applications a
                JOIN vacancies v ON a.id = v.id
                WHERE v.employer_id = ? 
                AND a.status != 'pending'
                ORDER BY a.application_date DESC
                LIMIT ?
            """, (employer_id, limit))

            status_changes = self.cursor.fetchall()

            # Combine and sort all activity
            all_activity = [dict(row) for row in applications + status_changes]
            return sorted(all_activity, key=lambda x: x['date'], reverse=True)[:limit]

        except sqlite3.Error as e:
            logging.error(f"Database error in get_recent_activity: {e}")
            return []

    def get_performance_trends(self, employer_id: int) -> dict:
        """Get trends using only available columns"""
        try:
            trends = {'applications': [], 'hire_rate': [], 'response_time': []}

            # Get monthly application counts (using application_date)
            self.cursor.execute("""
                SELECT 
                    strftime('%Y-%m', a.application_date) AS month,
                    COUNT(*) AS count
                FROM applications a
                JOIN vacancies v ON a.id = v.id
                WHERE v.employer_id = ?
                AND date(a.application_date) >= date('now', '-6 months')
                GROUP BY strftime('%Y-%m', a.application_date)
                ORDER BY month
            """, (employer_id,))
            trends['applications'] = [dict(row) for row in self.cursor.fetchall()] or [{'month': 'N/A', 'count': 0}]

            # Get monthly hire rates
            self.cursor.execute("""
                SELECT 
                    strftime('%Y-%m', a.application_date) AS month,
                    (SUM(CASE WHEN a.status = 'approved' THEN 1 ELSE 0 END) * 100.0) / 
                    NULLIF(COUNT(*), 0) AS rate
                FROM applications a
                JOIN vacancies v ON a.id = v.id
                WHERE v.employer_id = ?
                AND date(a.application_date) >= date('now', '-6 months')
                GROUP BY strftime('%Y-%m', a.application_date)
                ORDER BY month
            """, (employer_id,))
            trends['hire_rate'] = [dict(row) for row in self.cursor.fetchall()] or [{'month': 'N/A', 'rate': 0}]

            # Simplified response time (using only application_date)
            trends['response_time'] = [{'month': 'N/A', 'days': 0}]  # Placeholder

            return trends
        except sqlite3.Error as e:
            logging.error(f"Database error in get_performance_trends: {e}")
            return {
                'applications': [{'month': 'N/A', 'count': 0}],
                'hire_rate': [{'month': 'N/A', 'rate': 0}],
                'response_time': [{'month': 'N/A', 'days': 0}]
            }

    def get_candidate_demographics(self, employer_id: int) -> dict:
        """Get candidate demographic breakdown"""
        try:
            demographics = {
                'gender': {},
                'education': {},
                'experience': {}
            }

            # Gender distribution
            self.cursor.execute("""
                SELECT 
                    u.gender,
                    COUNT(*) * 100.0 / (SELECT COUNT(*) 
                                       FROM applications a
                                       JOIN vacancies v ON a.id = v.id
                                       WHERE v.employer_id = ?) AS percentage
                FROM applications a
                JOIN vacancies v ON a.id = v.id
                JOIN users u ON a.job_seeker_id = u.user_id
                WHERE v.employer_id = ?
                GROUP BY u.gender
            """, (employer_id, employer_id))

            demographics['gender'] = {row[0]: round(row[1], 1) for row in self.cursor.fetchall()}

            # Education level
            self.cursor.execute("""
                SELECT 
                    u.qualification,
                    COUNT(*) * 100.0 / (SELECT COUNT(*) 
                                       FROM applications a
                                       JOIN vacancies v ON a.id = v.id
                                       WHERE v.employer_id = ?) AS percentage
                FROM applications a
                JOIN vacancies v ON a.id = v.id
                JOIN users u ON a.job_seeker_id = u.user_id
                WHERE v.employer_id = ?
                GROUP BY u.qualification
            """, (employer_id, employer_id))

            demographics['education'] = {row[0]: round(row[1], 1) for row in self.cursor.fetchall()}

            # Experience level (estimated from profile)
            self.cursor.execute("""
                SELECT 
                    CASE 
                        WHEN u.skills_experience LIKE '%junior%' THEN 'Junior'
                        WHEN u.skills_experience LIKE '%senior%' THEN 'Senior'
                        WHEN u.skills_experience LIKE '%mid-level%' THEN 'Mid-Level'
                        ELSE 'Not Specified'
                    END AS experience_level,
                    COUNT(*) * 100.0 / (SELECT COUNT(*) 
                                       FROM applications a
                                       JOIN vacancies v ON a.id = v.id
                                       WHERE v.employer_id = ?) AS percentage
                FROM applications a
                JOIN vacancies v ON a.id = v.id
                JOIN users u ON a.job_seeker_id = u.user_id
                WHERE v.employer_id = ?
                GROUP BY experience_level
            """, (employer_id, employer_id))

            demographics['experience'] = {row[0]: round(row[1], 1) for row in self.cursor.fetchall()}

            return demographics

        except sqlite3.Error as e:
            logging.error(f"Database error in get_candidate_demographics: {e}")
            return {}

    def get_industry_benchmarks(self, employer_id: int) -> dict:
        """Get industry benchmark comparisons"""
        try:
            # First get the employer's type
            self.cursor.execute("""
                SELECT employer_type FROM employers WHERE employer_id = ?
            """, (employer_id,))
            employer_type = self.cursor.fetchone()[0]

            if not employer_type:
                return {}

            # Get benchmarks for this employer type
            benchmarks = {
                'hire_rate': 0,
                'response_time': 0,
                'applications_per_job': 0
            }

            # Calculate average hire rate for this industry
            self.cursor.execute("""
                SELECT AVG(
                    (COUNT(CASE WHEN a.status = 'approved' THEN 1 END) * 100.0) / 
                    NULLIF(COUNT(a.application_id), 0)
                )
                FROM applications a
                JOIN vacancies v ON a.id = v.id
                JOIN employers e ON v.employer_id = e.employer_id
                WHERE e.employer_type = ?
            """, (employer_type,))

            benchmarks['hire_rate'] = round(self.cursor.fetchone()[0] or 0, 1)

            # Calculate average response time for this industry
            self.cursor.execute("""
                SELECT AVG(
                    julianday(a.status_changed_at) - julianday(a.application_date)
                )
                FROM applications a
                JOIN vacancies v ON a.id = v.id
                JOIN employers e ON v.employer_id = e.employer_id
                WHERE e.employer_type = ?
                AND a.status != 'pending'
            """, (employer_type,))

            benchmarks['response_time'] = round(self.cursor.fetchone()[0] or 0, 1)

            # Calculate average applications per job
            self.cursor.execute("""
                SELECT AVG(app_count)
                FROM (
                    SELECT COUNT(*) AS app_count
                    FROM applications a
                    JOIN vacancies v ON a.id = v.id
                    JOIN employers e ON v.employer_id = e.employer_id
                    WHERE e.employer_type = ?
                    GROUP BY v.id
                )
            """, (employer_type,))

            benchmarks['applications_per_job'] = round(self.cursor.fetchone()[0] or 0, 1)

            return benchmarks

        except sqlite3.Error as e:
            logging.error(f"Database error in get_industry_benchmarks: {e}")
            return {}

    def get_response_time_stats(self, user_id: int) -> dict:
        """Simplified response stats without status_changed_at"""
        return {
            'avg_response_time': 0,  # Placeholder
            'min_response_time': 0,
            'max_response_time': 0,
            'fast_responses': 0,
            'slow_responses': 0,
            'recent_responses': []
        }

    def can_user_review(self, reviewer_id: int, target_id: int, target_type: str) -> bool:
        """Check if user can leave a review with all eligibility checks"""
        try:
            from datetime import date

            # Rate limiting check
            today = date.today().isoformat()
            self.cursor.execute("""
                SELECT count FROM review_limits 
                WHERE user_id = ? AND date = ?
            """, (reviewer_id, today))
            result = self.cursor.fetchone()
            if result and result[0] >= 3:  # Max 3 reviews per day
                return False

            # Check for existing review
            self.cursor.execute("""
                SELECT 1 FROM reviews 
                WHERE reviewer_id = ? AND target_id = ? AND target_type = ?
                LIMIT 1
            """, (reviewer_id, target_id, target_type))
            if self.cursor.fetchone():
                return False

            # Additional checks for employer reviews
            if target_type == "employer":
                self.cursor.execute("""
                    SELECT 1 FROM applications a
                    JOIN vacancies v ON a.id = v.id
                    WHERE a.job_seeker_id = ? AND v.employer_id = ?
                    LIMIT 1
                """, (reviewer_id, target_id))
                if not self.cursor.fetchone():
                    return False

            return True

        except Exception as e:
            logging.error(f"Error in can_user_review: {e}")
            return False  # Fail-safe

    def add_review(self, reviewer_id: int, target_id: int, target_type: str,
                   rating: int, comment: str = None, dimension_ratings: dict = None) -> bool:
        """Add a review to the database with dimension ratings"""
        try:
            from datetime import date
            import json  # Required for dimension_ratings serialization

            # Get privacy settings
            self.cursor.execute("""
                SELECT show_name FROM rating_privacy 
                WHERE user_id = ?
            """, (reviewer_id,))
            privacy = self.cursor.fetchone()
            is_anonymous = not privacy[0] if privacy else False

            # Serialize dimension ratings to JSON
            dim_ratings_json = json.dumps(dimension_ratings) if dimension_ratings else None

            # Insert review with dimension_ratings
            self.cursor.execute("""
                INSERT INTO reviews (
                    reviewer_id, target_id, target_type, 
                    rating, comment, is_anonymous,
                    dimension_ratings, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (
                reviewer_id, target_id, target_type,
                rating, comment, is_anonymous,
                dim_ratings_json
            ))

            # Update rate limiting
            today = date.today().isoformat()
            self.cursor.execute("""
                INSERT INTO review_limits (user_id, date, count)
                VALUES (?, ?, 1)
                ON CONFLICT(user_id, date) DO UPDATE SET count = count + 1
            """, (reviewer_id, today))

            self.connection.commit()
            return True

        except Exception as e:
            self.connection.rollback()
            logging.error(f"Error adding review: {e}")
            return False

    def get_reviews(self, target_id: int, target_type: str,
                    sort_by: str = "recent", limit: int = 10, offset: int = 0) -> list:
        """Get reviews with sorting options"""
        sort_options = {
            "recent": "ORDER BY r.created_at DESC",
            "highest": "ORDER BY r.rating DESC",
            "lowest": "ORDER BY r.rating ASC",
            "most_helpful": "ORDER BY m.helpful_count DESC"
        }
        sort_clause = sort_options.get(sort_by, sort_options["recent"])

        query = f"""
            SELECT r.*, u.full_name, u.profile_summary
            FROM reviews r
            LEFT JOIN users u ON r.reviewer_id = u.user_id AND NOT r.is_anonymous
            LEFT JOIN review_metadata m ON r.id = m.review_id
            WHERE r.target_id = ? AND r.target_type = ?
            {sort_clause}
            LIMIT ? OFFSET ?
        """
        self.cursor.execute(query, (target_id, target_type, limit, offset))
        return self.cursor.fetchall()

    def flag_review(self, review_id: int, flagger_id: int, reason: str) -> bool:
        """Flag a review for admin moderation"""
        try:
            # Check if already flagged by this user
            self.cursor.execute("""
                SELECT 1 FROM flagged_reviews 
                WHERE review_id = ? AND flagged_by = ?
                LIMIT 1
            """, (review_id, flagger_id))
            if self.cursor.fetchone():
                return False

            # Add flag
            self.cursor.execute("""
                INSERT INTO flagged_reviews (review_id, flagged_by, reason)
                VALUES (?, ?, ?)
            """, (review_id, flagger_id, reason))

            # Update metadata
            self.cursor.execute("""
                INSERT INTO review_metadata (review_id, flags_count)
                VALUES (?, 1)
                ON CONFLICT(review_id) DO UPDATE SET flags_count = flags_count + 1
            """, (review_id,))

            # Notify admins
            admins = self.get_all_admins()
            for admin_id in admins:
                self.create_notification(
                    admin_id,
                    f"Review #{review_id} flagged: {reason}",
                    "flagged_review",
                    review_id
                )

            self.connection.commit()
            return True
        except sqlite3.Error as e:
            logging.error(f"Error flagging review: {e}")
            return False

    def get_review_stats(self, target_id: int, target_type: str) -> dict:
        """Get aggregated review statistics"""
        self.cursor.execute("""
            SELECT 
                COUNT(*) as total,
                AVG(rating) as average,
                COUNT(CASE WHEN rating = 5 THEN 1 END) as five_star,
                COUNT(CASE WHEN rating = 1 THEN 1 END) as one_star
            FROM reviews
            WHERE target_id = ? AND target_type = ?
        """, (target_id, target_type))
        stats = self.cursor.fetchone()

        return {
            "total_reviews": stats[0],
            "average_rating": round(stats[1], 1) if stats[1] else 0,
            "five_star_count": stats[2],
            "one_star_count": stats[3],
            "distribution": self.get_rating_distribution(target_id, target_type)
        }

    def get_rating_distribution(self, target_id: int, target_type: str) -> dict:
        """Get rating distribution for analytics"""
        self.cursor.execute("""
            SELECT rating, COUNT(*) 
            FROM reviews 
            WHERE target_id = ? AND target_type = ?
            GROUP BY rating
            ORDER BY rating DESC
        """, (target_id, target_type))
        return dict(self.cursor.fetchall())

    def get_review_privacy_settings(self, user_id: int) -> dict:
        """Get user's review privacy settings"""
        self.cursor.execute("""
            SELECT show_name, show_contact 
            FROM rating_privacy 
            WHERE user_id = ?
        """, (user_id,))
        result = self.cursor.fetchone()
        return {
            "show_name": bool(result[0]) if result else True,
            "show_contact": bool(result[1]) if result else False
        } if result else {"show_name": True, "show_contact": False}

    def toggle_setting(self, user_id: int, setting: str) -> bool:
        """Toggle a privacy setting atomically"""
        try:
            self.cursor.execute(f"""
                INSERT INTO rating_privacy (user_id, {setting})
                VALUES (?, FALSE)
                ON CONFLICT(user_id) DO UPDATE SET {setting} = NOT {setting}
            """, (user_id,))
            self.connection.commit()
            return True
        except sqlite3.Error as e:
            self.connection.rollback()
            logging.error(f"Database error in toggle_setting: {e}")
            return False

    def get_recently_interacted_users(self, user_id: int) -> list:
        """Get users recently interacted with (employers or job seekers)"""
        self.cursor.execute("""
            -- Get employers from applications
            SELECT DISTINCT e.employer_id as id, u.full_name as name, 'employer' as type
            FROM applications a
            JOIN jobs j ON a.job_id = j.id
            JOIN employers e ON j.employer_id = e.employer_id
            JOIN users u ON e.employer_id = u.user_id
            WHERE a.job_seeker_id = ?
            ORDER BY a.applied_at DESC
            LIMIT 20

            UNION

            -- Get job seekers from applications (if employer)
            SELECT DISTINCT a.job_seeker_id as id, u.full_name as name, 'job_seeker' as type
            FROM applications a
            JOIN users u ON a.job_seeker_id = u.user_id
            JOIN jobs j ON a.job_id = j.id
            WHERE j.employer_id = ?
            ORDER BY a.applied_at DESC
            LIMIT 20
        """, (user_id, user_id))
        return self.cursor.fetchall()

    def get_user_reviews(self, user_id: int) -> list:
        """Get all reviews written by a user"""
        self.cursor.execute("""
            SELECT r.id, r.target_id, r.target_type, r.rating, r.comment, 
                   r.created_at, r.is_anonymous,
                   CASE WHEN r.target_type = 'employer' THEN e.company_name
                        WHEN r.target_type = 'job_seeker' THEN u.full_name
                        ELSE 'JobBot' END as target_name
            FROM reviews r
            LEFT JOIN employers e ON r.target_id = e.employer_id AND r.target_type = 'employer'
            LEFT JOIN users u ON r.target_id = u.user_id AND r.target_type = 'job_seeker'
            WHERE r.reviewer_id = ?
            ORDER BY r.created_at DESC
        """, (user_id,))
        return self.cursor.fetchall()

    def get_review_details(self, review_id: int) -> dict:
        """Get complete details for a specific review"""
        try:
            self.cursor.execute("""
                SELECT 
                    r.id, r.reviewer_id, r.target_id, r.target_type, 
                    r.rating, r.comment, r.is_anonymous,
                    datetime(r.created_at) as created_at,
                    CASE 
                        WHEN r.target_type = 'employer' THEN e.company_name
                        WHEN r.target_type = 'job_seeker' THEN u.full_name
                        ELSE 'JobBot' 
                    END as target_name
                FROM reviews r
                LEFT JOIN employers e ON r.target_id = e.employer_id AND r.target_type = 'employer'
                LEFT JOIN users u ON r.target_id = u.user_id AND r.target_type = 'job_seeker'
                WHERE r.id = ?
            """, (review_id,))

            columns = [col[0] for col in self.cursor.description]
            result = self.cursor.fetchone()
            return dict(zip(columns, result)) if result else None

        except Exception as e:
            logging.error(f"Error getting review details: {e}")
            return None

    def search_reviews(self, search_term: str = None, target_type: str = None,
                       sort_by: str = "recent") -> list:
        """Search reviews with filters and sorting"""
        query = """
            SELECT r.*, 
                   CASE WHEN r.target_type = 'employer' THEN e.company_name
                        WHEN r.target_type = 'job_seeker' THEN u.full_name
                        ELSE 'JobBot' END as target_name,
                   CASE WHEN r.is_anonymous THEN 'Anonymous'
                        ELSE reviewer.full_name END as reviewer_name,
                   COALESCE(m.flags_count, 0) as flags_count
            FROM reviews r
            LEFT JOIN employers e ON r.target_id = e.employer_id AND r.target_type = 'employer'
            LEFT JOIN users u ON r.target_id = u.user_id AND r.target_type = 'job_seeker'
            LEFT JOIN users reviewer ON r.reviewer_id = reviewer.user_id
            LEFT JOIN review_metadata m ON r.id = m.review_id
        """

        params = []
        conditions = []

        if search_term:
            conditions.append("""
                (r.comment LIKE ? OR 
                 e.company_name LIKE ? OR 
                 u.full_name LIKE ? OR 
                 reviewer.full_name LIKE ?)
            """)
            search_param = f"%{search_term}%"
            params.extend([search_param] * 4)

        if target_type:
            conditions.append("r.target_type = ?")
            params.append(target_type)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        # Add sorting
        if sort_by == "recent":
            query += " ORDER BY r.created_at DESC"
        elif sort_by == "top":
            query += " ORDER BY r.rating DESC, r.created_at DESC"
        elif sort_by == "controversial":
            query += " ORDER BY flags_count DESC, r.created_at DESC"

        self.cursor.execute(query, params)
        return self.cursor.fetchall()

    def has_user_reviewed(self, user_id: int, target_id: int, target_type: str) -> bool:
        """Check if user already reviewed target today"""
        today = date.today().isoformat()
        self.cursor.execute("""
            SELECT 1 FROM reviews 
            WHERE reviewer_id = ? 
              AND target_id = ?
              AND target_type = ?
              AND date(created_at) = ?
            LIMIT 1
        """, (user_id, target_id, target_type, today))
        return bool(self.cursor.fetchone())

    def has_user_reviewed_any_today(self, user_id: int) -> bool:
        """Check if user has reviewed anyone today"""
        today = date.today().isoformat()
        self.cursor.execute("""
            SELECT 1 FROM reviews 
            WHERE reviewer_id = ? 
              AND date(created_at) = ?
            LIMIT 1
        """, (user_id, today))
        return bool(self.cursor.fetchone())

    def has_user_applied(self, user_id: int, job_id: int) -> bool:
        """
        Check if the user has already applied for a specific job.

        Args:
            user_id (int): The ID of the job seeker.
            job_id (int): The ID of the job post.

        Returns:
            bool: True if the user has already applied, False otherwise.
        """
        try:
            self.cursor.execute("""
                SELECT 1 
                FROM applications
                WHERE job_seeker_id = ? AND id = ?
                LIMIT 1
            """, (user_id, job_id))
            result = self.cursor.fetchone()
            return bool(result)
        except sqlite3.Error as e:
            logging.error(f"Database error in has_user_applied: {e}")
            return False

    def get_rateable_users(self, user_id: int) -> list:
        """Get users that the current user can rate"""
        try:
            # Employers the user has applied to
            self.cursor.execute("""
                SELECT DISTINCT 
                    e.employer_id as id, 
                    e.company_name as name, 
                    'employer' as type
                FROM applications a
                JOIN vacancies v ON a.id = v.id
                JOIN employers e ON v.employer_id = e.employer_id
                WHERE a.job_seeker_id = ?
            """, (user_id,))
            employers = self.cursor.fetchall()

            # Job seekers the employer has hired
            self.cursor.execute("""
                SELECT DISTINCT 
                    a.job_seeker_id as id,
                    u.full_name as name,
                    'job_seeker' as type
                FROM applications a
                JOIN users u ON a.job_seeker_id = u.user_id
                JOIN vacancies v ON a.id = v.id
                WHERE v.employer_id = ?
            """, (user_id,))
            job_seekers = self.cursor.fetchall()

            return employers + job_seekers

        except Exception as e:
            logging.error(f"Error getting rateable users: {e}")
            return []

    def get_user_name(self, user_id: int) -> str:
        """Get user's full name or company name"""
        try:
            # First try to get employer company name
            self.cursor.execute("""
                SELECT company_name FROM employers 
                WHERE employer_id = ?
            """, (user_id,))
            result = self.cursor.fetchone()
            if result:
                return result[0]

            # If not an employer, get user's full name
            self.cursor.execute("""
                SELECT full_name FROM users 
                WHERE user_id = ?
            """, (user_id,))
            result = self.cursor.fetchone()
            return result[0] if result else "Unknown User"

        except Exception as e:
            logging.error(f"Error getting user name: {e}")
            return "Unknown User"

    def delete_review(self, review_id: int) -> bool:
        """Delete a review by ID"""
        try:
            self.cursor.execute("DELETE FROM reviews WHERE id = ?", (review_id,))
            self.connection.commit()
            return self.cursor.rowcount > 0
        except Exception as e:
            logging.error(f"Error deleting review: {e}")
            return False

    def update_review(self, review_id: int, review_data: dict) -> bool:
        """Update an existing review"""
        try:
            # Convert dimension ratings to JSON string if they exist
            dimension_ratings = json.dumps(review_data.get("dimension_ratings", {}))

            self.cursor.execute("""
                UPDATE reviews 
                SET rating = ?, 
                    comment = ?,
                    dimension_ratings = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                review_data["rating"],
                review_data.get("comment", ""),
                dimension_ratings,
                review_id
            ))
            self.connection.commit()
            return self.cursor.rowcount > 0
        except Exception as e:
            logging.error(f"Error updating review: {e}")
            self.connection.rollback()
            return False
    #contact admin feature
    def get_contact_categories(self):
        """Retrieve active contact categories from database"""
        self.cursor.execute("SELECT id, name_key, emoji FROM contact_categories WHERE is_active = 1")
        categories = [dict(row) for row in self.cursor.fetchall()]
        return categories

    def get_user_contact_stats(self, user_id):
        """Get user's contact message statistics"""
        self.cursor.execute("""
           SELECT 
               COUNT(*) as total,
               SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
               SUM(CASE WHEN status = 'answered' THEN 1 ELSE 0 END) as answered
           FROM contact_messages 
           WHERE user_id = ?
           """, (user_id,))
        stats = self.cursor.fetchone()
        return dict(stats) if stats else None

    def save_contact_message(self, user_id, category_id, message_text, priority=1):
        """Save contact message to database"""
        self.cursor.execute("""
           INSERT INTO contact_messages 
           (user_id, category_id, message_text, priority)
           VALUES (?, ?, ?, ?)
           """, (user_id, category_id, message_text, priority))
        message_id = self.cursor.lastrowid
        self.connection.commit()
        return message_id

    def get_category_name(self, category_id):
        """Get category name by ID"""
        self.cursor.execute("SELECT name_key FROM contact_categories WHERE id = ?", (category_id,))
        result = self.cursor.fetchone()
        return result["name_key"] if result else "Unknown"

    def get_contact_message(self, message_id):
        """Get full contact message details"""
        self.cursor.execute("""
           SELECT 
               cm.*,
               cc.name_key as category_name
           FROM contact_messages cm
           JOIN contact_categories cc ON cm.category_id = cc.id
           WHERE cm.id = ?
           """, (message_id,))
        message = self.cursor.fetchone()
        return dict(message) if message else None

    def save_admin_reply(self, message_id, admin_id, reply_text):
        """Save admin reply to database"""
        self.cursor.execute("""
           UPDATE contact_messages 
           SET 
               status = 'answered',
               admin_id = ?,
               answer_text = ?,
               answered_at = CURRENT_TIMESTAMP
           WHERE id = ?
           """, (admin_id, reply_text, message_id))
        self.connection.commit()

    def get_contact_stats(self):
        """Return statistics for dashboard"""
        self.cursor.execute("""
           SELECT 
               COUNT(*) as total,
               SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
               SUM(CASE WHEN status = 'answered' THEN 1 ELSE 0 END) as answered,
               AVG(JULIANDAY(answered_at) - JULIANDAY(created_at)) * 24 as avg_response_time
           FROM contact_messages
           """)

        stats = self.cursor.fetchone()

        return {
            'total': stats['total'],
            'pending': stats['pending'],
            'answered': stats['answered'],
            'avg_response_time': round(stats['avg_response_time'] or 0, 1)
        }

    def get_paginated_messages(self, status='all', page=1, per_page=10):
        """Get paginated messages with filters"""
        offset = (page - 1) * per_page
        query = """
           SELECT 
               cm.id, 
               cm.user_id,
               cm.message_text,
               cc.name_key as category,
               cm.status,
               cm.priority,
               cm.created_at
           FROM contact_messages cm
           JOIN contact_categories cc ON cm.category_id = cc.id
           """

        if status != 'all':
            query += f" WHERE cm.status = '{status}'"

        query += " ORDER BY cm.created_at DESC LIMIT ? OFFSET ?"

        self.cursor.execute(query, (per_page, offset))
        messages = [dict(row) for row in self.cursor.fetchall()]

        return messages

    def get_category_stats(self) -> list:
        """Get statistics by category
        Returns:
            list: List of dictionaries containing category statistics
        """
        self.cursor.execute("""
        SELECT 
            cc.name_key as name,
            cc.emoji,
            COUNT(cm.id) as count,
            ROUND(COUNT(cm.id) * 100.0 / (SELECT COUNT(*) FROM contact_messages), 1) as percentage
        FROM contact_categories cc
        LEFT JOIN contact_messages cm ON cc.id = cm.category_id
        GROUP BY cc.id
        ORDER BY count DESC
        """)

        return [dict(row) for row in self.cursor.fetchall()]

    def update_contact_message(self, message_id: int, admin_id: int, status: str, response: str = None) -> bool:
        """
        Update a contact message with admin reply and status
        Args:
            message_id: ID of the message to update
            admin_id: ID of the admin handling the message
            status: New status ('pending', 'answered', 'closed')
            response: Optional response text (default: None)
        Returns:
            bool: True if update was successful, False otherwise
        """
        try:
            query = """
                UPDATE contact_messages 
                SET 
                    admin_id = ?,
                    status = ?,
                    answer_text = ?,
                    answered_at = CASE WHEN ? IS NOT NULL THEN CURRENT_TIMESTAMP ELSE answered_at END
                WHERE id = ?
            """
            self.cursor.execute(query, (admin_id, status, response, response, message_id))

            self.connection.commit()
            return self.cursor.rowcount > 0

        except Exception as e:
            logging.error(f"Error updating contact message {message_id}: {e}")
            self.connection.rollback()
            return False

    def get_contact_message_details(self, message_id: int) -> dict:
        """
        Get complete message details including category
        Returns dictionary with message details or None if not found
        """
        self.cursor.execute("""
           SELECT 
               cm.id,
               cm.user_id,
               cm.message_text as text,
               cm.status,
               cm.priority,
               cm.created_at,
               cm.answer_text as response,
               cm.answered_at,
               cc.name_key as category,
               cm.admin_id
           FROM contact_messages cm
           LEFT JOIN contact_categories cc ON cm.category_id = cc.id
           WHERE cm.id = ?
           """, (message_id,))

        result = self.cursor.fetchone()
        if not result:
            return None

        message_data = dict(result)


        message_data['admin'] = f"Admin ID: {message_data['admin_id']}" if message_data['admin_id'] else "Not assigned"

        return message_data

    def delete_contact_message(self, message_id: int) -> bool:
        """Permanently delete a contact message from database
        Args:
            message_id: ID of the message to delete
        Returns:
            bool: True if deletion was successful, False otherwise
        """
        try:
            self.cursor.execute("DELETE FROM contact_messages WHERE id = ?", (message_id,))
            self.connection.commit()
            return self.cursor.rowcount > 0

        except Exception as e:
            logging.error(f"Error deleting message {message_id}: {e}")
            self.connection.rollback()
            return False

    def search_users(self, search_term, page=1, page_size=5):
        """
        Search for users (job seekers and employers) based on a search term.

        Args:
            search_term (str): The search term (name, ID, or partial match).
            page (int): The current page number.
            page_size (int): Number of results per page.

        Returns:
            list: A list of dictionaries containing user details.
        """
        offset = (page - 1) * page_size
        term = f"%{search_term}%" if search_term else ""

        query = """
            SELECT 
                user_id AS id, 
                full_name AS name, 
                'job_seeker' AS type 
            FROM users 
            WHERE registration_type = 'job_seeker' AND (? = '' OR full_name LIKE ? OR CAST(user_id AS TEXT) LIKE ?)
            UNION ALL
            SELECT 
                employer_id AS id, 
                company_name AS name, 
                'employer' AS type 
            FROM employers 
            WHERE (? = '' OR company_name LIKE ? OR CAST(employer_id AS TEXT) LIKE ?)
            LIMIT ? OFFSET ?
        """

        params = (search_term, term, term, search_term, term, term, page_size, offset)

        try:
            self.cursor.execute(query, params)
            results = self.cursor.fetchall()

            # Convert results to a list of dictionaries for easier handling
            columns = ["id", "name", "type"]
            return [dict(zip(columns, row)) for row in results]
        except sqlite3.Error as e:
            logging.error(f"Error searching users: {e}")
            return []

    def get_total_pages_users(self, search_term, page_size=5):
        """
        Get the total number of pages for user search results.

        Args:
            search_term (str): The search term (name, ID, or partial match).
            page_size (int): Number of results per page.

        Returns:
            int: Total number of pages.
        """
        term = f"%{search_term}%" if search_term else ""

        query = """
            SELECT COUNT(*)
            FROM (
                SELECT user_id 
                FROM users 
                WHERE registration_type = 'job_seeker' AND (? = '' OR full_name LIKE ? OR CAST(user_id AS TEXT) LIKE ?)
                UNION ALL
                SELECT employer_id 
                FROM employers 
                WHERE (? = '' OR company_name LIKE ? OR CAST(employer_id AS TEXT) LIKE ?)
            )
        """

        params = (search_term, term, term, search_term, term, term)

        try:
            self.cursor.execute(query, params)
            total = self.cursor.fetchone()[0]
            return (total // page_size) + (1 if total % page_size else 0)
        except sqlite3.Error as e:
            logging.error(f"Error getting total pages for users: {e}")
            return 0

    def add_status_column_to_vacancies(self):
        try:
            # Check if the 'status' column exists
            self.cursor.execute("PRAGMA table_info(vacancies);")
            columns = [column[1] for column in self.cursor.fetchall()]
            if "status" not in columns:
                # Add the 'status' column with a default value of 'approved' and valid values constraint
                self.cursor.execute("""
                ALTER TABLE vacancies ADD COLUMN status TEXT DEFAULT 'approved' 
                CHECK (status IN ('pending', 'approved', 'rejected', 'closed'));
                """)
                self.connection.commit()
        except sqlite3.Error as e:
            print(f"Error adding 'status' column: {e}")

    def normalize_vacancy_statuses(self):
        """
        Normalize the 'status' column in vacancies to ensure all rows have valid statuses.
        """
        try:
            self.cursor.execute("""
                UPDATE vacancies 
                SET status = CASE 
                    WHEN status = 'open' THEN 'approved'
                    WHEN status = 'filled' THEN 'closed'
                    WHEN status IS NULL OR status = '' THEN 'pending'
                    ELSE status
                END
            """)
            self.connection.commit()
            print("Vacancy statuses normalized.")
        except sqlite3.Error as e:
            print(f"Error normalizing vacancy statuses: {e}")

    def set_default_status_for_existing_jobs(self):
        try:
            # Set the default status for existing vacancies to 'approved'
            self.cursor.execute("UPDATE vacancies SET status = 'approved' WHERE status IS NULL;")
            self.connection.commit()
        except sqlite3.Error as e:
            print(f"Error setting default status: {e}")

    def get_pending_job_posts(self):
        """
        Fetch job posts with status 'pending' from job_posts.
        """
        try:
            self.cursor.execute("""
                SELECT id, employer_id, job_title, employment_type, gender, 
                       quantity, level, description, qualification, skills, salary, benefits, deadline, status, source, reason_for_rejection
                FROM job_posts
                WHERE status = 'pending'
            """)
            rows = self.cursor.fetchall()

            # Debugging: Log raw pending jobs
            logging.debug(f"Raw pending jobs fetched: {rows}")

            return rows
        except sqlite3.Error as e:
            logging.error(f"Database error fetching pending job posts: {e}")
            return []

    def move_to_vacancies(self, job_id: int) -> int:
        try:
            # Fetch the approved job post
            self.cursor.execute("""
                SELECT employer_id, job_title, employment_type, gender, 
                       quantity, level, description, qualification, skills, salary, benefits, deadline
                FROM job_posts
                WHERE id = ? AND status = 'approved'
            """, (job_id,))
            job_post = self.cursor.fetchone()

            if not job_post:
                logging.error(f"Failed to find job post with ID {job_id} in job_posts.")
                return None

            job_dict = dict(zip([desc[0] for desc in self.cursor.description], job_post))

            # Validate the job post before moving
            try:
                validate_job_post_data(job_dict)
            except ValueError as ve:
                logging.error(f"Validation error while moving job post {job_id}: {ve}")
                return None

            # Insert into vacancies
            self.cursor.execute("""
                INSERT INTO vacancies (
                    id, employer_id, job_title, employment_type, gender, 
                    quantity, level, description, qualification, skills, salary, benefits, application_deadline, status, source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job_id, job_dict["employer_id"], job_dict["job_title"], job_dict["employment_type"],
                job_dict["gender"], job_dict["quantity"], job_dict["level"], job_dict["description"],
                job_dict["qualification"], job_dict["skills"], job_dict["salary"], job_dict["benefits"],
                job_dict["deadline"], "approved", "vacancy"
            ))

            self.connection.commit()

            # Delete from job_posts
            self.cursor.execute("DELETE FROM job_posts WHERE id = ?", (job_id,))
            self.connection.commit()

            logging.info(f"Job post {job_id} moved to vacancies successfully.")
            return job_id
        except Exception as e:
            logging.error(f"Error moving job post {job_id} to vacancies: {e}")
            return None

    def save_application(self, job_seeker_id, vacancy_id, cover_letter):
        """Save a job application."""
        try:
            # Insert the application into the applications table
            self.cursor.execute("""
                INSERT INTO applications (job_seeker_id, id, cover_letter, application_date, status)
                VALUES (?, ?, ?, datetime('now'), 'pending')
            """, (job_seeker_id, vacancy_id, cover_letter))
            self.connection.commit()
        except sqlite3.Error as e:
            logging.error(f"Database error saving application: {e}")
            raise ValueError("Failed to save application") from e

    def get_cover_letter_for_job(self, job_seeker_id: int, id: int) -> str:
        """
        Retrieve the cover letter for a specific job application.
        """
        self.cursor.execute("""
        SELECT cover_letter FROM applications 
        WHERE job_seeker_id = ? AND id = ?
        """, (job_seeker_id, id))
        result = self.cursor.fetchone()
        return result[0] if result else ""

    def add_reason_for_rejection_column(self):
        try:
            # Check if the 'reason_for_rejection' column exists
            self.cursor.execute("PRAGMA table_info(job_posts);")
            columns = [column[1] for column in self.cursor.fetchall()]
            if "reason_for_rejection" not in columns:
                # Add the 'reason_for_rejection' column
                self.cursor.execute("ALTER TABLE job_posts ADD COLUMN reason_for_rejection TEXT;")
                self.connection.commit()
        except sqlite3.Error as e:
            print(f"Error adding 'reason_for_rejection' column: {e}")

    def has_any_application(self, user_id: int) -> bool:
        """Check if user has applied to any job"""
        self.cursor.execute("""
            SELECT 1 FROM applications 
            WHERE job_seeker_id = ? 
            LIMIT 1
        """, (user_id,))
        return bool(self.cursor.fetchone())

    def get_user_rating_stats(self, user_id: int) -> dict:
        """
        Get comprehensive statistics about a user's rating activity
        Returns:
            {
                "total_reviews": int,
                "average_rating": float,
                "rating_distribution": dict,
                "reviews_by_type": dict,
                "recent_activity": list,
                "daily_average": float,
                "helpful_votes": int,
                "flags_received": int
            }
        """
        try:
            stats = {}

            # Total reviews given
            self.cursor.execute("""
                SELECT COUNT(*) FROM reviews 
                WHERE reviewer_id = ?
            """, (user_id,))
            stats["total_reviews"] = self.cursor.fetchone()[0] or 0

            # Average rating given
            self.cursor.execute("""
                SELECT AVG(rating) FROM reviews 
                WHERE reviewer_id = ?
            """, (user_id,))
            stats["average_rating"] = round(float(self.cursor.fetchone()[0] or 0), 1)

            # Rating distribution (1-5 stars)
            self.cursor.execute("""
                SELECT rating, COUNT(*) 
                FROM reviews 
                WHERE reviewer_id = ?
                GROUP BY rating
                ORDER BY rating
            """, (user_id,))
            stats["rating_distribution"] = dict(self.cursor.fetchall())

            # Reviews by target type
            self.cursor.execute("""
                SELECT target_type, COUNT(*) 
                FROM reviews 
                WHERE reviewer_id = ?
                GROUP BY target_type
            """, (user_id,))
            stats["reviews_by_type"] = dict(self.cursor.fetchall())

            # Recent activity (last 5 reviews)
            self.cursor.execute("""
                SELECT target_type, rating, created_at 
                FROM reviews 
                WHERE reviewer_id = ?
                ORDER BY created_at DESC 
                LIMIT 5
            """, (user_id,))
            stats["recent_activity"] = [
                {"type": row[0], "rating": row[1], "date": row[2]}
                for row in self.cursor.fetchall()
            ]

            # Daily average reviews
            self.cursor.execute("""
                SELECT COUNT(*) / COUNT(DISTINCT date(created_at)) 
                FROM reviews 
                WHERE reviewer_id = ?
            """, (user_id,))
            stats["daily_average"] = round(float(self.cursor.fetchone()[0] or 0), 2)

            # Helpful votes received
            self.cursor.execute("""
                SELECT COALESCE(SUM(helpful_count), 0)
                FROM review_metadata rm
                JOIN reviews r ON rm.review_id = r.id
                WHERE r.reviewer_id = ?
            """, (user_id,))
            stats["helpful_votes"] = self.cursor.fetchone()[0]

            # Flags received
            self.cursor.execute("""
                SELECT COALESCE(SUM(flags_count), 0)
                FROM review_metadata rm
                JOIN reviews r ON rm.review_id = r.id
                WHERE r.reviewer_id = ?
            """, (user_id,))
            stats["flags_received"] = self.cursor.fetchone()[0]

            return stats

        except Exception as e:
            logging.error(f"Error getting user rating stats: {e}")
            return {
                "total_reviews": 0,
                "average_rating": 0.0,
                "rating_distribution": {},
                "reviews_by_type": {},
                "recent_activity": [],
                "daily_average": 0.0,
                "helpful_votes": 0,
                "flags_received": 0
            }

    # def add_job_summary_column(self):
    #     try:
    #         # Check if the 'job_summary' column exists
    #         self.cursor.execute("PRAGMA table_info(job_posts);")
    #         columns = [column[1] for column in self.cursor.fetchall()]
    #         if "job_summary" not in columns:
    #             # Add the 'job_summary' column
    #             self.cursor.execute("ALTER TABLE job_posts ADD COLUMN job_summary TEXT;")
    #             self.connection.commit()
    #     except sqlite3.Error as e:
    #         print(f"Error adding 'job_summary' column: {e}")
    #
    # def add_min_requirements_column(self):
    #     try:
    #         # Check if the 'min_requirements' column exists
    #         self.cursor.execute("PRAGMA table_info(job_posts);")
    #         columns = [column[1] for column in self.cursor.fetchall()]
    #         if "min_requirements" not in columns:
    #             # Add the 'min_requirements' column
    #             self.cursor.execute("ALTER TABLE job_posts ADD COLUMN min_requirements TEXT;")
    #             self.connection.commit()
    #     except sqlite3.Error as e:
    #         print(f"Error adding 'min_requirements' column: {e}")

    def add_missing_vacancies_columns(self):
        try:
            # Check if the 'vacancies' table exists
            self.cursor.execute("PRAGMA table_info(vacancies);")
            columns = [column[1] for column in self.cursor.fetchall()]

            # Add missing columns if they don't exist
            if "gender" not in columns:
                self.cursor.execute("ALTER TABLE vacancies ADD COLUMN gender TEXT;")
            if "level" not in columns:
                self.cursor.execute("ALTER TABLE vacancies ADD COLUMN level TEXT;")
            if "description" not in columns:
                self.cursor.execute("ALTER TABLE vacancies ADD COLUMN description TEXT;")
            if "qualification" not in columns:
                self.cursor.execute("ALTER TABLE vacancies ADD COLUMN qualification TEXT;")
            if "skills" not in columns:
                self.cursor.execute("ALTER TABLE vacancies ADD COLUMN skills TEXT;")

            self.connection.commit()
        except sqlite3.Error as e:
            print(f"Error adding missing columns to vacancies table: {e}")

    # def set_default_status_for_job_posts(self):
    #     """
    #     Set default status ('pending') for job posts where status is NULL.
    #     """
    #     try:
    #         # Update only rows where status is NULL
    #         self.cursor.execute("UPDATE job_posts SET status = 'pending' WHERE status IS NULL;")
    #         self.connection.commit()
    #     except sqlite3.Error as e:
    #         print(f"Error setting default status for job posts: {e}")
    #

    def remove_job_summary_and_min_requirements_columns(self):
        try:
            # Check if the 'job_summary' column exists and remove it
            self.cursor.execute("PRAGMA table_info(job_posts);")
            columns = [column[1] for column in self.cursor.fetchall()]
            if "job_summary" in columns:
                self.cursor.execute("ALTER TABLE job_posts DROP COLUMN job_summary;")

            # Check if the 'min_requirements' column exists and remove it
            if "min_requirements" in columns:
                self.cursor.execute("ALTER TABLE job_posts DROP COLUMN min_requirements;")

            # Repeat for the vacancies table
            self.cursor.execute("PRAGMA table_info(vacancies);")
            columns = [column[1] for column in self.cursor.fetchall()]
            if "job_summary" in columns:
                self.cursor.execute("ALTER TABLE vacancies DROP COLUMN job_summary;")

            if "min_requirements" in columns:
                self.cursor.execute("ALTER TABLE vacancies DROP COLUMN min_requirements;")

            self.connection.commit()
        except sqlite3.Error as e:
            print(f"Error removing columns: {e}")

    def normalize_job_post_statuses(self):
        """
        Normalize the 'status' column in job_posts to ensure all rows have valid statuses.
        """
        try:
            self.cursor.execute("""
                UPDATE job_posts 
                SET status = CASE 
                    WHEN status IS NULL OR status = '' THEN 'pending'
                    WHEN status NOT IN ('pending', 'approved', 'rejected', 'closed') THEN 'unknown'
                    ELSE status
                END
            """)
            self.connection.commit()
            print("Job post statuses normalized.")
        except sqlite3.Error as e:
            print(f"Error normalizing job post statuses: {e}")

    def add_status_column_to_applications(self):
        try:
            # Check if the 'status' column exists
            self.cursor.execute("PRAGMA table_info(applications);")
            columns = [column[1] for column in self.cursor.fetchall()]
            if "status" not in columns:
                # Add the 'status' column with a default value of 'pending'
                self.cursor.execute("ALTER TABLE applications ADD COLUMN status TEXT DEFAULT 'pending';")
                self.connection.commit()
        except sqlite3.Error as e:
            print(f"Error adding 'status' column to applications table: {e}")


        except sqlite3.Error as e:
            print(f"Error normalizing vacancy statuses: {e}")
    def normalize_application_statuses(self):
        try:
            self.cursor.execute("""
                UPDATE applications 
                SET status = CASE 
                    WHEN status = 'pending' THEN 'pending'
                    WHEN status = 'reviewed' THEN 'reviewed'
                    WHEN status = 'approved' THEN 'approved'
                    WHEN status = 'rejected' THEN 'rejected'
                    ELSE 'pending'  -- Default to 'pending' for invalid statuses
                END
            """)
            self.connection.commit()
        except sqlite3.Error as e:
            print(f"Error normalizing application statuses: {e}")

    def get_job_post_by_id(self, job_id: int):
        self.cursor.execute("""
            SELECT id AS job_id, 'job_post' AS source, employer_id, job_title, employment_type, gender, quantity, level, 
                   description, qualification, skills, salary, benefits, deadline, status
            FROM job_posts WHERE id = ?
        """, (job_id,))
        columns = [column[0] for column in self.cursor.description]
        result = self.cursor.fetchone()
        if result:
            job_dict = dict(zip(columns, result))
            validate_job_post(job_dict)  # Validate the dictionary
            return job_dict
        return None

    def get_cv_path_for_job_seeker(self, job_seeker_id: int) -> str:
        """
        Retrieve the CV path for a job seeker.
        """
        self.cursor.execute("""
        SELECT cv_path FROM users 
        WHERE user_id = ?
        """, (job_seeker_id,))
        result = self.cursor.fetchone()
        return result[0] if result else None

    def get_employer_id(self, user_id: int) -> int:
        """Retrieve the employer_id for a given user_id."""
        self.cursor.execute("SELECT employer_id FROM employers WHERE employer_id = ?", (user_id,))
        result = self.cursor.fetchone()
        return result[0] if result else None

    def fix_invalid_job_post_statuses(self):
        try:
            self.cursor.execute("""
                UPDATE job_posts
                SET status = 'pending'
                WHERE status NOT IN ('pending', 'approved', 'rejected', 'closed')
            """)
            self.connection.commit()
            print("Invalid job post statuses fixed.")
        except sqlite3.Error as e:
            print(f"Error fixing invalid job post statuses: {e}")

    def get_vacancy_by_id(self, job_id: int):
        self.cursor.execute("""
            SELECT id AS job_id, 'vacancy' AS source, employer_id, job_title, employment_type, gender, quantity, level, 
                   description, qualification, skills, salary, benefits, application_deadline, status
            FROM vacancies WHERE id = ?
        """, (job_id,))
        columns = [column[0] for column in self.cursor.description]
        result = self.cursor.fetchone()
        if result:
            vacancy_dict = dict(zip(columns, result))
            validate_job_post(vacancy_dict)  # Validate the dictionary
            return vacancy_dict
        return None

    def vacancy_belongs_to_employer(self, id: int, employer_id: int):
        """Check if a vacancy belongs to the specified employer."""
        self.cursor.execute("SELECT COUNT(*) FROM vacancies WHERE id = ? AND employer_id = ?",
                            (id, employer_id))
        return self.cursor.fetchone()[0] > 0

    def add_status_column_to_job_posts(self):
        try:
            self.cursor.execute("PRAGMA table_info(job_posts);")
            columns = [column[1] for column in self.cursor.fetchall()]
            if "status" not in columns:
                self.cursor.execute("""
                    ALTER TABLE job_posts ADD COLUMN status TEXT DEFAULT 'pending'
                    CHECK (status IN ('pending', 'approved', 'rejected', 'closed'));
                """)
                self.connection.commit()
        except sqlite3.Error as e:
            print(f"Error adding 'status' column to job_posts: {e}")

    def add_registration_type_column(self):
        try:
            # Check if the 'registration_type' column exists
            self.cursor.execute("PRAGMA table_info(users);")
            columns = [column[1] for column in self.cursor.fetchall()]
            if "registration_type" not in columns:
                # Add the 'registration_type' column with a default value of NULL
                self.cursor.execute("ALTER TABLE users ADD COLUMN registration_type TEXT;")
                self.connection.commit()
        except sqlite3.Error as e:
            print(f"Error adding 'registration_type' column: {e}")

    def get_all_job_seekers(self):
        """Fetch all job seekers from the users table."""
        self.cursor.execute("SELECT user_id, full_name FROM users WHERE registration_type = 'job_seeker'")
        return self.cursor.fetchall()

    def get_all_employers(self):
        """Fetch all employers from the employers table."""
        self.cursor.execute("SELECT employer_id, company_name FROM employers")
        return self.cursor.fetchall()

    def get_all_applications(self):
        """Fetch all applications from the applications table."""
        self.cursor.execute("""
        SELECT applications.application_id, vacancies.job_title, users.full_name
        FROM applications
        JOIN vacancies ON applications.id = vacancies.id
        JOIN users ON applications.job_seeker_id = users.user_id
        """)
        return self.cursor.fetchall()

    def remove_job_seeker(self, user_id):
        """Remove a job seeker and related data."""
        self.cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        self.connection.commit()

    def remove_employer(self, employer_id):
        """Remove an employer and their job posts."""
        self.cursor.execute("DELETE FROM vacancies WHERE employer_id = ?", (employer_id,))
        self.cursor.execute("DELETE FROM employers WHERE employer_id = ?", (employer_id,))
        self.cursor.execute("DELETE FROM users WHERE user_id = ?", (employer_id,))
        self.connection.commit()

    def remove_application(self, application_id):
        """Remove an application."""
        self.cursor.execute("DELETE FROM applications WHERE application_id = ?", (application_id,))
        self.connection.commit()

    def clear_all_data(self):
        """Clear all data from relevant tables."""
        try:
            # Step 1: Clear dependent tables first (to avoid foreign key constraint violations)
            self.cursor.execute("DELETE FROM applications")  # Applications depend on users and vacancies
            self.cursor.execute("DELETE FROM vacancies")  # Vacancies depend on employers
            self.cursor.execute("DELETE FROM employers")  # Employers depend on users

            # Step 2: Clear the users table
            self.cursor.execute("DELETE FROM users")

            # Commit changes
            self.connection.commit()
        except sqlite3.Error as e:
            self.connection.rollback()

    def normalize_registration_type(self):
        try:
            # Update registration_type for users who are employers
            self.cursor.execute("""
                UPDATE users
                SET registration_type = 'employer'
                WHERE user_id IN (SELECT employer_id FROM employers);
            """)
            # Update registration_type for other users (default to 'job_seeker')
            self.cursor.execute("""
                UPDATE users
                SET registration_type = 'job_seeker'
                WHERE registration_type IS NULL;
            """)
            self.connection.commit()
        except sqlite3.Error as e:
            print(f"Error normalizing registration_type: {e}")

    def normalize_user_profiles(self):
        try:
            # Add the 'registration_type' column if it doesn't exist
            self.cursor.execute("PRAGMA table_info(users);")
            columns = [column[1] for column in self.cursor.fetchall()]
            if "registration_type" not in columns:
                self.cursor.execute("ALTER TABLE users ADD COLUMN registration_type TEXT;")

            # Set default value for existing rows
            self.cursor.execute("""
                UPDATE users 
                SET registration_type = CASE 
                    WHEN employer_id IS NOT NULL THEN 'employer'
                    ELSE 'job_seeker'
                END
                WHERE registration_type IS NULL;
            """)
            self.connection.commit()
        except sqlite3.Error as e:
            print(f"Error normalizing user profiles: {e}")

    # def add_employer_id_column(self):
    #     """Add the employer_id column to the employers table if it doesn't exist."""
    #     try:
    #         # Check if the 'employer_id' column exists
    #         self.cursor.execute("PRAGMA table_info(employers);")
    #         columns = [column[1] for column in self.cursor.fetchall()]
    #         if "employer_id" not in columns:
    #             # Add the 'employer_id' column with a foreign key reference to users(user_id)
    #             self.cursor.execute("""
    #                    ALTER TABLE employers ADD COLUMN employer_id INTEGER PRIMARY KEY
    #                    REFERENCES users(user_id) ON DELETE CASCADE;
    #                """)
    #             print("employer_id column added to employers table.")
    #         else:
    #             print("employer_id column already exists in employers table.")
    #     except sqlite3.Error as e:
    #         print(f"Error adding employer_id column: {e}")
    #     finally:
    #         self.connection.commit()

    def add_reason_for_rejection_column(self):
        """
        Add or modify the 'reason_for_rejection' column in the job_posts table with a default value of 'Not applicable'.
        """
        try:
            # Check if the 'reason_for_rejection' column exists
            self.cursor.execute("PRAGMA table_info(job_posts);")
            columns = [column[1] for column in self.cursor.fetchall()]

            if "reason_for_rejection" not in columns:
                # Add the 'reason_for_rejection' column with a default value of 'Not applicable'
                self.cursor.execute("""
                    ALTER TABLE job_posts ADD COLUMN reason_for_rejection TEXT DEFAULT 'Not applicable';
                """)
                print("Added 'reason_for_rejection' column with default value 'Not applicable'.")
            else:
                # Modify the existing 'reason_for_rejection' column to set default value for NULL rows
                self.cursor.execute("""
                    UPDATE job_posts 
                    SET reason_for_rejection = 'Not applicable' 
                    WHERE reason_for_rejection IS NULL OR reason_for_rejection = '';
                """)
                print(
                    "Updated 'reason_for_rejection' column to set default value 'Not applicable' for NULL or empty rows.")

            self.connection.commit()
        except sqlite3.Error as e:
            print(f"Error modifying 'reason_for_rejection' column: {e}")

    def normalize_reason_for_rejection(self):
        """
        Normalize the 'reason_for_rejection' column to ensure all rows have a valid value ('Not applicable' for NULL or empty).
        """
        try:
            self.cursor.execute("""
                UPDATE job_posts 
                SET reason_for_rejection = 'Not applicable' 
                WHERE reason_for_rejection IS NULL OR reason_for_rejection = '';
            """)
            self.connection.commit()
            print("Reason for rejection normalized.")
        except sqlite3.Error as e:
            print(f"Error normalizing reason_for_rejection: {e}")

    def add_source_column_to_job_posts(self):
        """
        Add a 'source' column to the job_posts table with a default value of 'job_post'.
        """
        try:
            # Check if the 'source' column exists in the job_posts table
            self.cursor.execute("PRAGMA table_info(job_posts);")
            columns = [column[1] for column in self.cursor.fetchall()]
            if "source" not in columns:
                # Add the 'source' column with a default value of 'job_post'
                self.cursor.execute("""
                    ALTER TABLE job_posts ADD COLUMN source TEXT DEFAULT 'job_post';
                """)
                print("Added 'source' column to job_posts table with default value 'job_post'.")
            else:
                print("'source' column already exists in job_posts table.")
        except sqlite3.Error as e:
            print(f"Error adding 'source' column to job_posts table: {e}")

    # def add_source_column_to_vacancies(self):
    #     """
    #     Add a 'source' column to the vacancies table with a default value of 'vacancy'.
    #     """
    #     try:
    #         # Check if the 'source' column exists in the vacancies table
    #         self.cursor.execute("PRAGMA table_info(vacancies);")
    #         columns = [column[1] for column in self.cursor.fetchall()]
    #         if "source" not in columns:
    #             # Add the 'source' column with a default value of 'vacancy'
    #             self.cursor.execute("""
    #                 ALTER TABLE vacancies ADD COLUMN source TEXT DEFAULT 'vacancy';
    #             """)
    #             print("Added 'source' column to vacancies table with default value 'vacancy'.")
    #         else:
    #             print("'source' column already exists in vacancies table.")
    #     except sqlite3.Error as e:
    #         print(f"Error adding 'source' column to vacancies table: {e}")

    def normalize_job_post_sources(self):
        """
        Normalize the 'source' column in job_posts to ensure all rows have 'job_post' as the default value.
        """
        try:
            self.cursor.execute("""
                UPDATE job_posts SET source = 'job_post' WHERE source IS NULL OR source = '';
            """)
            self.connection.commit()
            print("Normalized 'source' column in job_posts table.")
        except sqlite3.Error as e:
            print(f"Error normalizing 'source' column in job_posts table: {e}")

    def normalize_vacancy_sources(self):
        """
        Normalize the 'source' column in vacancies to ensure all rows have 'vacancy' as the default value.
        """
        try:
            self.cursor.execute("""
                UPDATE vacancies SET source = 'vacancy' WHERE source IS NULL OR source = '';
            """)
            self.connection.commit()
            print("Normalized 'source' column in vacancies table.")
        except sqlite3.Error as e:
            print(f"Error normalizing 'source' column in vacancies table: {e}")

    def fetch_pending_jobs(self):
        """
        Fetch all pending job posts from the job_posts table.
        """
        try:
            # Enable sqlite3.Row factory to return rows as dictionary-like objects
            self.connection.row_factory = sqlite3.Row
            self.cursor = self.connection.cursor()

            # Query to fetch pending jobs
            self.cursor.execute("""
                SELECT * FROM job_posts WHERE status = 'pending'
            """)
            rows = self.cursor.fetchall()

            print(f"Raw pending jobs from DB: {rows}")  # Debugging log

            jobs = []
            for row in rows:
                job_dict = dict(row)  # Explicit conversion to dictionary
                print(f"Fetched job keys: {job_dict.keys()}")  # Debugging log

                # Debugging status field
                status_value = job_dict.get("status", "MISSING_STATUS")
                print(f"Status field value: {status_value}")

                # Debugging source field
                source_value = job_dict.get("source", "MISSING_SOURCE")
                print(f"Source field value: {source_value}")

                # Validate the job post before adding it to the result list

                jobs.append(validate_job_post(job_dict))  # Validate after conversion

            return jobs

        except ValueError as ve:
            print(f"Validation error in fetch_pending_jobs: {ve}")
            return []  # Return an empty list if validation fails

        except sqlite3.Error as e:
            print(f"Database error in fetch_pending_jobs: {e}")
            return []  # Return an empty list if a database error occurs

    def get_job_post_status(self, job_id: int) -> str:
        """
        Fetch the status of a job post by job_id.
        """
        try:
            # Query the database for the job post's status
            self.cursor.execute("SELECT status FROM job_posts WHERE id = ?", (job_id,))
            result = self.cursor.fetchone()

            if result:
                return result[0]  # Return the status value
            else:
                print(f"Warning: Job post with ID {job_id} not found.")
                return None  # Job not found

        except sqlite3.Error as e:
            print(f"Database error fetching job post status: {e}")
            return None  # Return None on error

    def get_all_jobs(self):
        self.cursor.execute("SELECT * FROM job_posts")
        return self.cursor.fetchall()

    def get_all_vacancies(self):
        self.cursor.execute("SELECT * FROM vacancies")
        return self.cursor.fetchall()

    def search_job_seekers(self, search_term, page=1, page_size=5):
        offset = (page - 1) * page_size
        query = """
            SELECT user_id, full_name FROM users 
            WHERE registration_type = 'job_seeker'
            AND (? = '' OR full_name LIKE ? OR CAST(user_id AS TEXT) LIKE ?)
            LIMIT ? OFFSET ?
        """
        term = f"%{search_term}%" if search_term else ""
        self.cursor.execute(query, (search_term, term, term, page_size, offset))
        return self.cursor.fetchall()

    def get_total_pages_job_seekers(self, search_term, page_size=5):
        query = """
            SELECT COUNT(*) FROM users 
            WHERE registration_type = 'job_seeker'
            AND (? = '' OR full_name LIKE ? OR CAST(user_id AS TEXT) LIKE ?)
        """
        term = f"%{search_term}%" if search_term else ""
        self.cursor.execute(query, (search_term, term, term))
        total = self.cursor.fetchone()[0]
        return (total // page_size) + (1 if total % page_size else 0)

    def search_employers(self, search_term, page=1, page_size=5):
        offset = (page - 1) * page_size
        query = """
            SELECT employer_id, company_name FROM employers 
            WHERE (? = '' OR company_name LIKE ? OR CAST(employer_id AS TEXT) LIKE ?)
            LIMIT ? OFFSET ?
        """
        term = f"%{search_term}%" if search_term else ""
        self.cursor.execute(query, (search_term, term, term, page_size, offset))
        return self.cursor.fetchall()

    def get_total_pages_employers(self, search_term, page_size=5):
        query = """
            SELECT COUNT(*) FROM employers 
            WHERE (? = '' OR company_name LIKE ? OR CAST(employer_id AS TEXT) LIKE ?)
        """
        term = f"%{search_term}%" if search_term else ""
        self.cursor.execute(query, (search_term, term, term))
        total = self.cursor.fetchone()[0]
        return (total // page_size) + (1 if total % page_size else 0)

    def search_applications(self, search_term, page=1, page_size=5):
        offset = (page - 1) * page_size
        query = """
            SELECT a.application_id, v.job_title, u.full_name 
            FROM applications a
            JOIN vacancies v ON a.id = v.id
            JOIN users u ON a.job_seeker_id = u.user_id
            WHERE (? = '' OR v.job_title LIKE ? OR u.full_name LIKE ?)
            LIMIT ? OFFSET ?
        """
        term = f"%{search_term}%" if search_term else ""
        self.cursor.execute(query, (search_term, term, term, page_size, offset))
        return self.cursor.fetchall()

    def get_total_pages_applications(self, search_term, page_size=5):
        query = """
            SELECT COUNT(*) 
            FROM applications a
            JOIN vacancies v ON a.id = v.id
            JOIN users u ON a.job_seeker_id = u.user_id
            WHERE (? = '' OR v.job_title LIKE ? OR u.full_name LIKE ?)
        """
        term = f"%{search_term}%" if search_term else ""
        self.cursor.execute(query, (search_term, term, term))
        total = self.cursor.fetchone()[0]
        return (total // page_size) + (1 if total % page_size else 0)

    def get_all_job_seekers_details(self):
        self.cursor.execute("""
            SELECT 
                user_id, 
                full_name, 
                contact_number,
                dob,
                cv_path,
                languages,
                qualification,
                field_of_study,
                cgpa,
                skills_experience,
                profile_summary
            FROM users 
            WHERE registration_type = 'job_seeker'
        """)
        return self.cursor.fetchall()

    def get_all_employers_details(self):
        """Fetch all employer details."""
        self.cursor.execute("""
            SELECT employer_id, company_name, contact_number, city, employer_type, about_company, verification_docs
            FROM employers
        """)
        return self.cursor.fetchall()

    def get_all_applications_details(self):
        """Fetch all application details with related job, job seeker, and employer information."""
        self.cursor.execute("""
            SELECT 
                a.application_id AS "Application ID",
                v.job_title AS "Job Title",
                u.full_name AS "Job Seeker Name",
                e.company_name AS "Employer Name",
                a.application_date AS "Application Date",
                a.status AS "Status",
                a.cover_letter AS "Cover Letter",
                v.id AS "Vacancy ID"
            FROM applications a
            JOIN vacancies v ON a.id = v.id
            JOIN users u ON a.job_seeker_id = u.user_id
            JOIN employers e ON v.employer_id = e.employer_id
        """)
        return self.cursor.fetchall()

    def get_all_job_posts(self):
        """
        Fetch all job posts from both job_posts and vacancies tables.
        """
        try:
            self.cursor.execute("""
                SELECT id AS ID, company_name AS Employer, job_title AS Title, employment_type AS Type,
                       deadline AS Deadline, status AS Status, 'job_post' AS Source
                FROM job_posts
                JOIN employers ON job_posts.employer_id = employers.employer_id
                UNION ALL
                SELECT id AS ID, company_name AS Employer, job_title AS Title, employment_type AS Type,
                       application_deadline AS Deadline, status AS Status, 'vacancy' AS Source
                FROM vacancies
                JOIN employers ON vacancies.employer_id = employers.employer_id
            """)
            rows = self.cursor.fetchall()
            return [dict(row) for row in rows]  # Convert rows to dictionaries
        except sqlite3.Error as e:
            print(f"Error fetching all job posts: {e}")
            return []

    def get_all_vacancies_posts(self):
        """
        Fetch all vacancies with all details from the vacancies table.
        """
        self.cursor.execute("""
            SELECT 
                id AS ID,
                job_title AS "Job Title",
                employment_type AS "Employment Type",
                gender AS Gender,
                quantity AS Quantity,
                level AS Level,
                description AS Description,
                qualification AS Qualification,
                skills AS Skills,
                salary AS Salary,
                benefits AS Benefits,
                application_deadline AS "Application Deadline",
                status AS Status,
                source AS Source,
                e.company_name AS Employer
            FROM vacancies
            JOIN employers e ON vacancies.employer_id = e.employer_id
        """)
        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]  # Convert rows to dictionaries

    def search_jobs(self, search_term, page=1, page_size=5):
        offset = (page - 1) * page_size
        query = """
            SELECT v.id, v.job_title, e.company_name AS employer_name 
            FROM vacancies v
            JOIN employers e ON v.employer_id = e.employer_id
            WHERE (? = '' OR v.job_title LIKE ? OR e.company_name LIKE ?)
            LIMIT ? OFFSET ?
        """
        term = f"%{search_term}%" if search_term else ""
        self.cursor.execute(query, (search_term, term, term, page_size, offset))
        return self.cursor.fetchall()

    def get_total_pages_jobs(self, search_term, page_size=5):
        query = """
            SELECT COUNT(*) 
            FROM vacancies v
            JOIN employers e ON v.employer_id = e.employer_id
            WHERE (? = '' OR v.job_title LIKE ? OR e.company_name LIKE ?)
        """
        term = f"%{search_term}%" if search_term else ""
        self.cursor.execute(query, (search_term, term, term))
        total = self.cursor.fetchone()[0]
        return (total // page_size) + (1 if total % page_size else 0)

    def search_vacancies(self, search_term, page=1, page_size=5):
        offset = (page - 1) * page_size
        query = """
            SELECT id, job_title, employer_id, application_deadline 
            FROM vacancies 
            WHERE job_title LIKE ? OR CAST(id AS TEXT) LIKE ?
            LIMIT ? OFFSET ?
        """
        term = f"%{search_term}%"
        self.cursor.execute(query, (term, term, page_size, offset))
        return self.cursor.fetchall()

    def get_total_pages_vacancies(self, search_term, page_size=5):
        query = """
            SELECT COUNT(*) 
            FROM vacancies 
            WHERE job_title LIKE ? OR CAST(id AS TEXT) LIKE ?
        """
        term = f"%{search_term}%"
        self.cursor.execute(query, (term, term))
        total = self.cursor.fetchone()[0]
        return (total // page_size) + (1 if total % page_size else 0)

    def get_all_vacancies_details(self):
        self.cursor.execute("""
            SELECT id, employer_id, job_title, employment_type, 
                   application_deadline, status 
            FROM vacancies
        """)
        return self.cursor.fetchall()

    def fetch_notifications(self, limit=10):
        """Fetch pending notifications with a limit."""
        self.cursor.execute("SELECT * FROM notifications ORDER BY timestamp ASC LIMIT ?", (limit,))
        return self.cursor.fetchall()

    def clear_notifications(self, limit=10):
        """Clear processed notifications with a limit."""
        self.cursor.execute(
            "DELETE FROM notifications WHERE id IN (SELECT id FROM notifications ORDER BY timestamp ASC LIMIT ?)",
            (limit,))
        self.connection.commit()

    def delete_user_account(self, user_id):
        """Delete the user's account from the database."""
        self.cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        self.connection.commit()

    def delete_employer_account(self, employer_id):
        try:
            # Delete the employer's record from the employers table
            self.cursor.execute("DELETE FROM employers WHERE employer_id = ?", (employer_id,))

            # Delete the user's record from the users table
            self.cursor.execute("DELETE FROM users WHERE user_id = ?", (employer_id,))

            self.conn.commit()
            print(f"Employer account {employer_id} deleted successfully.")
        except Exception as e:
            print(f"Error deleting employer account {employer_id}: {e}")

    def update_user_language(self, user_id, language):
        """Update the user's language preference in the database."""
        self.cursor.execute("""
            UPDATE users SET language = ? WHERE user_id = ?
        """, (language, user_id))
        self.connection.commit()

    def save_decision(self, application_id, decision, rejection_reason=None, employer_message=None):
        """
        Save a decision (approved/rejected) for an application in the application_decisions table.
        """
        try:
            self.cursor.execute("""
                INSERT INTO application_decisions (
                    application_id, decision, rejection_reason, employer_message
                ) VALUES (?, ?, ?, ?)
            """, (application_id, decision, rejection_reason, employer_message))
            self.connection.commit()
            print(f"Decision saved successfully for application ID: {application_id}")
        except Exception as e:
            print(f"Error saving decision for application ID {application_id}: {e}")
    def get_latest_decision(self, application_id):
        """
        Fetch the latest decision for an application from the application_decisions table.
        """
        try:
            self.cursor.execute("""
                SELECT * FROM application_decisions
                WHERE application_id = ?
                ORDER BY decision_date DESC
                LIMIT 1
            """, (application_id,))
            decision = self.cursor.fetchone()
            return decision
        except Exception as e:
            print(f"Error fetching latest decision for application ID {application_id}: {e}")
            return None

    def update_application_status(self, application_id, status, rejection_reason=None):
        """
        Update the status of an application in the applications table.
        Args:
            application_id: ID of the application
            status: New status ('pending', 'approved', 'rejected')
            rejection_reason: Optional reason for rejection (if status is 'rejected')
        """
        try:
            if status == 'rejected' and rejection_reason:
                self.cursor.execute("""
                    UPDATE applications
                    SET status = ?, rejection_reason = ?
                    WHERE application_id = ?
                """, (status, rejection_reason, application_id))
            else:
                self.cursor.execute("""
                    UPDATE applications
                    SET status = ?
                    WHERE application_id = ?
                """, (status, application_id))
            self.connection.commit()
            print(f"Application status updated successfully for application ID: {application_id}")
        except Exception as e:
            print(f"Error updating application status for application ID {application_id}: {e}")
    def ban_user(self, user_id=None, employer_id=None, reason=None, entity_type=None):
        """Ban a user or employer with strict validation."""
        # Debug: Log all incoming parameters
        logging.info(
            f"ban_user() called with: user_id={user_id}, employer_id={employer_id}, "
            f"reason='{reason}', entity_type='{entity_type}'"
        )
        # Validate reason (ensure it's not empty and is a string)
        if not reason or not isinstance(reason, str) or reason.strip() == "":
            raise ValueError("Ban reason must be a non-empty string.")
        # Validate entity type and ID
        if entity_type not in ("job_seeker", "employer"):
            raise ValueError("Invalid entity_type. Must be 'job_seeker' or 'employer'.")
        if entity_type == "job_seeker" and not user_id:
            raise ValueError("user_id is required for job_seeker bans.")
        elif entity_type == "employer" and not employer_id:
            raise ValueError("employer_id is required for employer bans.")
        # Proceed with the ban
        try:
            if entity_type == "job_seeker":
                query = "INSERT INTO bans (user_id, reason) VALUES (?, ?)"
                self.cursor.execute(query, (user_id, reason))
            elif entity_type == "employer":
                query = "INSERT INTO bans (employer_id, reason) VALUES (?, ?)"
                self.cursor.execute(query, (employer_id, reason))
            self.connection.commit()
        except Exception as e:
            logging.error(f"Database error in ban_user(): {e}")
            raise

    def unban_user(self, user_id: int):
        """Unban a user by removing them from the bans table."""
        self.cursor.execute("DELETE FROM bans WHERE user_id = ?", (user_id,))
        self.connection.commit()

    def unban_employer(self, employer_id: int):
        """Unban an employer by removing them from the bans table."""
        self.cursor.execute("DELETE FROM bans WHERE employer_id = ?", (employer_id,))
        self.connection.commit()

    def is_user_banned(self, user_id: int = None, employer_id: int = None) -> bool:
        """
        Check if a user or employer is banned.
        Args:
            user_id (int): The user ID to check (for job seekers).
            employer_id (int): The employer ID to check (for employers).
        Returns:
            bool: True if banned, False otherwise.
        """
        if user_id is not None:
            self.cursor.execute("""
            SELECT COUNT(*) FROM bans WHERE user_id = ?
            """, (user_id,))
            return self.cursor.fetchone()[0] > 0
        elif employer_id is not None:
            self.cursor.execute("""
            SELECT COUNT(*) FROM bans WHERE employer_id = ?
            """, (employer_id,))
            return self.cursor.fetchone()[0] > 0
        else:
            raise ValueError("Either user_id or employer_id must be provided.")

    def get_ban_reason(self, user_id: int = None, employer_id: int = None) -> str:
        """
        Get the reason for a ban.
        Args:
            user_id (int): The user ID to check (for job seekers).
            employer_id (int): The employer ID to check (for employers).
        Returns:
            str: The ban reason.
        """
        if user_id is not None:
            self.cursor.execute("""
            SELECT reason FROM bans WHERE user_id = ?
            """, (user_id,))
            result = self.cursor.fetchone()
            return result[0] if result else "No reason provided"
        elif employer_id is not None:
            self.cursor.execute("""
            SELECT reason FROM bans WHERE employer_id = ?
            """, (employer_id,))
            result = self.cursor.fetchone()
            return result[0] if result else "No reason provided"
        else:
            raise ValueError("Either user_id or employer_id must be provided.")

    #before
    def get_banned_users(self):
        """
        Get all banned users (job seekers and employers) with their details.
        Returns:
            list: List of dictionaries containing banned users and employers.
        """
        query = """
        SELECT 
            CASE 
                WHEN b.user_id IS NOT NULL THEN u.full_name 
                WHEN b.employer_id IS NOT NULL THEN e.company_name 
            END as name,
            b.user_id, 
            b.employer_id, 
            b.reason, 
            b.banned_at,
            CASE
                WHEN b.user_id IS NOT NULL THEN 'job_seeker'
                WHEN b.employer_id IS NOT NULL THEN 'employer'
            END as entity_type
        FROM bans b
        LEFT JOIN users u ON b.user_id = u.user_id
        LEFT JOIN employers e ON b.employer_id = e.employer_id
        """
        self.cursor.execute(query)
        columns = [column[0] for column in self.cursor.description]
        return [dict(zip(columns, row)) for row in self.cursor.fetchall()]

    def create_appeal(self, user_id: int, content: str) -> None:
        """Create a new ban appeal."""
        self.cursor.execute(
            "INSERT INTO appeals (user_id, content) VALUES (?, ?)",
            (user_id, content)
        )
        self.connection.commit()

    def get_appeal(self, user_id: int) -> dict:
        """Get the latest appeal for a user."""
        self.cursor.execute(
            "SELECT * FROM appeals WHERE user_id = ? ORDER BY appeal_id DESC LIMIT 1",
            (user_id,)
        )
        columns = [column[0] for column in self.cursor.description]
        row = self.cursor.fetchone()
        return dict(zip(columns, row)) if row else None

    def update_appeal_status(self, user_id: int, status: str) -> None:
        """Update the status of an appeal."""
        valid_statuses = ['pending', 'approved', 'rejected', 'more_info_needed', 'ban_lifted','ban_upheld', 'info_requested']
        if status not in valid_statuses:
            raise ValueError(f"Invalid status. Must be one of: {valid_statuses}")

        self.cursor.execute(
            "UPDATE appeals SET status = ? WHERE user_id = ? AND status = 'pending'",
            (status, user_id)
        )
        self.connection.commit()

     # Returns list of user_ids of currently logged-in admins

    def search_job_seekers_for_ban(self, search_term, page=1, page_size=5):
        """
        Search for job seekers specifically for banning purposes.

        Args:
            search_term (str): The search term (name, ID, or empty for all).
            page (int): The current page number.
            page_size (int): Number of results per page.

        Returns:
            list: List of job seekers matching the search criteria.
        """
        offset = (page - 1) * page_size
        query = """
            SELECT user_id, full_name FROM users 
            WHERE registration_type = 'job_seeker'
            AND (? = '' OR full_name LIKE ? OR CAST(user_id AS TEXT) LIKE ?)
            LIMIT ? OFFSET ?
        """
        term = f"%{search_term}%" if search_term else ""
        self.cursor.execute(query, (search_term, term, term, page_size, offset))
        return self.cursor.fetchall()

    def get_total_pages_job_seekers_for_ban(self, search_term, page_size=5):
        """
        Get the total number of pages for job seekers specifically for banning purposes.

        Args:
            search_term (str): The search term (name, ID, or empty for all).
            page_size (int): Number of results per page.

        Returns:
            int: Total number of pages.
        """
        query = """
            SELECT COUNT(*) FROM users 
            WHERE registration_type = 'job_seeker'
            AND (? = '' OR full_name LIKE ? OR CAST(user_id AS TEXT) LIKE ?)
        """
        term = f"%{search_term}%" if search_term else ""
        self.cursor.execute(query, (search_term, term, term))
        total = self.cursor.fetchone()[0]
        return (total // page_size) + (1 if total % page_size else 0)

    def search_employers_for_ban(self, search_term, page=1, page_size=5):
        """
        Search for employers specifically for banning purposes.

        Args:
            search_term (str): The search term (company name, ID, or empty for all).
            page (int): The current page number.
            page_size (int): Number of results per page.

        Returns:
            list: List of employers matching the search criteria.
        """
        offset = (page - 1) * page_size
        query = """
            SELECT employer_id, company_name FROM employers 
            WHERE (? = '' OR company_name LIKE ? OR CAST(employer_id AS TEXT) LIKE ?)
            LIMIT ? OFFSET ?
        """
        term = f"%{search_term}%" if search_term else ""
        self.cursor.execute(query, (search_term, term, term, page_size, offset))
        return self.cursor.fetchall()

    def get_total_pages_employers_for_ban(self, search_term, page_size=5):
        """
        Get the total number of pages for employers specifically for banning purposes.

        Args:
            search_term (str): The search term (company name, ID, or empty for all).
            page_size (int): Number of results per page.

        Returns:
            int: Total number of pages.
        """
        query = """
            SELECT COUNT(*) FROM employers 
            WHERE (? = '' OR company_name LIKE ? OR CAST(employer_id AS TEXT) LIKE ?)
        """
        term = f"%{search_term}%" if search_term else ""
        self.cursor.execute(query, (search_term, term, term))
        total = self.cursor.fetchone()[0]
        return (total // page_size) + (1 if total % page_size else 0)

    def log_error(self, error_data: dict) -> str:
        """Log an error to the database with enhanced details"""
        error_id = str(uuid4())
        try:
            # Get the full traceback with local variables
            exc_type, exc_value, exc_tb = sys.exc_info()
            full_traceback = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))

            self.cursor.execute("""
            INSERT INTO bot_errors (
                error_id, timestamp, user_id, chat_id, command,
                error_type, error_message, traceback, status,
                context_data, update_data
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                error_id,
                datetime.now().isoformat(),
                error_data.get("user_id"),
                error_data.get("chat_id"),
                error_data.get("command"),
                error_data.get("error_type", "Unknown"),
                str(error_data.get("error_message", "No message")),
                full_traceback,
                "unresolved",
                json.dumps(error_data.get("context_data")) if error_data.get("context_data") else None,
                json.dumps(error_data.get("update_data")) if hasattr(error_data.get("update"), 'to_dict') else None
            ))
            self.connection.commit()
            return error_id
        except Exception as e:
            logging.error(f"Error logging error record {error_id}: {e}")
            # Fallback to console logging if DB fails
            print(f"Failed to log error {error_id}:")
            traceback.print_exc()
            return error_id

    def get_errors(self, limit: int = 50, status: str = None) -> list:
        """Retrieve errors from database"""
        query = "SELECT * FROM bot_errors"
        params = []

        if status:
            query += " WHERE status = ?"
            params.append(status)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        self.cursor.execute(query, params)
        errors = []
        for row in self.cursor.fetchall():
            error = dict(row)
            # Convert JSON strings back to objects
            for field in ['context_data', 'update_data']:
                if error.get(field):
                    try:
                        error[field] = json.loads(error[field])
                    except (json.JSONDecodeError, TypeError):
                        error[field] = None
            errors.append(error)
        return errors
    def get_error_by_id(self, error_id: str) -> Optional[dict]:
        """Get a specific error by ID"""
        self.cursor.execute("""
        SELECT * FROM bot_errors WHERE error_id = ?
        """, (error_id,))
        row = self.cursor.fetchone()
        if row:
            error = dict(row)
            # Convert JSON strings back to objects
            for field in ['context_data', 'update_data']:
                if error.get(field):
                    try:
                        error[field] = json.loads(error[field])
                    except (json.JSONDecodeError, TypeError):
                        error[field] = None
            return error
        return None

    def update_error_status(self, error_id: str, status: str) -> bool:
        """Update error status"""
        try:
            self.cursor.execute("""
            UPDATE bot_errors SET status = ? WHERE error_id = ?
            """, (status, error_id))
            self.connection.commit()
            return self.cursor.rowcount > 0
        except Exception as e:
            logging.error(f"Error updating error status {error_id}: {e}")
            return False



    # def migrate_vacancies_table(self):
    #     try:
    #         # Step 1: Check if the 'vacancies' table exists
    #         self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='vacancies';")
    #         vacancies_exists = self.cursor.fetchone()
    #
    #         if not vacancies_exists:
    #             print("Vacancies table does not exist. Migration is not needed.")
    #             return
    #
    #         self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='old_vacancies';")
    #         old_vacancies_exists = self.cursor.fetchone()
    #
    #         if old_vacancies_exists:
    #             # Drop the existing 'old_vacancies' table to avoid conflicts
    #             print("Old_vacancies table already exists. Dropping it before migration.")
    #             self.cursor.execute("DROP TABLE old_vacancies;")
    #             self.connection.commit()
    #
    #         # Step 2: Rename the existing 'vacancies' table to 'old_vacancies'
    #         self.cursor.execute("ALTER TABLE vacancies RENAME TO old_vacancies;")
    #         print("Renamed 'vacancies' table to 'old_vacancies'.")
    #
    #         # Step 3: Create the new 'vacancies' table with 'id' as the primary key
    #         self.cursor.execute("""
    #             CREATE TABLE vacancies (
    #                 id INTEGER PRIMARY KEY,  -- Use the same ID as job_posts
    #                 employer_id INTEGER NOT NULL,
    #                 job_title TEXT NOT NULL,
    #                 employment_type TEXT NOT NULL,
    #                 gender TEXT NOT NULL CHECK (gender IN ('Male', 'Female', 'Any')),
    #                 quantity INTEGER NOT NULL CHECK (quantity > 0),
    #                 level TEXT NOT NULL,
    #                 description TEXT NOT NULL,
    #                 qualification TEXT NOT NULL,
    #                 skills TEXT NOT NULL,
    #                 salary TEXT,
    #                 benefits TEXT,
    #                 application_deadline TEXT NOT NULL ,
    #                 status TEXT DEFAULT 'approved' CHECK (status IN ('pending', 'approved', 'rejected', 'closed')),
    #                 source TEXT DEFAULT 'vacancy',
    #                 FOREIGN KEY (employer_id) REFERENCES employers(employer_id) ON DELETE CASCADE
    #             );
    #         """)
    #         print("Created new 'vacancies' table.")
    #
    #         # Step 4: Migrate data from 'old_vacancies' to the new 'vacancies' table
    #         self.cursor.execute("PRAGMA table_info(old_vacancies);")
    #         columns = [column[1] for column in self.cursor.fetchall()]
    #
    #         if "application_deadline" in columns:
    #             # Use 'application_deadline' instead of 'deadline'
    #             self.cursor.execute("""
    #                 INSERT INTO vacancies (id, employer_id, job_title, employment_type, gender, quantity, level,
    #                                        description, qualification, skills, salary, benefits, application_deadline, status, source)
    #                 SELECT id, employer_id, job_title, employment_type, gender, quantity, level,
    #                        description, qualification, skills, salary, benefits, application_deadline, status, source
    #                 FROM old_vacancies;
    #             """)
    #         else:
    #             raise ValueError("Column 'application_deadline' not found in old_vacancies table.")
    #
    #         print("Migrated data from 'old_vacancies' to 'vacancies'.")
    #
    #         # Step 5: Drop the 'old_vacancies' table
    #         self.cursor.execute("DROP TABLE old_vacancies;")
    #         print("Dropped 'old_vacancies' table.")
    #
    #         # Step 6: Commit changes
    #         self.connection.commit()
    #     except sqlite3.Error as e:
    #         print(f"Error during vacancies table migration: {e}")
    #         self.connection.rollback()
# Initialize database
if __name__ == "__main__":
    db = Database()
    # db.migrate_vacancies_table()
    print("Database and tables created successfully!")
