# import sqlite3
# class DatabaseUpdater:
#     def __init__(self, db_path="db/database.db"):
#         self.connection = sqlite3.connect(db_path)
#         self.cursor = self.connection.cursor()
#
#     def add_notification_table(self):
#         """Create a table to store real-time notifications."""
#         try:
#             self.cursor.execute("""
#                 CREATE TABLE IF NOT EXISTS notifications (
#                     id INTEGER PRIMARY KEY AUTOINCREMENT,
#                     user_id INTEGER NOT NULL,
#                     action TEXT NOT NULL,
#                     timestamp TEXT DEFAULT (datetime('now'))
#                 )
#             """)
#             self.connection.commit()
#             print("Notifications table created successfully.")
#         except sqlite3.Error as e:
#             print(f"Error creating notifications table: {e}")
#
#     def add_triggers(self):
#         """Add triggers for real-time updates."""
#         try:
#             # Trigger for removing job seekers
#             self.cursor.execute("""
#             CREATE TRIGGER IF NOT EXISTS notify_job_seeker_removal
#             AFTER DELETE ON users
#             FOR EACH ROW
#             BEGIN
#                 INSERT INTO notifications (user_id, action)
#                 VALUES (OLD.user_id, 'removed');
#             END;
#             """)
#             self.connection.commit()
#             print("Trigger 'notify_job_seeker_removal' added successfully.")
#         except sqlite3.Error as e:
#             print(f"Error adding triggers: {e}")
#
#     def close(self):
#         self.connection.close()
#
# if __name__ == "__main__":
#     # Initialize the database updater
#     updater = DatabaseUpdater()
#
#     # Add the notifications table
#     updater.add_notification_table()
#
#     # Add the triggers
#     updater.add_triggers()
#
#     # Close the connection
#     updater.close()
#     print("Database update completed successfully.")
#

import sqlite3
from pathlib import Path


def add_employer_id_to_bans_table(db_path=None):
    """Add employer_id column to bans table if it doesn't exist"""
    if db_path is None:
        # Get absolute path to the database file
        base_dir = Path(__file__).parent.parent
        db_path = base_dir / "db" / "database.db"

    print(f"Connecting to database at: {db_path}")

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if column already exists
        cursor.execute("PRAGMA table_info(bans)")
        columns = [column[1] for column in cursor.fetchall()]

        if 'employer_id' not in columns:
            print("Adding employer_id column to bans table...")
            cursor.execute("""
                ALTER TABLE bans
                ADD COLUMN employer_id INTEGER
            """)
            conn.commit()
            print("Successfully added employer_id column")
        else:
            print("employer_id column already exists")

    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"General error: {e}")
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    add_employer_id_to_bans_table()