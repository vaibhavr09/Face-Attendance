import cv2
import face_recognition
import numpy as np
import database_ops as db
from tkinter import messagebox
import threading, time, warnings


def _legacy_draw_text(frame, text, position, font, scale, color, thickness):
    warnings.warn(
        "'_legacy_draw_text' is deprecated. Use direct cv2 calls.",
        DeprecationWarning
    )
    cv2.putText(frame, text, position, font, scale, color, thickness)


def open_camera_and_capture_images(name):
    # registration - capture images
    video_capture = cv2.VideoCapture(0)
    if not video_capture.isOpened():
        messagebox.showerror("Camera Error", "Could not open your camera.")
        return []

    captured_frames_list = []
    total_captures_needed = 100

    while len(captured_frames_list) < total_captures_needed:
        ret, frame = video_capture.read()
        if not ret:
            print("Couldn't get a frame from the camera.");
            break

        progress_text = f"Images captured: {len(captured_frames_list)}/{total_captures_needed}"
        cv2.putText(frame, progress_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        face_locations = face_recognition.face_locations(frame)

        if len(face_locations) == 1:
            top, right, bottom, left = face_locations[0]
            pad = 10
            cv2.rectangle(frame, (left - pad, top - pad), (right + pad, bottom + pad), (255, 0, 0), 2)
            _legacy_draw_text(frame, name, (left - pad, top - pad - 10), cv2.FONT_HERSHEY_DUPLEX, 0.8, (255, 255, 255),
                              1)

            captured_frames_list.append(frame)
        elif len(face_locations) > 1:
            cv2.putText(frame, "Multiple faces detected!", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        else:
            cv2.putText(frame, "No face detected.", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        cv2.imshow('Registration - Look at Camera & Press Q to Quit', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            captured_frames_list = [];
            break  # user cancelled

    video_capture.release()
    cv2.destroyAllWindows()
    return captured_frames_list


def process_captured_images_and_save(roll_no, name, frames, progress_bar_widget, main_app_window,
                                     is_retraining_flow=False):
    # registration -process images
    encodings_from_all_images = []

    for i, frame in enumerate(frames):
        face_locations = face_recognition.face_locations(frame)
        if face_locations:
            # get face encoding
            face_encoding = face_recognition.face_encodings(frame, face_locations)[0]
            encodings_from_all_images.append(face_encoding)

        progress_bar_widget.set((i + 1) / len(frames))
        main_app_window.update_idletasks()

    if not encodings_from_all_images:
        messagebox.showerror("Processing Error",
                             "Could not find a face in any of the captured images. Please try again.")
        return

    # average all encodings
    average_encoding = np.mean(encodings_from_all_images, axis=0)

    if is_retraining_flow:
        db.update_face_data_for_student(roll_no, average_encoding)
        messagebox.showinfo("Success", f"{name} was retrained successfully.")
    else:
        if not db.save_new_student_to_db(roll_no, name, average_encoding):
            messagebox.showerror("Database Error", f"Roll number {roll_no} already exists.")
        else:
            messagebox.showinfo("Success", f"{name} was registered successfully.")


# global vars for threading
latest_frame_from_cam, all_face_locations_in_frame, all_face_names_in_frame, should_stop_thread = None, [], [], False


def background_thread_for_face_rec(all_known_encodings, all_known_student_info):
    # background worker for recognition, smoothness controller DO NOT CHAHNGE ANY SHIT HERE
    global latest_frame_from_cam, all_face_locations_in_frame, all_face_names_in_frame, should_stop_thread
    students_marked_today = []

    while not should_stop_thread:
        if latest_frame_from_cam is None:
            time.sleep(0.1);
            continue

        frame_to_process = latest_frame_from_cam
        # cmprs image for faster processing
        small_frame = cv2.resize(frame_to_process, (0, 0), fx=0.25, fy=0.25)
        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

        face_locations = face_recognition.face_locations(rgb_small_frame)
        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

        names_found = []
        # loop found faces
        for encoding in face_encodings:
            matches = face_recognition.compare_faces(all_known_encodings, encoding, tolerance=0.6)
            name, roll_no = "Unknown", None

            face_distances = face_recognition.face_distance(all_known_encodings, encoding)
            if len(face_distances) > 0:
                best_match_index = np.argmin(face_distances)
                if matches[best_match_index]:
                    roll_no = all_known_student_info[best_match_index]["roll_no"]
                    name = all_known_student_info[best_match_index]["name"]

                    if roll_no not in students_marked_today:
                        if db.log_student_attendance(roll_no): students_marked_today.append(roll_no)

            names_found.append(f"{name} - {roll_no}" if roll_no is not None else "Unknown")

        # update glbl results
        all_face_locations_in_frame, all_face_names_in_frame = face_locations, names_found


def start_attendance_recognition_process():
    global latest_frame_from_cam, all_face_locations_in_frame, all_face_names_in_frame, should_stop_thread
    # reset glbl vars
    should_stop_thread, all_face_locations_in_frame, all_face_names_in_frame = False, [], []

    known_students = db.load_all_registered_students_from_db()
    if not known_students:
        messagebox.showwarning("No students", "There are no students registered in the system.")
        return

    known_encodings = [s["face_encoding"] for s in known_students]
    known_info = [{"roll_no": s["roll_no"], "name": s["name"]} for s in known_students]

    rec_thread = threading.Thread(target=background_thread_for_face_rec, args=(known_encodings, known_info),
                                  daemon=True)
    rec_thread.start()

    #main thread - camera display
    video_capture = cv2.VideoCapture(0)
    if not video_capture.isOpened():
        messagebox.showerror("Camera Error", "Could not open camera.");
        should_stop_thread = True;
        return

    while not should_stop_thread:
        ret, frame = video_capture.read()
        if not ret: break
        latest_frame_from_cam = frame

        #background thread
        if all_face_locations_in_frame:
            for (top, right, bottom, left), name in zip(all_face_locations_in_frame, all_face_names_in_frame):
                top *= 4;
                right *= 4;
                bottom *= 4;
                left *= 4
                pad = 10
                box_color = (0, 0, 255) if "Unknown" in name else (0, 255, 0)
                cv2.rectangle(frame, (left - pad, top - pad), (right + pad, bottom + pad), box_color, 2)
                _legacy_draw_text(frame, name, (left - pad, top - pad - 10), cv2.FONT_HERSHEY_DUPLEX, 0.8,
                                  (255, 255, 255), 1)

        cv2.imshow('Attendance - Press Q to Exit', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'): break

    should_stop_thread = True
    if rec_thread.is_alive(): rec_thread.join()
    video_capture.release()
    cv2.destroyAllWindows()
