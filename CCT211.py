#!/usr/bin/env python3
"""
Condo Amenity & Service Hub - improved implementation with role-based UI
Matches the proposal: login -> dashboard -> (amenities, packages, service requests, announcements)
Uses SQLite for persistence.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from datetime import datetime
from datetime import date, time as dtime
import re


# ------------------------- Domain Models ------------------------- #

class User:
    def __init__(self, username: str, role: str = "resident", unit: str = ""):
        self.username = username
        self.role = role  # "resident" or "admin"
        self.unit = unit

    def is_admin(self) -> bool:
        return self.role == "admin"


class AmenityBooking:
    """
    Rules：
    1. Appointment Date:
       - Must be in “YYYY-MM-DD” format, e.g. “2025-09-02”
       - Must be a valid date
       - Must be on or after 2025-09-02

    2. Time:
       - 24-hour format, must be “HH:MM”
       - Hours 00–23, minutes 00–59
       - start_time must precede end_time (comparison within the same day)
    """

    _MIN_BOOKING_DATE = date(2025, 9, 2)  # Earliest booking date

    def __init__(
        self,
        booking_id: int,
        unit: str,
        facility_type: str,
        date_str: str,      # 'YYYY-MM-DD'
        start_time: str,    # 'HH:MM'
        end_time: str,      # 'HH:MM'
        status: str = "Booked",
        created_by: str = "",
    ):
        self.id = booking_id
        self.unit = unit
        self.facility_type = facility_type

        # Validate date and times
        self.date = self._validate_and_normalize_date(date_str)
        self.start_time = self._validate_time(start_time, field_name="start_time")
        self.end_time = self._validate_time(end_time, field_name="end_time")

        # Ensure the start time is earlier than the end time.
        st_h, st_m = map(int, self.start_time.split(":"))
        et_h, et_m = map(int, self.end_time.split(":"))
        if dtime(st_h, st_m) >= dtime(et_h, et_m):
            raise ValueError("start_time must be earlier than end_time")

        self.status = status
        self.created_by = created_by

    @classmethod
    def _validate_and_normalize_date(cls, date_str: str) -> str:
        """
        Accept user input in “YYYY-MM-DD” format:
        - Must conform to the regular expression format
        - Must be a valid date
        - Must be >= 02 September 2025
        Return a standard “YYYY-MM-DD” string (i.e. isoformat)
        """
        # Must be YYYY-MM-DD
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_str):
            raise ValueError("Date must be in 'YYYY-MM-DD' format, e.g., '2025-11-22'")

        year_str, month_str, day_str = date_str.split("-")
        year = int(year_str)
        month = int(month_str)
        day = int(day_str)

        try:
            candidate = date(year, month, day)
        except ValueError:
            raise ValueError("Invalid date value")

        # Must be on or after 2025-09-02
        if candidate < cls._MIN_BOOKING_DATE:
            raise ValueError("Booking date must be on or after 2025-09-02")

        return candidate.isoformat()  # 'YYYY-MM-DD'

    @staticmethod
    def _validate_time(time_str: str, field_name: str = "time") -> str:
        """
        Time must be in “HH:MM” format (24-hour clock)
        - Valid: “00:00”, “09:05”, “12:30”, “23:59”
        - Invalid: “9:00”, “12:0”, “24:00”, 'aa:bb'
        """
        if not re.fullmatch(r"\d{2}:\d{2}", time_str):
            raise ValueError(f"{field_name} must be in 'HH:MM' format, e.g., '12:30'")

        hh_str, mm_str = time_str.split(":")
        hour = int(hh_str)
        minute = int(mm_str)

        if not (0 <= hour <= 23):
            raise ValueError(f"{field_name} hour must be between 00 and 23")

        if not (0 <= minute <= 59):
            raise ValueError(f"{field_name} minutes must be between 00 and 59")

        _ = dtime(hour, minute)  # just to verify it's constructible

        return time_str

    def to_dict(self) -> dict:
        """
        Export date as 'YYYY-MM-DD'.
        """
        return {
            "id": self.id,
            "unit": self.unit,
            "facility_type": self.facility_type,
            "date": self.date,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "status": self.status,
            "created_by": self.created_by,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AmenityBooking":
        return cls(
            booking_id=data.get("id", 0),
            unit=data.get("unit", ""),
            facility_type=data.get("facility_type", ""),
            date_str=data.get("date", ""),
            start_time=data.get("start_time", ""),
            end_time=data.get("end_time", ""),
            status=data.get("status", "Booked"),
            created_by=data.get("created_by", ""),
        )


class PackageRecord:
    def __init__(self, package_id: int, unit: str, carrier: str,
                 arrival_date: str, picked_up: bool = False):
        self.id = package_id
        self.unit = unit
        self.carrier = carrier
        self.arrival_date = arrival_date  # "YYYY-MM-DD"
        self.picked_up = picked_up

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "unit": self.unit,
            "carrier": self.carrier,
            "arrival_date": self.arrival_date,
            "picked_up": self.picked_up,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PackageRecord":
        return cls(
            package_id=data.get("id", 0),
            unit=data.get("unit", ""),
            carrier=data.get("carrier", ""),
            arrival_date=data.get("arrival_date", ""),
            picked_up=data.get("picked_up", False),
        )


class ServiceRequest:
    def __init__(self, req_id: int, unit: str, req_type: str,
                 description: str, status: str = "Submitted",
                 created_by: str = ""):
        self.id = req_id
        self.unit = unit
        self.req_type = req_type
        self.description = description
        self.status = status
        # Which user submitted this request (for filtering / permissions)
        self.created_by = created_by

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "unit": self.unit,
            "req_type": self.req_type,
            "description": self.description,
            "status": self.status,
            "created_by": self.created_by,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ServiceRequest":
        return cls(
            req_id=data.get("id", 0),
            unit=data.get("unit", ""),
            req_type=data.get("req_type", ""),
            description=data.get("description", ""),
            status=data.get("status", "Submitted"),
            created_by=data.get("created_by", ""),
        )


class Announcement:
    def __init__(self, ann_id: int, title: str, content: str,
                 created_at: str = None):
        self.id = ann_id
        self.title = title
        self.content = content
        self.created_at = created_at or datetime.now().strftime("%Y-%m-%d %H:%M")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Announcement":
        return cls(
            ann_id=data.get("id", 0),
            title=data.get("title", ""),
            content=data.get("content", ""),
            created_at=data.get("created_at"),
        )


# ------------------------- Persistence Layer (SQLite) ------------------------- #

class DataStore:
    """SQLite-based persistence for all entities."""

    def __init__(self, filename: str = "condo_data.sqlite3"):
        # Link to the database, if don't have one, it will automatically create one.
        self.conn = sqlite3.connect(filename)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        """Create tables if not exist."""
        cur = self.conn.cursor()

        # Amenity bookings
        cur.execute("""
            CREATE TABLE IF NOT EXISTS amenity_bookings (
                id            INTEGER PRIMARY KEY,
                unit          TEXT NOT NULL,
                facility_type TEXT NOT NULL,
                date          TEXT NOT NULL,
                start_time    TEXT NOT NULL,
                end_time      TEXT NOT NULL,
                status        TEXT NOT NULL,
                created_by    TEXT
            )
        """)

        # Packages
        cur.execute("""
            CREATE TABLE IF NOT EXISTS packages (
                id           INTEGER PRIMARY KEY,
                unit         TEXT NOT NULL,
                carrier      TEXT NOT NULL,
                arrival_date TEXT NOT NULL,
                picked_up    INTEGER NOT NULL DEFAULT 0
            )
        """)

        # Service requests
        cur.execute("""
            CREATE TABLE IF NOT EXISTS service_requests (
                id          INTEGER PRIMARY KEY,
                unit        TEXT NOT NULL,
                req_type    TEXT NOT NULL,
                description TEXT NOT NULL,
                status      TEXT NOT NULL,
                created_by  TEXT
            )
        """)

        # Announcements
        cur.execute("""
            CREATE TABLE IF NOT EXISTS announcements (
                id         INTEGER PRIMARY KEY,
                title      TEXT NOT NULL,
                content    TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        self.conn.commit()

    def save(self) -> None:
        """Commit pending changes to disk."""
        self.conn.commit()

    def __del__(self):
        try:
            self.conn.close()
        except Exception:
            pass

    # ------------- ID helper ------------- #

    def next_id(self, key: str) -> int:
        """Return next integer id for a given logical table key."""
        table = {
            "amenity_bookings": "amenity_bookings",
            "packages": "packages",
            "service_requests": "service_requests",
            "announcements": "announcements",
        }.get(key)

        if table is None:
            raise ValueError(f"Unknown key for next_id: {key}")

        cur = self.conn.execute(f"SELECT MAX(id) AS max_id FROM {table}")
        row = cur.fetchone()
        max_id = row["max_id"] if row and row["max_id"] is not None else 0
        return max_id + 1

    # ------------- Amenity bookings ------------- #

    def get_amenity_bookings(self):
        cur = self.conn.execute(
            """
            SELECT id, unit, facility_type, date, start_time, end_time, status, created_by
            FROM amenity_bookings
            ORDER BY date, start_time, id
            """
        )
        rows = cur.fetchall()
        return [AmenityBooking.from_dict(dict(row)) for row in rows]

    def set_amenity_bookings(self, bookings):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM amenity_bookings")
        cur.executemany(
            """
            INSERT INTO amenity_bookings
            (id, unit, facility_type, date, start_time, end_time, status, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    b.id,
                    b.unit,
                    b.facility_type,
                    b.date,
                    b.start_time,
                    b.end_time,
                    b.status,
                    b.created_by,
                )
                for b in bookings
            ],
        )

    # ------------- Packages ------------- #

    def get_packages(self):
        cur = self.conn.execute(
            """
            SELECT id, unit, carrier, arrival_date, picked_up
            FROM packages
            ORDER BY arrival_date DESC, id DESC
            """
        )
        rows = cur.fetchall()
        result = []
        for row in rows:
            result.append(
                PackageRecord.from_dict(
                    {
                        "id": row["id"],
                        "unit": row["unit"],
                        "carrier": row["carrier"],
                        "arrival_date": row["arrival_date"],
                        "picked_up": bool(row["picked_up"]),
                    }
                )
            )
        return result

    def set_packages(self, packages):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM packages")
        cur.executemany(
            """
            INSERT INTO packages
            (id, unit, carrier, arrival_date, picked_up)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (
                    p.id,
                    p.unit,
                    p.carrier,
                    p.arrival_date,
                    int(p.picked_up),
                )
                for p in packages
            ],
        )

    # ------------- Service requests ------------- #

    def get_service_requests(self):
        cur = self.conn.execute(
            """
            SELECT id, unit, req_type, description, status, created_by
            FROM service_requests
            ORDER BY id DESC
            """
        )
        rows = cur.fetchall()
        return [ServiceRequest.from_dict(dict(row)) for row in rows]

    def set_service_requests(self, requests):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM service_requests")
        cur.executemany(
            """
            INSERT INTO service_requests
            (id, unit, req_type, description, status, created_by)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    r.id,
                    r.unit,
                    r.req_type,
                    r.description,
                    r.status,
                    r.created_by,
                )
                for r in requests
            ],
        )

    # ------------- Announcements ------------- #

    def get_announcements(self):
        cur = self.conn.execute(
            """
            SELECT id, title, content, created_at
            FROM announcements
            ORDER BY id
            """
        )
        rows = cur.fetchall()
        return [Announcement.from_dict(dict(row)) for row in rows]

    def set_announcements(self, announcements):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM announcements")
        cur.executemany(
            """
            INSERT INTO announcements
            (id, title, content, created_at)
            VALUES (?, ?, ?, ?)
            """,
            [
                (
                    a.id,
                    a.title,
                    a.content,
                    a.created_at,
                )
                for a in announcements
            ],
        )


# ------------------------- Utility Functions ------------------------- #

def parse_time_to_minutes(time_str: str) -> int:
    """Convert 'HH:MM' into minutes since midnight."""
    try:
        h, m = time_str.split(":")
        return int(h) * 60 + int(m)
    except ValueError:
        return -1


# ------------------------- GUI: Login & Dashboard ------------------------- #

class LoginFrame(tk.Frame):
    def __init__(self, master, app, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.app = app
        self.configure(padx=30, pady=30)

        # Title
        title_frame = tk.Frame(self)
        title_frame.place(relx=0.5, rely=0.25, anchor="center")
        tk.Label(
            title_frame,
            text="Condo Amenity & Service Hub",
            font=("Arial", 22, "bold")
        ).pack(pady=(0, 15))

        # Login form
        content = tk.Frame(self)
        content.place(relx=0.5, rely=0.55, anchor="center")

        form = tk.Frame(content)
        form.pack()

        # Username
        tk.Label(form, text="Username:").grid(row=0, column=0, sticky="w", pady=5, padx=5)
        self.username_entry = tk.Entry(form, width=25)
        self.username_entry.grid(row=0, column=1, pady=5, padx=5)

        # Unit
        tk.Label(form, text="Unit:").grid(row=1, column=0, sticky="w", pady=5, padx=5)
        self.unit_entry = tk.Entry(form, width=25)
        self.unit_entry.grid(row=1, column=1, pady=5, padx=5)

        # Role
        tk.Label(form, text="Role:").grid(row=2, column=0, sticky="w", pady=5, padx=5)
        role_frame = tk.Frame(form)
        role_frame.grid(row=2, column=1, pady=5, padx=5)

        self.role_var = tk.StringVar(value="resident")
        tk.Radiobutton(role_frame, text="Resident", variable=self.role_var, value="resident").pack(side="left", padx=10)
        tk.Radiobutton(role_frame, text="Admin", variable=self.role_var, value="admin").pack(side="left", padx=10)

        tk.Button(content, text="Login", width=18, command=self.do_login).pack(pady=20)

    def do_login(self):
        username = self.username_entry.get().strip()
        unit = self.unit_entry.get().strip()
        if not username:
            messagebox.showerror("Error", "Please enter a username.")
            return
        if not unit and self.role_var.get() == "resident":
            messagebox.showerror("Error", "Please enter your unit.")
            return
        role = self.role_var.get()
        user = User(username=username, role=role, unit=unit)
        self.app.show_dashboard(user)


class DashboardFrame(tk.Frame):
    def __init__(self, master, app, user: User, store: DataStore, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.app = app
        self.user = user
        self.store = store
        self.configure(bg="#f2f2f2")

        # ----- Modern flat button styles ----- #
        style = ttk.Style(self)
        style.theme_use("clam")

        # Logout button style (matches "Open" buttons)
        style = ttk.Style()
        style.configure(
            "SidebarLogout.TButton",
            padding=(18, 6),
            relief="solid",
            borderwidth=1,
            focusthickness=0,
            font=("Arial", 11, "bold"),
            background="white",
            foreground="black",
        )
        style.map(
            "SidebarLogout.TButton",
            background=[("active", "#f2f2f2"), ("pressed", "#e5e5e5")]
        )

        # Dashboard tile "Open" buttons
        style.configure(
            "Dashboard.TButton",
            padding=(18, 6),
            relief="solid",
            borderwidth=1,
            focusthickness=0,
            font=("Arial", 11),
            background="white",
        )
        style.map(
            "Dashboard.TButton",
            background=[("active", "#f2f2f2"), ("pressed", "#e5e5e5")]
        )

        # Announcement "View all" / "Manage" buttons
        style.configure(
            "Banner.TButton",
            padding=(12, 4),
            relief="solid",
            borderwidth=1,
            focusthickness=0,
            font=("Arial", 10),
            background="#dbeff0",
        )
        style.map(
            "Banner.TButton",
            background=[("active", "#cfe4e4"), ("pressed", "#bcd9d9")]
        )

        # ---------------- Top bar ---------------- #
        top_bar = tk.Frame(self, bg="#0f3b3a", height=55)
        top_bar.pack(fill="x")
        top_bar.pack_propagate(False)

        # Hamburger menu
        menu_lbl = tk.Label(top_bar, text="≡", fg="white", bg="#0f3b3a", font=("Arial", 18), cursor="hand2")
        menu_lbl.pack(side="left", padx=10)
        menu_lbl.bind("<Button-1>", lambda e: self.toggle_menu())

        # Role label
        role_text = "Admin Console" if self.user.is_admin() else "Resident Portal"
        tk.Label(
            top_bar,
            text=role_text,
            fg="white",
            bg="#0f3b3a",
            font=("Arial", 16, "bold"),
        ).pack(side="left", padx=10)

        # Welcome bits
        welcome_bits = f"{self.user.username}"
        if self.user.unit:
            welcome_bits += f" • Unit {self.user.unit}"
        tk.Label(
            top_bar,
            text=welcome_bits,
            fg="white",
            bg="#0f3b3a",
            font=("Arial", 14),
        ).pack(side="right", padx=10)

        # --------------- Announcement card --------------- #
        announce_frame = tk.Frame(self, bg="#d9eceb")
        announce_frame.pack(fill="x", padx=20, pady=(15, 10))

        tk.Label(
            announce_frame,
            text="Today's Condo Announcement",
            bg="#d9eceb",
            font=("Arial", 12, "bold"),
        ).pack(anchor="w", padx=10, pady=(8, 0))

        self.announce_label = tk.Label(
            announce_frame,
            text="No announcements yet.",
            bg="#d9eceb",
            font=("Arial", 11),
            justify="left",
            wraplength=600,
        )
        self.announce_label.pack(anchor="w", padx=10, pady=(4, 10))

        btn_frame = tk.Frame(announce_frame, bg="#d9eceb")
        btn_frame.pack(fill="x", padx=10, pady=(0, 8))

        # "View all" button (banner style)
        ttk.Button(
            btn_frame,
            text="View all",
            command=self.open_announcements,
            style="Banner.TButton",
        ).pack(side="right", padx=20)

        # Admin-only "Manage" button
        if self.user.is_admin():
            ttk.Button(
                btn_frame,
                text="Manage",
                command=self.open_announcements,
                style="Banner.TButton",
            ).pack(side="right", padx=(0, 5))

        # Ensure at least one "today's update" style announcement for residents
        self.ensure_default_announcement()
        self.refresh_announcement_text()

        # ---------------- Tiles container ---------------- #
        tiles_frame = tk.Frame(self, bg="#f2f2f2")
        tiles_frame.pack(fill="both", expand=True, padx=20, pady=10)

        amenity_tile = tk.Frame(tiles_frame, bg="white", bd=1, relief="raised")
        pkg_tile = tk.Frame(tiles_frame, bg="white", bd=1, relief="raised")
        srv_tile = tk.Frame(tiles_frame, bg="white", bd=1, relief="raised")

        amenity_tile.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        pkg_tile.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        srv_tile.grid(row=0, column=2, padx=10, pady=10, sticky="nsew")

        tiles_frame.columnconfigure(0, weight=1)
        tiles_frame.columnconfigure(1, weight=1)
        tiles_frame.columnconfigure(2, weight=1)
        tiles_frame.rowconfigure(0, weight=1)

        # ---------------- Amenity tile ---------------- #
        tk.Label(amenity_tile, text="🏊", font=("Arial", 32), bg="white").pack(
            pady=(15, 5)
        )
        tk.Label(
            amenity_tile,
            text="Book Amenities",
            font=("Arial", 12, "bold"),
            bg="white",
        ).pack()
        tk.Label(
            amenity_tile,
            text="Reserve meeting room, pool lanes, party room.",
            font=("Arial", 9),
            bg="white",
            fg="#555555",
            wraplength=200,
        ).pack(pady=(2, 4))
        ttk.Button(
            amenity_tile,
            text="Open",
            command=self.open_amenities,
            style="Dashboard.TButton",
        ).pack(pady=10)

        # ---------------- Package tile ---------------- #
        tk.Label(pkg_tile, text="📦", font=("Arial", 32), bg="white").pack(
            pady=(15, 5)
        )
        tk.Label(
            pkg_tile,
            text="Packages",
            font=("Arial", 12, "bold"),
            bg="white",
        ).pack()
        tk.Label(
            pkg_tile,
            text="Track deliveries and pickup status.",
            font=("Arial", 9),
            bg="white",
            fg="#555555",
            wraplength=200,
        ).pack(pady=(2, 4))
        ttk.Button(
            pkg_tile,
            text="Open",
            command=self.open_packages,
            style="Dashboard.TButton",
        ).pack(pady=10)

        # ------------- Service Requests tile ------------- #
        tk.Label(srv_tile, text="🛠", font=("Arial", 32), bg="white").pack(
            pady=(15, 5)
        )
        tk.Label(
            srv_tile,
            text="Service Requests",
            font=("Arial", 12, "bold"),
            bg="white",
        ).pack()
        tk.Label(
            srv_tile,
            text="Submit repair and concierge requests.",
            font=("Arial", 9),
            bg="white",
            fg="#555555",
            wraplength=200,
        ).pack(pady=(2, 4))
        ttk.Button(
            srv_tile,
            text="Open",
            command=self.open_service_requests,
            style="Dashboard.TButton",
        ).pack(pady=10)

        # ---------- Admin summary bar (3 numbers) ---------- #
        if self.user.is_admin():
            stats_frame = tk.Frame(self, bg="#f2f2f2")
            stats_frame.pack(fill="x", padx=20, pady=(0, 15))

            # Live variables so we can refresh counts
            self.bookings_var = tk.IntVar()
            self.packages_var = tk.IntVar()
            self.requests_var = tk.IntVar()

            def make_stat(parent, title, var):
                card = tk.Frame(parent, bg="white", bd=1, relief="solid")
                card.pack(side="left", expand=True, fill="x", padx=5)
                tk.Label(
                    card,
                    text=title,
                    bg="white",
                    font=("Arial", 10, "bold"),
                ).pack(pady=(6, 0))
                tk.Label(
                    card,
                    textvariable=var,
                    bg="white",
                    font=("Arial", 14),
                ).pack(pady=(0, 6))

            # Titles可以按需要改文案，这里三个数字的含义是：
            # 1) 总预约数 2) 未取件包裹 3) 未解决请求
            make_stat(stats_frame, "Total Amenity Bookings", self.bookings_var)
            make_stat(stats_frame, "Waiting Packages", self.packages_var)
            make_stat(stats_frame, "Open Service Requests", self.requests_var)

            # Set initial values
            self.refresh_admin_summary()

    # ---------- Slide-out menu & logout ---------- #

    def toggle_menu(self):
        """Open/close the slide-out menu on the left."""
        # If menu already open → close it
        if hasattr(self, "menu_frame") and self.menu_frame.winfo_exists():
            self.menu_frame.destroy()
            return

        # Create slide-out sidebar
        self.menu_frame = tk.Frame(self, bg="#0f3b3a", width=220)
        self.menu_frame.place(x=0, y=0, relheight=1.0)

        # --- Top row: Close arrow + Title ---
        top_row = tk.Frame(self.menu_frame, bg="#0f3b3a")
        top_row.pack(fill="x", pady=(3, 3))

        close_btn = tk.Label(
            top_row,
            text="⟵",
            font=("Arial", 16),
            bg="#0f3b3a",
            fg="white",
            cursor="hand2"
        )
        close_btn.pack(side="left", padx=20, pady=8)
        close_btn.bind("<Button-1>", lambda e: self.close_menu())

        tk.Label(
            top_row,
            text="Menu",
            font=("Arial", 16, "bold"),
            bg="#0f3b3a",
            fg="white",
        ).pack(side="left", padx=10, pady=10)

        # --- Divider line ---
        tk.Frame(self.menu_frame, bg="white", height=1).pack(
            fill="x", pady=(5, 15)
        )

        # Spacer to push logout to bottom
        tk.Frame(self.menu_frame, bg="#0f3b3a").pack(expand=True, fill="both")

        # --- Logout button pinned at bottom ---
        ttk.Button(
            self.menu_frame,
            text="Log Out",
            style="SidebarLogout.TButton",
            command=self.confirm_logout
        ).pack(fill="x", padx=20, pady=25, side="bottom")

    def close_menu(self):
        """Close the slide-out menu if it exists."""
        if hasattr(self, "menu_frame") and self.menu_frame.winfo_exists():
            self.menu_frame.destroy()

    def refresh_admin_summary(self):
        """Recalculate dashboard summary numbers."""
        if not self.user.is_admin():
            return

        # 1) Amenity bookings – count all
        bookings = self.store.get_amenity_bookings()
        self.bookings_var.set(len(bookings))

        # 2) Packages – count ONLY those not yet picked up
        packages = self.store.get_packages()
        active_pkgs = sum(
            1 for p in packages
            if not getattr(p, "picked_up", False)
        )
        self.packages_var.set(active_pkgs)

        # 3) Service Requests – count ONLY those not resolved
        requests = self.store.get_service_requests()
        open_reqs = sum(
            1 for r in requests
            if getattr(r, "status", "").lower() != "resolved"
        )
        self.requests_var.set(open_reqs)

    def confirm_logout(self):
        """Logout with confirmation dialog."""
        if messagebox.askyesno("Logout", "Are you sure you want to log out?"):
            self.close_menu()
            self.app.logout()

    # ---------- Announcement helpers ---------- #

    def ensure_default_announcement(self):
        announcements = self.store.get_announcements()
        if announcements:
            return
        # First-time default content
        if self.user.is_admin():
            content = "No condo updates yet. Use 'Manage' to post an announcement for residents."
        else:
            content = "Today: partly cloudy with a light breeze. Remember to close balcony doors before you leave home."
        ann = Announcement(
            ann_id=self.store.next_id("announcements"),
            title="Today's Update",
            content=content,
        )
        announcements = [ann]
        self.store.set_announcements(announcements)
        self.store.save()

    def refresh_announcement_text(self):
        announcements = self.store.get_announcements()
        if announcements:
            latest = announcements[-1]
            text = f"{latest.title} – {latest.content}"
        else:
            text = "No announcements yet."
        self.announce_label.config(text=text)

    # ---------- Open sub-windows ---------- #

    def open_announcements(self):
        AnnouncementWindow(self, self.store, self.user,
                           on_update=self.refresh_announcement_text)

    def open_amenities(self):
        AmenityWindow(self, self.store, self.user,
                      on_changed=self.refresh_admin_summary)

    def open_packages(self):
        PackageWindow(self, self.store, self.user,
                      on_changed=self.refresh_admin_summary)

    def open_service_requests(self):
        ServiceRequestWindow(self, self.store, self.user,
                             on_changed=self.refresh_admin_summary)


# ------------------------- GUI: Amenity Booking Window ------------------------- #

class AmenityWindow(tk.Toplevel):
    FACILITIES = ["Meeting Room", "Swimming Pool Lane", "Party Room"]

    def __init__(self, master, store: DataStore, user: User, on_changed=None):
        super().__init__(master)
        self.title("Amenity Bookings")
        self.store = store
        self.user = user
        self.on_changed = on_changed
        self.bookings = self.store.get_amenity_bookings()

        self.geometry("600x420")

        # Top controls
        top = tk.Frame(self)
        top.pack(fill="x", padx=10, pady=5)

        tk.Label(top, text="Amenity Bookings", font=("Arial", 12, "bold")).pack(side="left")

        btn_frame = tk.Frame(top)
        btn_frame.pack(side="right")
        tk.Button(btn_frame, text="Add", width=10, command=self.add_booking).pack(side="left", padx=3)
        tk.Button(btn_frame, text="Edit", width=10, command=self.edit_booking).pack(side="left", padx=3)
        tk.Button(btn_frame, text="Cancel", width=10, command=self.cancel_booking).pack(side="left", padx=3)
        tk.Button(btn_frame, text="Delete", width=10, command=self.delete_booking).pack(side="left", padx=3)

        # Listbox for bookings
        self.listbox = tk.Listbox(self, height=16)
        self.listbox.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.refresh_listbox()

    def refresh_listbox(self):
        self.listbox.delete(0, tk.END)
        for b in self.bookings:
            creator = f" • by {b.created_by}" if b.created_by else ""
            text = f"#{b.id} | {b.date} {b.start_time}-{b.end_time} | {b.facility_type} | Unit {b.unit} | {b.status}{creator}"
            self.listbox.insert(tk.END, text)

    def add_booking(self):
        BookingForm(self, self.store, on_save=self.on_booking_saved, booking=None)

    def get_selected_booking(self):
        idx = self.listbox.curselection()
        if not idx:
            return None
        return self.bookings[idx[0]]

    def _can_modify(self, booking: AmenityBooking) -> bool:
        if booking is None:
            return False
        if self.user.is_admin():
            return True
        # Residents may only modify/cancel their own bookings
        return booking.created_by == self.user.username

    def edit_booking(self):
        b = self.get_selected_booking()
        if not b:
            messagebox.showwarning("Select", "Please select a booking to edit.")
            return
        if not self._can_modify(b):
            messagebox.showerror("Permission", "You can only edit bookings that you created.")
            return
        BookingForm(self, self.store, on_save=self.on_booking_saved, booking=b)

    def cancel_booking(self):
        b = self.get_selected_booking()
        if not b:
            messagebox.showwarning("Select", "Please select a booking to cancel.")
            return
        if not self._can_modify(b):
            messagebox.showerror("Permission", "You can only cancel bookings that you created.")
            return
        if b.status == "Cancelled":
            messagebox.showinfo("Info", "This booking is already cancelled.")
            return
        if messagebox.askyesno("Confirm", "Cancel this booking?"):
            b.status = "Cancelled"
            self.save_and_refresh()

    def delete_booking(self):
        b = self.get_selected_booking()
        if not b:
            messagebox.showwarning("Select", "Please select a booking to delete.")
            return

        # ----- Permission check -----
        # Admin: can delete anything
        # Resident: only delete bookings that belong to their own unit
        if not self.user.is_admin():
            if str(b.unit) != str(self.user.unit):
                messagebox.showerror(
                    "Permission",
                    "You can only delete your own bookings."
                )
                return

        # ----- Confirm deletion -----
        if messagebox.askyesno("Confirm", "Delete this booking permanently?"):
            self.bookings = [bk for bk in self.bookings if bk.id != b.id]
            self.save_and_refresh()

    def has_conflict(self, new_booking: AmenityBooking) -> bool:
        """Check overlapping time slots for same facility and date."""
        new_start = parse_time_to_minutes(new_booking.start_time)
        new_end = parse_time_to_minutes(new_booking.end_time)
        if new_start < 0 or new_end < 0:
            return False  # time parse error handled elsewhere
        for b in self.bookings:
            if b.id == new_booking.id:
                continue
            if b.facility_type == new_booking.facility_type and b.date == new_booking.date:
                start = parse_time_to_minutes(b.start_time)
                end = parse_time_to_minutes(b.end_time)
                if start < new_end and new_start < end:
                    return True
        return False

    def on_booking_saved(self, booking: AmenityBooking, is_new: bool):
        # Validate conflict
        if self.has_conflict(booking):
            messagebox.showerror("Conflict",
                                 "This facility is already booked for the given time range.")
            return False  # tell form not to close

        if is_new:
            self.bookings.append(booking)
        else:
            for i, b in enumerate(self.bookings):
                if b.id == booking.id:
                    self.bookings[i] = booking
                    break

        self.save_and_refresh()

        # Admin "notifies" resident after editing/creating bookings
        if self.user.is_admin():
            messagebox.showinfo(
                "Resident notified",
                f"Resident in Unit {booking.unit} has been notified about booking #{booking.id}."
            )
        return True

    def save_and_refresh(self):
        """Persist amenity bookings and refresh list + admin summary."""
        self.store.set_amenity_bookings(self.bookings)
        self.store.save()
        self.refresh_listbox()

        if self.on_changed:
            self.on_changed()


class BookingForm(tk.Toplevel):
    def __init__(
        self,
        master: AmenityWindow,
        store: DataStore,
        on_save,
        booking: AmenityBooking = None,
    ):
        super().__init__(master)
        self.title("Amenity Booking")
        self.store = store
        self.on_save = on_save
        self.booking = booking

        # Window size
        self.geometry("600x420")
        self.minsize(600, 420)

        # Use a form frame for nicer padding/alignment
        form = tk.Frame(self)
        form.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        form.columnconfigure(0, weight=0)   # labels
        form.columnconfigure(1, weight=1)   # inputs

        # ---------- row 0: Unit ----------
        tk.Label(form, text="Unit:").grid(row=0, column=0, sticky="e",
                                          padx=(0, 10), pady=8)
        self.unit_entry = tk.Entry(form)
        self.unit_entry.grid(row=0, column=1, sticky="ew",
                             padx=(0, 0), pady=8)

        # ---------- row 1: Facility ----------
        tk.Label(form, text="Facility:").grid(row=1, column=0, sticky="e",
                                              padx=(0, 10), pady=8)
        self.fac_var = tk.StringVar(value=AmenityWindow.FACILITIES[0])
        self.fac_menu = ttk.Combobox(
            form,
            textvariable=self.fac_var,
            values=AmenityWindow.FACILITIES,
            state="readonly",
        )
        self.fac_menu.grid(row=1, column=1, sticky="ew",
                           padx=(0, 0), pady=8)

        # ---------- row 2–3: Date ----------
        tk.Label(form, text="Date (YYYY-MM-DD):").grid(
            row=2, column=0, sticky="e", padx=(0, 10), pady=(8, 2)
        )
        self.date_entry = tk.Entry(form)
        self.date_entry.grid(row=2, column=1, sticky="ew",
                             padx=(0, 0), pady=(8, 2))

        tk.Label(
            form,
            text="Example: 2025-09-02 (YYYY-MM-DD). Bookings are only allowed on or after this date.",
            fg="#777777",
            font=("Arial", 8),
        ).grid(row=3, column=1, sticky="w", padx=(0, 0), pady=(0, 8))

        # ---------- row 4–5: Start time ----------
        tk.Label(form, text="Start time (HH:MM):").grid(
            row=4, column=0, sticky="e", padx=(0, 10), pady=(8, 2)
        )
        self.start_entry = tk.Entry(form)
        self.start_entry.grid(row=4, column=1, sticky="ew",
                              padx=(0, 0), pady=(8, 2))

        tk.Label(
            form,
            text="Example: 13:00 (24-hour clock)",
            fg="#777777",
            font=("Arial", 8),
        ).grid(row=5, column=1, sticky="w", padx=(0, 0), pady=(0, 8))

        # ---------- row 6–7: End time ----------
        tk.Label(form, text="End time (HH:MM):").grid(
            row=6, column=0, sticky="e", padx=(0, 10), pady=(8, 2)
        )
        self.end_entry = tk.Entry(form)
        self.end_entry.grid(row=6, column=1, sticky="ew",
                            padx=(0, 0), pady=(8, 2))

        tk.Label(
            form,
            text="Example: 16:30 (24-hour clock)",
            fg="#777777",
            font=("Arial", 8),
        ).grid(row=7, column=1, sticky="w", padx=(0, 0), pady=(0, 8))

        # ---------- row 8: Status ----------
        tk.Label(form, text="Status:").grid(
            row=8, column=0, sticky="e", padx=(0, 10), pady=8
        )
        self.status_var = tk.StringVar(value="Booked")
        self.status_menu = ttk.Combobox(
            form,
            textvariable=self.status_var,
            values=["Booked", "Cancelled"],
            state="readonly",
        )
        self.status_menu.grid(row=8, column=1, sticky="ew",
                              padx=(0, 0), pady=8)

        # ---------- row 9: Buttons ----------
        btn_frame = tk.Frame(form)
        btn_frame.grid(row=9, column=0, columnspan=2, pady=(20, 0))
        tk.Button(btn_frame, text="Save", width=10,
                  command=self.save).pack(side="left", padx=8)
        tk.Button(btn_frame, text="Cancel", width=10,
                  command=self.destroy).pack(side="left", padx=8)

        # ----- Prefill from booking / user -----
        user = getattr(master, "user", None)

        if self.booking:
            # Editing existing booking
            self.unit_entry.insert(0, self.booking.unit)
            self.fac_var.set(self.booking.facility_type)
            self.date_entry.insert(0, self.booking.date)
            self.start_entry.insert(0, self.booking.start_time)
            self.end_entry.insert(0, self.booking.end_time)
            self.status_var.set(self.booking.status)
        else:
            # New booking: if resident has a unit, pre-fill + lock it
            if user and not user.is_admin() and user.unit:
                self.unit_entry.insert(0, user.unit)
                self.unit_entry.config(state="disabled")

    def save(self):
        unit = self.unit_entry.get().strip()
        facility = self.fac_var.get().strip()
        date_str = self.date_entry.get().strip()
        start = self.start_entry.get().strip()
        end = self.end_entry.get().strip()
        status = self.status_var.get().strip()

        if not unit or not facility or not date_str or not start or not end:
            messagebox.showerror("Error", "All fields are required.")
            return

        # 1) Quick time sanity check for nicer error messages
        try:
            start_m = parse_time_to_minutes(start)
            end_m = parse_time_to_minutes(end)
            if start_m < 0 or end_m < 0 or end_m <= start_m:
                raise ValueError("Time range is invalid.")
        except Exception as e:
            messagebox.showerror("Invalid Time", str(e))
            return

        # 2) Create or reuse ID
        if self.booking:
            booking_id = self.booking.id
        else:
            booking_id = self.store.next_id("amenity_bookings")

        # 3) Creator
        user = getattr(self.master, "user", None)
        creator = user.username if user else ""
        if self.booking:
            creator = self.booking.created_by  # preserve original creator

        # 4) Let AmenityBooking do full validation (date + time formats + min date)
        try:
            booking = AmenityBooking(
                booking_id=booking_id,
                unit=unit,
                facility_type=facility,
                date_str=date_str,
                start_time=start,
                end_time=end,
                status=status,
                created_by=creator,
            )
        except ValueError as e:
            # Any date/time validation errors from the model show up here
            messagebox.showerror("Invalid Booking", str(e))
            return

        is_new = self.booking is None
        ok = self.on_save(booking, is_new)
        if ok:
            self.destroy()


# ------------------------- GUI: Packages Window ------------------------- #

class PackageWindow(tk.Toplevel):
    def __init__(self, master, store: DataStore, user: User, on_changed=None):
        super().__init__(master)
        self.title("Packages")
        self.store = store
        self.user = user
        self.on_changed = on_changed
        self.packages = self.store.get_packages()
        self.current_view = []
        self.geometry("1000x350")

        top = tk.Frame(self)
        top.pack(fill="x", padx=10, pady=5)

        tk.Label(top, text="Packages", font=("Arial", 12, "bold")).pack(side="left")

        self.search_var = tk.StringVar()
        tk.Label(top, text="Unit filter:").pack(side="left", padx=(30, 0))
        tk.Entry(top, textvariable=self.search_var, width=10).pack(side="left", padx=5)
        tk.Button(top, text="Apply", command=self.refresh_tree).pack(side="left", padx=5)

        btn_frame = tk.Frame(top)
        btn_frame.pack(side="right")
        if self.user.is_admin():
            tk.Button(btn_frame, text="Add", width=11, command=self.add_package).pack(side="left", padx=3)
            tk.Button(btn_frame, text="Edit", width=11, command=self.edit_package).pack(side="left", padx=3)
            tk.Button(btn_frame, text="Delete", width=11, command=self.delete_package).pack(side="left", padx=3)
        tk.Button(btn_frame, text="Mark Picked Up", width=13, command=self.mark_picked).pack(side="left", padx=3)

        # Use a Treeview here so this window looks and feels different
        self.tree = ttk.Treeview(self, columns=("unit", "carrier", "arrival", "status"), show="headings")
        self.tree.heading("unit", text="Unit")
        self.tree.heading("carrier", text="Carrier")
        self.tree.heading("arrival", text="Arrival date")
        self.tree.heading("status", text="Status")

        self.tree.column("unit", width=40, anchor="center")
        self.tree.column("carrier", width=120)
        self.tree.column("arrival", width=120, anchor="center")
        self.tree.column("status", width=220, anchor="center")

        self.tree.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.refresh_tree()

    def filtered_packages(self):
        # Resident can only see their own unit's packages
        pkgs = self.packages
        if (not self.user.is_admin()) and self.user.unit:
            pkgs = [p for p in pkgs if p.unit == self.user.unit]

        prefix = self.search_var.get().strip()
        if prefix:
            pkgs = [p for p in pkgs if p.unit.startswith(prefix)]
        return pkgs

    def refresh_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.current_view = self.filtered_packages()
        prefix = self.search_var.get().strip()   # What user typed in filter

        # If no packages for this filter
        if not self.current_view:
            if prefix:      # Only show if filter was actually used
                self.tree.insert(
                    "",
                    "end",
                    values=(
                        prefix,   # unit
                        "",       # carrier
                        "",       # arrival
                        "You currently don't receive any packages.",  # status
                    ),
                )
            return

        # Otherwise, populate normally
        for idx, p in enumerate(self.current_view):
            status = "Picked up" if p.picked_up else "Waiting"
            self.tree.insert(
                "",
                "end",
                iid=str(idx),
                values=(p.unit, p.carrier, p.arrival_date, status),
            )

    def get_selected(self):
        sel = self.tree.selection()
        if not sel:
            return None
        idx = self.tree.index(sel[0])
        if 0 <= idx < len(self.current_view):
            return self.current_view[idx]
        return None

    def add_package(self):
        if not self.user.is_admin():
            messagebox.showerror("Permission", "Only admin/staff may add package records.")
            return
        PackageForm(self, self.store, on_save=self.on_saved, record=None)

    def edit_package(self):
        if not self.user.is_admin():
            messagebox.showerror("Permission", "Only admin/staff may edit package records.")
            return
        p = self.get_selected()
        if not p:
            messagebox.showwarning("Select", "Please select a record.")
            return
        PackageForm(self, self.store, on_save=self.on_saved, record=p)

    def delete_package(self):
        if not self.user.is_admin():
            messagebox.showerror("Permission", "Only admin/staff may delete package records.")
            return
        p = self.get_selected()
        if not p:
            messagebox.showwarning("Select", "Please select a record.")
            return
        if messagebox.askyesno("Confirm", "Delete this package record?"):
            self.packages = [pk for pk in self.packages if pk.id != p.id]
            self.save_and_refresh()

    def mark_picked(self):
        p = self.get_selected()
        if not p:
            messagebox.showwarning("Select", "Please select a record.")
            return
        if (not self.user.is_admin()) and self.user.unit and p.unit != self.user.unit:
            messagebox.showerror("Permission", "You can only mark packages for your own unit as picked up.")
            return
        p.picked_up = True
        self.save_and_refresh()

    def on_saved(self, record: PackageRecord, is_new: bool):
        if is_new:
            self.packages.append(record)
        else:
            for i, p in enumerate(self.packages):
                if p.id == record.id:
                    self.packages[i] = record
                    break
        self.save_and_refresh()

        if self.user.is_admin():
            messagebox.showinfo(
                "Resident notified",
                f"Resident in Unit {record.unit} has been notified about the package update."
            )
        return True

    def save_and_refresh(self):
        """Persist packages and refresh tree + admin summary."""
        self.store.set_packages(self.packages)
        self.store.save()
        self.refresh_tree()

        if self.on_changed:
            self.on_changed()


class PackageForm(tk.Toplevel):
    def __init__(self, master: PackageWindow, store: DataStore, on_save, record: PackageRecord = None):
        super().__init__(master)
        self.title("Package")
        self.store = store
        self.on_save = on_save
        self.record = record

        self.geometry("420x230")

        tk.Label(self, text="Unit:").grid(row=0, column=0, sticky="w", padx=10, pady=5)
        self.unit_entry = tk.Entry(self)
        self.unit_entry.grid(row=0, column=1, padx=10, pady=5)

        tk.Label(self, text="Carrier:").grid(row=1, column=0, sticky="w", padx=10, pady=5)
        self.carrier_entry = tk.Entry(self)
        self.carrier_entry.grid(row=1, column=1, padx=10, pady=5)

        tk.Label(self, text="Arrival date (YYYY-MM-DD):").grid(row=2, column=0, sticky="w", padx=10, pady=5)
        self.date_entry = tk.Entry(self)
        self.date_entry.grid(row=2, column=1, padx=10, pady=5)

        self.picked_var = tk.BooleanVar(value=False)
        tk.Checkbutton(self, text="Picked up", variable=self.picked_var).grid(
            row=3, column=0, columnspan=2, padx=10, pady=5, sticky="w"
        )

        btn_frame = tk.Frame(self)
        btn_frame.grid(row=4, column=0, columnspan=2, pady=10)
        tk.Button(btn_frame, text="Save", command=self.save).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side="left", padx=5)

        if self.record:
            self.unit_entry.insert(0, self.record.unit)
            self.carrier_entry.insert(0, self.record.carrier)
            self.date_entry.insert(0, self.record.arrival_date)
            self.picked_var.set(self.record.picked_up)

    def save(self):
        unit = self.unit_entry.get().strip()
        carrier = self.carrier_entry.get().strip()
        date_str = self.date_entry.get().strip()
        picked = self.picked_var.get()

        if not unit or not carrier or not date_str:
            messagebox.showerror("Error", "All fields are required.")
            return

        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Error", "Date must be in YYYY-MM-DD format.")
            return

        if self.record:
            rec_id = self.record.id
        else:
            rec_id = self.store.next_id("packages")

        rec = PackageRecord(
            package_id=rec_id,
            unit=unit,
            carrier=carrier,
            arrival_date=date_str,
            picked_up=picked,
        )

        is_new = self.record is None
        ok = self.on_save(rec, is_new)
        if ok:
            self.destroy()


# ------------------------- GUI: Service Requests ------------------------- #

class ServiceRequestWindow(tk.Toplevel):
    TYPES = ["Service Request", "Architectural Change Request",
             "Suggestion", "Question"]

    def __init__(self, master, store: DataStore, user: User, on_changed=None):
        super().__init__(master)
        self.title("Service Requests")
        self.store = store
        self.user = user
        self.on_changed = on_changed
        self.requests = self.store.get_service_requests()
        self.current_view = []
        self.geometry("800x450")

        top = tk.Frame(self)
        top.pack(fill="x", padx=10, pady=5)

        tk.Label(top, text="Service Requests", font=("Arial", 12, "bold")).pack(side="left")

        btn_frame = tk.Frame(top)
        btn_frame.pack(side="right")
        tk.Button(btn_frame, text="New Request", width=13, command=self.new_request).pack(side="left", padx=3)
        tk.Button(btn_frame, text="Edit", width=10, command=self.edit_request).pack(side="left", padx=3)
        tk.Button(btn_frame, text="Delete", width=10, command=self.delete_request).pack(side="left", padx=3)
        if self.user.is_admin():
            tk.Button(btn_frame, text="Change Status", width=13, command=self.change_status).pack(side="left", padx=3)

        # Main list of requests
        self.listbox = tk.Listbox(self, height=12)
        self.listbox.pack(fill="both", expand=True, padx=10, pady=(0, 5))
        self.listbox.bind("<<ListboxSelect>>", self.show_details)

        # Details area to show full description
        details_frame = tk.LabelFrame(self, text="Details", padx=5, pady=5)
        details_frame.pack(fill="both", expand=False, padx=10, pady=(0, 10))

        self.detail_text = tk.Text(details_frame, height=4, wrap="word", state="disabled")
        self.detail_text.pack(fill="both", expand=True)

        self.refresh_listbox()

    def refresh_listbox(self):
        self.listbox.delete(0, tk.END)
        if self.user.is_admin():
            self.current_view = list(self.requests)
        else:
            # Residents only see their own submitted requests
            self.current_view = [r for r in self.requests if r.created_by == self.user.username]

        for r in self.current_view:
            txt = f"#{r.id} | Unit {r.unit} | {r.req_type} | {r.status}"
            self.listbox.insert(tk.END, txt)

        self.show_details()

    def show_details(self, event=None):
        self.detail_text.config(state="normal")
        self.detail_text.delete("1.0", "end")
        idx = self.listbox.curselection()
        if idx:
            req = self.current_view[idx[0]]
            text = f"Unit: {req.unit}\nType: {req.req_type}\nStatus: {req.status}\n\n{req.description}"
            self.detail_text.insert("1.0", text)
        self.detail_text.config(state="disabled")

    def get_selected(self):
        idx = self.listbox.curselection()
        if not idx:
            return None
        return self.current_view[idx[0]]

    def new_request(self):
        ServiceRequestForm(self, self.store, on_save=self.on_saved, request=None)

    def edit_request(self):
        r = self.get_selected()
        if not r:
            messagebox.showwarning("Select", "Please select a request.")
            return
        if (not self.user.is_admin()) and r.created_by != self.user.username:
            messagebox.showerror("Permission", "You can only edit your own requests.")
            return
        ServiceRequestForm(self, self.store, on_save=self.on_saved, request=r)

    def delete_request(self):
        r = self.get_selected()
        if not r:
            messagebox.showwarning("Select", "Please select a request.")
            return

        # ---- Permission logic ----
        # Admin: can delete anything
        # Resident: can delete ONLY requests they created
        if not self.user.is_admin():
            if r.created_by != self.user.username:
                messagebox.showerror(
                    "Permission",
                    "You can only delete your own service requests."
                )
                return

        # Confirm deletion
        if messagebox.askyesno("Confirm", "Delete this request?"):
            self.requests = [req for req in self.requests if req.id != r.id]
            self.save_and_refresh()

    def change_status(self):
        r = self.get_selected()
        if not r:
            messagebox.showwarning("Select", "Please select a request.")
            return
        if not self.user.is_admin():
            messagebox.showerror("Permission", "Only admin/staff may change status.")
            return
        StatusForm(self, r, on_save=self.on_status_changed)

    def on_status_changed(self, req: ServiceRequest):
        for i, r in enumerate(self.requests):
            if r.id == req.id:
                self.requests[i] = req
                break
        self.save_and_refresh()

    def on_saved(self, req: ServiceRequest, is_new: bool):
        if is_new:
            self.requests.append(req)
        else:
            for i, r in enumerate(self.requests):
                if r.id == req.id:
                    self.requests[i] = req
                    break
        self.save_and_refresh()
        return True

    def save_and_refresh(self):
        """Persist service requests and refresh list + admin summary."""
        self.store.set_service_requests(self.requests)
        self.store.save()
        self.refresh_listbox()

        if self.on_changed:
            self.on_changed()


class ServiceRequestForm(tk.Toplevel):
    def __init__(self, master: ServiceRequestWindow, store: DataStore, on_save, request: ServiceRequest = None):
        super().__init__(master)
        self.title("Service Request")
        self.store = store
        self.on_save = on_save
        self.request = request

        self.geometry("600x380")  # a bit wider

        # Let the window and form expand nicely
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        form = tk.Frame(self, padx=30, pady=30)
        form.grid(row=0, column=0, sticky="nsew")

        # Make column 1 (inputs) stretch horizontally
        form.columnconfigure(0, weight=0)
        form.columnconfigure(1, weight=1)

        # --- Unit ---
        tk.Label(form, text="Unit:").grid(
            row=0, column=0, sticky="e", padx=(0, 10), pady=5
        )
        self.unit_entry = tk.Entry(form)
        self.unit_entry.grid(
            row=0, column=1, sticky="we", pady=5
        )

        # --- Type ---
        tk.Label(form, text="Type:").grid(
            row=1, column=0, sticky="e", padx=(0, 10), pady=5
        )
        self.type_var = tk.StringVar(value=ServiceRequestWindow.TYPES[0])
        self.type_menu = ttk.Combobox(
            form,
            textvariable=self.type_var,
            values=ServiceRequestWindow.TYPES,
            state="readonly",
        )
        self.type_menu.grid(
            row=1, column=1, sticky="we", pady=5
        )

        # --- Description ---
        tk.Label(form, text="Description:").grid(
            row=2, column=0, sticky="ne", padx=(0, 10), pady=(10, 5)
        )
        self.desc_text = tk.Text(form, height=8, width=40)
        self.desc_text.grid(
            row=2, column=1, sticky="nsew", pady=(10, 5)
        )

        # Let the description row grow vertically
        form.rowconfigure(2, weight=1)

        # --- Buttons ---
        btn_frame = tk.Frame(form)
        btn_frame.grid(row=3, column=1, sticky="e", pady=(20, 0))

        tk.Button(btn_frame, text="Save", command=self.save, width=10).pack(
            side="left", padx=(0, 10)
        )
        tk.Button(btn_frame, text="Cancel", command=self.destroy, width=10).pack(
            side="left"
        )

        # Pre-fill data
        if self.request:
            self.unit_entry.insert(0, self.request.unit)
            self.type_var.set(self.request.req_type)
            self.desc_text.insert("1.0", self.request.description)
        else:
            # For residents, auto-fill unit
            user = master.user
            if (not user.is_admin()) and user.unit:
                self.unit_entry.insert(0, user.unit)
                self.unit_entry.config(state="disabled")

    def save(self):
        unit = self.unit_entry.get().strip()
        req_type = self.type_var.get().strip()
        desc = self.desc_text.get("1.0", "end").strip()

        if not unit or not req_type or not desc:
            messagebox.showerror("Error", "All fields are required.")
            return

        if self.request:
            req_id = self.request.id
            status = self.request.status
            created_by = self.request.created_by
        else:
            req_id = self.store.next_id("service_requests")
            status = "Submitted"
            user = self.master.user
            created_by = user.username if user is not None else ""

        req = ServiceRequest(
            req_id=req_id,
            unit=unit,
            req_type=req_type,
            description=desc,
            status=status,
            created_by=created_by,
        )

        is_new = self.request is None
        ok = self.on_save(req, is_new)
        if ok:
            self.destroy()


class StatusForm(tk.Toplevel):
    def __init__(self, master: ServiceRequestWindow, request: ServiceRequest, on_save):
        super().__init__(master)
        self.title("Change Status")
        self.request = request
        self.on_save = on_save

        self.geometry("260x160")

        tk.Label(self, text=f"Request #{self.request.id} status:").pack(padx=10, pady=10)
        self.status_var = tk.StringVar(value=self.request.status)
        combo = ttk.Combobox(self, textvariable=self.status_var,
                             values=["Submitted", "In Progress", "Resolved"],
                             state="readonly")
        combo.pack(padx=10, pady=5)

        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="Save", command=self.save).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side="left", padx=5)

    def save(self):
        self.request.status = self.status_var.get()
        self.on_save(self.request)
        self.destroy()


# ------------------------- GUI: Announcements ------------------------- #

class AnnouncementWindow(tk.Toplevel):
    def __init__(self, master: DashboardFrame, store: DataStore, user: User, on_update=None):
        super().__init__(master)
        self.title("Announcements")
        self.store = store
        self.user = user
        self.announcements = self.store.get_announcements()
        self.on_update = on_update
        self.geometry("900x360")

        top = tk.Frame(self)
        top.pack(fill="x", padx=10, pady=5)

        if self.user.is_admin():
            tk.Button(top, text="Add", command=self.add_announcement).pack(side="left", padx=5)
            tk.Button(top, text="Edit", command=self.edit_announcement).pack(side="left", padx=5)
            tk.Button(top, text="Delete", command=self.delete_announcement).pack(side="left", padx=5)

        self.listbox = tk.Listbox(self, height=14)
        self.listbox.pack(fill="both", expand=True, padx=10, pady=5)

        self.refresh_listbox()

    def refresh_listbox(self):
        self.listbox.delete(0, tk.END)
        for a in self.announcements:
            txt = f"#{a.id} | {a.created_at} | {a.title} | {a.content}"
            self.listbox.insert(tk.END, txt)

    def get_selected(self):
        idx = self.listbox.curselection()
        if not idx:
            return None
        return self.announcements[idx[0]]

    def add_announcement(self):
        AnnouncementForm(self, self.store, on_save=self.on_saved, announcement=None)

    def edit_announcement(self):
        a = self.get_selected()
        if not a:
            messagebox.showwarning("Select", "Please select an announcement.")
            return
        AnnouncementForm(self, self.store, on_save=self.on_saved, announcement=a)

    def delete_announcement(self):
        a = self.get_selected()
        if not a:
            messagebox.showwarning("Select", "Please select an announcement.")
            return
        if messagebox.askyesno("Confirm", "Delete this announcement?"):
            self.announcements = [ann for ann in self.announcements if ann.id != a.id]
            self.save_and_refresh()

    def on_saved(self, ann: Announcement, is_new: bool):
        if is_new:
            self.announcements.append(ann)
        else:
            for i, a in enumerate(self.announcements):
                if a.id == ann.id:
                    self.announcements[i] = ann
                    break
        self.save_and_refresh()
        return True

    def save_and_refresh(self):
        self.store.set_announcements(self.announcements)
        self.store.save()
        self.refresh_listbox()
        if self.on_update:
            self.on_update()


class AnnouncementForm(tk.Toplevel):
    def __init__(self, master: AnnouncementWindow, store: DataStore, on_save, announcement: Announcement = None):
        super().__init__(master)
        self.title("Announcement")
        self.store = store
        self.on_save = on_save
        self.announcement = announcement
        self.geometry("600x260")

        tk.Label(self, text="Title:").grid(row=0, column=0, sticky="w", padx=10, pady=5)
        self.title_entry = tk.Entry(self, width=50)
        self.title_entry.grid(row=0, column=1, padx=10, pady=5, sticky="ew")

        tk.Label(self, text="Content:").grid(row=1, column=0, sticky="nw", padx=10, pady=(5, 5))
        self.content_text = tk.Text(self, width=50, height=8)
        self.content_text.grid(row=1, column=1, padx=10, pady=5, sticky="ew")

        btn_frame = tk.Frame(self)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=10)
        tk.Button(btn_frame, text="Save", command=self.save).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side="left", padx=5)

        if self.announcement:
            self.title_entry.insert(0, self.announcement.title)
            self.content_text.insert("1.0", self.announcement.content)

    def save(self):
        title = self.title_entry.get().strip()
        content = self.content_text.get("1.0", "end").strip()

        if not title or not content:
            messagebox.showerror("Error", "All fields are required.")
            return

        if self.announcement:
            ann_id = self.announcement.id
            created_at = self.announcement.created_at
        else:
            ann_id = self.store.next_id("announcements")
            created_at = None

        ann = Announcement(ann_id=ann_id, title=title, content=content, created_at=created_at)

        is_new = self.announcement is None
        ok = self.on_save(ann, is_new)
        if ok:
            self.destroy()


# ------------------------- Main Application ------------------------- #

class CondoApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Condo Amenity & Service Hub")
        self.geometry("960x540")
        self.store = DataStore()
        self.current_frame = None
        self.user = None
        self.show_login()

    def clear_current_frame(self):
        if self.current_frame is not None:
            self.current_frame.destroy()
            self.current_frame = None

    def show_login(self):
        self.clear_current_frame()
        self.current_frame = LoginFrame(self, app=self)
        self.current_frame.pack(fill="both", expand=True)

    def show_dashboard(self, user: User):
        self.user = user
        self.clear_current_frame()
        self.current_frame = DashboardFrame(self, app=self, user=user, store=self.store)
        self.current_frame.pack(fill="both", expand=True)

    def logout(self):
        # Close current frame
        if self.current_frame:
            self.current_frame.destroy()
            self.current_frame = None
        # Clear user session
        self.user = None
        # Return to login screen
        self.show_login()


if __name__ == "__main__":
    app = CondoApp()
    app.mainloop()
