import sqlite3
import numpy as np
import pickle, warnings
from datetime import datetime


# functions fr numpy arrays fr db
def adapt_array(arr):
    return pickle.dumps(arr)


def convert_array(text):
    return pickle.loads(text)

sqlite3.register_adapter(np.ndarray, adapt_array)
sqlite3.register_converter("array", convert_array)


def get_connection_to_database(db_file="attendance.db"):
    conn = None
    try:
        conn = sqlite3.connect(db_file, detect_types=sqlite3.PARSE_DECLTYPES)
        return conn
    except sqlite3.Error as e:
        print(f"Database connection error: {e}")
    return conn


def setup_database_tables_if_needed():
    #setup table
    conn = get_connection_to_database()
    if conn is not None:
        try:
            c = conn.cursor()
            #create std table
            c.execute("""CREATE TABLE IF NOT EXISTS students
                         (
                             roll_no
                             INTEGER
                             PRIMARY
                             KEY,
                             name
                             TEXT
                             NOT
                             NULL,
                             face_encoding
                             array
                             NOT
                             NULL
                         );""")

            #create attend table
            c.execute("""CREATE TABLE IF NOT EXISTS attendance_records
            (
                record_id
                INTEGER
                PRIMARY
                KEY
                AUTOINCREMENT,
                roll_no
                INTEGER
                NOT
                NULL,
                attendance_date
                TEXT
                NOT
                NULL,
                attendance_time
                TEXT
                NOT
                NULL,
                FOREIGN
                KEY
                         (
                roll_no
                         ) REFERENCES students
                         (
                             roll_no
                         ) ON DELETE CASCADE
                );""")

            c.execute("PRAGMA user_version = 1")
            c.execute("PRAGMA user_version")
            db_version = c.fetchone()[0]
            if db_version < 2:
                warnings.warn("Database schema might be outdated. Consider running migrations.", UserWarning)

            conn.commit()
        except sqlite3.Error as e:
            print(f"Error creating tables: {e}")
        finally:
            conn.close()


def save_new_student_to_db(roll_no, name, face_encoding):
    conn = get_connection_to_database()
    sql = ''' INSERT INTO students(roll_no, name, face_encoding) \
              VALUES (?, ?, ?) '''
    try:
        c = conn.cursor()
        c.execute(sql, (roll_no, name, face_encoding))
        conn.commit()
        return True
    except sqlite3.Error:
        # integrity error chk
        return False
    finally:
        if conn:
            conn.close()


def update_face_data_for_student(roll_no, face_encoding):
    #updt std face data
    conn = get_connection_to_database()
    sql = ''' UPDATE students \
              SET face_encoding = ? \
              WHERE roll_no = ? '''
    try:
        c = conn.cursor()
        c.execute(sql, (face_encoding, roll_no))
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Error updating student face data: {e}")
        return False
    finally:
        if conn:
            conn.close()


def delete_student_from_db(roll_no):
    conn = get_connection_to_database()
    sql = 'DELETE FROM students WHERE roll_no=?'
    try:
        c = conn.cursor()
        c.execute(sql, (roll_no,))
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Error deleting student: {e}")
        return False
    finally:
        if conn:
            conn.close()


def load_all_registered_students_from_db():
    #load std face recog
    conn = get_connection_to_database()
    students_data = []
    try:
        c = conn.cursor()
        rows = c.execute("SELECT roll_no, name, face_encoding FROM students").fetchall()
        for row in rows:
            students_data.append({"roll_no": row[0], "name": row[1], "face_encoding": row[2]})
    except sqlite3.Error as e:
        print(f"Couldn't load students from DB: {e}")
    finally:
        if conn:
            conn.close()
    return students_data


def log_student_attendance(roll_no):
    conn = get_connection_to_database()
    now = datetime.now()
    today_date_str, current_time_str = now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S")

    try:
        c = conn.cursor()
        c.execute("SELECT * FROM attendance_records WHERE roll_no = ? AND attendance_date = ?",
                  (roll_no, today_date_str))
        if c.fetchone() is None:
            #ins new record
            sql = ''' INSERT INTO attendance_records(roll_no, attendance_date, attendance_time) \
                      VALUES (?, ?, ?) '''
            c.execute(sql, (roll_no, today_date_str, current_time_str))
            conn.commit()
            return True
        else:
            return False
    except sqlite3.Error as e:
        print(f"Error logging attendance: {e}")
    finally:
        if conn:
            conn.close()


def fetch_full_attendance_report():
    conn = get_connection_to_database()
    try:
        c = conn.cursor()
        #join with std table -name
        sql = """SELECT ar.roll_no, s.name, ar.attendance_date, ar.attendance_time
                 FROM attendance_records ar \
                          JOIN students s ON ar.roll_no = s.roll_no
                 ORDER BY ar.record_id DESC"""
        rows = c.execute(sql).fetchall()
        return rows
    except sqlite3.Error as e:
        print(f"Error fetching report: {e}")
        return []
    finally:
        if conn:
            conn.close()