import customtkinter as ctk
from tkinter import ttk, messagebox
import database_ops as db
import face_operations as face_op
import os


class AttendanceAppGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        db.setup_database_tables_if_needed()

        self.title("Face Recognition Attendance System")
        self.geometry("750x550")
        self.minsize(650, 450)
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")
        self.make_window_appear_in_center()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        main_container = ctk.CTkFrame(self, corner_radius=10)
        main_container.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        main_container.grid_columnconfigure(0, weight=1)

        title_label = ctk.CTkLabel(main_container, text="Main Menu", font=ctk.CTkFont(size=26, weight="bold"))
        title_label.pack(pady=30)

        btn_pady = 12;
        btn_padx = 80;
        btn_height = 45

        register_button = ctk.CTkButton(main_container, text="Register a New Student",
                                        command=self.new_student_button_clicked, height=btn_height)
        register_button.pack(pady=btn_pady, padx=btn_padx, fill="x")
        attendance_button = ctk.CTkButton(main_container, text="Start Taking Attendance",
                                          command=self.take_attendance_button_clicked, height=btn_height)
        attendance_button.pack(pady=btn_pady, padx=btn_padx, fill="x")
        manage_button = ctk.CTkButton(main_container, text="Manage Students",
                                      command=self.manage_students_button_clicked, height=btn_height)
        manage_button.pack(pady=btn_pady, padx=btn_padx, fill="x")
        report_button = ctk.CTkButton(main_container, text="View Attendance Report",
                                      command=self.view_report_button_clicked, height=btn_height)
        report_button.pack(pady=btn_pady, padx=btn_padx, fill="x")

        db_file_path = os.path.abspath("attendance.db")
        path_label = ctk.CTkLabel(self, text=f"DB Path: {db_file_path}", font=ctk.CTkFont(size=10), text_color="grey")
        path_label.place(relx=0.01, rely=0.98, anchor="sw")

    def make_window_appear_in_center(self, pop_up_window=None):
        #center window function
        target_window = pop_up_window if pop_up_window is not None else self
        target_window.update_idletasks()

        width = target_window.winfo_width()
        height = target_window.winfo_height()

        if pop_up_window is None:
            x = (target_window.winfo_screenwidth() // 2) - (width // 2)
            y = (target_window.winfo_screenheight() // 2) - (height // 2)
        else:
            x = self.winfo_x() + (self.winfo_width() // 2) - (width // 2)
            y = self.winfo_y() + (self.winfo_height() // 2) - (height // 2)

        target_window.geometry(f'{width}x{height}+{x}+{y}')

    def new_student_button_clicked(self, retrain_data=None):
        #register/retrain button action
        is_retraining = retrain_data is not None

        popup = ctk.CTkToplevel(self)
        popup.transient(self);
        popup.grab_set()
        popup.title("Retrain Student" if is_retraining else "Register New Student")
        popup.geometry("400x300")

        roll_entry = ctk.CTkEntry(popup, placeholder_text="Enter Roll Number")
        name_entry = ctk.CTkEntry(popup, placeholder_text="Enter Full Name")
        if is_retraining:
            roll_no, name = retrain_data
            roll_entry.insert(0, str(roll_no))
            roll_entry.configure(state="disabled")
            name_entry.insert(0, name)
            name_entry.configure(state="disabled")

        ctk.CTkLabel(popup, text="Student Roll Number:").pack(pady=(20, 5))
        roll_entry.pack(pady=5, padx=20, fill="x")
        ctk.CTkLabel(popup, text="Student Full Name:").pack(pady=(10, 5));
        name_entry.pack(pady=5, padx=20, fill="x")

        button_text = "Start Retraining Capture" if is_retraining else "Start Face Capture"
        ctk.CTkButton(popup, text=button_text,
                      command=lambda: self.start_the_capture_process(popup, roll_entry, name_entry,
                                                                     is_retraining)).pack(pady=20, padx=20, fill="x")

        self.make_window_appear_in_center(popup)

    def start_the_capture_process(self, popup_window, roll_entry, name_entry, is_retraining=False):
        #form submission
        roll_no_text, name_text = roll_entry.get(), name_entry.get()

        if not roll_no_text or not name_text:
            messagebox.showerror("Input Error", "Please fill out all fields.", parent=popup_window)
            return
        try:
            roll_no_int = int(roll_no_text)
        except ValueError:
            messagebox.showerror("Input Error", "Roll Number must be a number.", parent=popup_window)
            return

        popup_window.destroy()
        captured_frames = face_op.open_camera_and_capture_images(name_text)

        if captured_frames: self.show_the_processing_progress_bar(roll_no_int, name_text, captured_frames,
                                                                  is_retraining)

    def show_the_processing_progress_bar(self, roll_no, name, frames, is_retraining=False):
        #proces popup
        progress_popup = ctk.CTkToplevel(self)
        progress_popup.title("Working...");
        progress_popup.geometry("400x150")
        progress_popup.transient(self);
        progress_popup.grab_set()
        progress_popup.protocol("WM_DELETE_WINDOW", lambda: None)  # disable closing
        self.make_window_appear_in_center(progress_popup)

        ctk.CTkLabel(progress_popup, text="Processing images, this might take a moment...").pack(pady=20)
        progress_bar = ctk.CTkProgressBar(progress_popup, width=300)
        progress_bar.set(0);
        progress_bar.pack(pady=10)
        self.update()

        face_op.process_captured_images_and_save(roll_no, name, frames, progress_bar, self, is_retraining)
        progress_popup.destroy()

    def manage_students_button_clicked(self):
        manage_popup = ctk.CTkToplevel(self)
        manage_popup.title("Student Management")
        manage_popup.geometry("800x600");
        manage_popup.minsize(600, 400)
        self.make_window_appear_in_center(manage_popup)
        manage_popup.transient(self);
        manage_popup.grab_set()

        manage_popup.grid_columnconfigure(0, weight=1);
        manage_popup.grid_rowconfigure(0, weight=1)
        frame = ctk.CTkFrame(manage_popup)
        frame.grid(padx=10, pady=10, sticky="nsew")
        frame.grid_columnconfigure((0, 1), weight=1);
        frame.grid_rowconfigure(0, weight=1)

        student_table = self.setup_the_table_style_and_columns(frame)
        student_table.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")

        def refresh_student_list():
            for item in student_table.get_children(): student_table.delete(item)
            for student in db.load_all_registered_students_from_db(): student_table.insert("", "end",
                                                                                           values=(student["roll_no"],
                                                                                                   student["name"]))

        refresh_student_list()

        def delete_selected_student():
            if not student_table.focus():
                messagebox.showerror("Selection Error", "You need to select a student first.", parent=manage_popup);
                return

            roll_no, name = student_table.item(student_table.focus())['values']
            if messagebox.askyesno("Confirm", f"Are you sure you want to delete {name} (Roll No: {roll_no})?",
                                   parent=manage_popup):
                if db.delete_student_from_db(roll_no):
                    refresh_student_list()
                else:
                    messagebox.showerror("Database Error", "Could not delete the student.", parent=manage_popup)

        def retrain_selected_student():
            if not student_table.focus():
                messagebox.showerror("Selection Error", "You need to select a student first.", parent=manage_popup);
                return
            roll_no, name = student_table.item(student_table.focus())['values']
            # open reg window in retrain mode
            self.new_student_button_clicked(retrain_data=(roll_no, name))

        delete_button = ctk.CTkButton(frame, text="Delete Selected Student", command=delete_selected_student,
                                      fg_color="#E53935", hover_color="#C62828")
        delete_button.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        retrain_button = ctk.CTkButton(frame, text="Retrain Selected Student", command=retrain_selected_student)
        retrain_button.grid(row=1, column=1, padx=10, pady=10, sticky="ew")

    def take_attendance_button_clicked(self):
        self.withdraw()
        face_op.start_attendance_recognition_process()
        self.deiconify()

    def setup_the_table_style_and_columns(self, parent_container):
        #table styke
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", background="#242424", foreground="white", rowheight=28, fieldbackground="#343638",
                        font=('Calibri', 11))
        style.map('Treeview', background=[('selected', '#0078D7')])
        style.configure("Treeview.Heading", background="#333333", foreground="white", font=('Calibri', 13, 'bold'))
        style.map("Treeview.Heading", background=[('active', '#555555')])

        table = ttk.Treeview(parent_container, columns=("Roll No", "Name"), show='headings')
        table.heading("Roll No", text="Roll No");
        table.heading("Name", text="Name")
        table.column("Roll No", width=150, anchor="center");
        table.column("Name", width=400)
        return table

    def view_report_button_clicked(self):
        report_popup = ctk.CTkToplevel(self)
        report_popup.title("Attendance Report")
        report_popup.geometry("900x700");
        report_popup.minsize(700, 500)
        self.make_window_appear_in_center(report_popup)
        report_popup.transient(self);
        report_popup.grab_set()
        report_popup.grid_columnconfigure(0, weight=1);
        report_popup.grid_rowconfigure(0, weight=1)

        report_table = self.setup_the_table_style_and_columns(report_popup)
        report_table['columns'] = ("Roll No", "Name", "Date", "Time")
        report_table.heading("Date", text="Date");
        report_table.heading("Time", text="Time")
        report_table.column("Date", anchor="center");
        report_table.column("Time", anchor="center")
        report_table.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")

        for record in db.fetch_full_attendance_report():
            report_table.insert("", "end", values=record)

if __name__ == "__main__":
    app = AttendanceAppGUI()
    app.mainloop()