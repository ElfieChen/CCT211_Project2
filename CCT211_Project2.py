#!/usr/bin/env python3
"""
Condo Amenity & Service Hub - improved implementation with role-based UI
Matches the proposal: login -> dashboard -> (amenities, packages, service requests, announcements)
Uses JSON for persistence.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
from datetime import datetime


# ------------------------- Domain Models ------------------------- #

class User:
    def __init__(self, username: str, role: str = "resident", unit: str = ""):
        self.username = username
        self.role = role  # "resident" or "admin"
        self.unit = unit

    def is_admin(self) -> bool:
        return self.role == "admin"


class AmenityBooking:
    def __init__(self, booking_id: int, unit: str, facility_type: str,
                 date_str: str, start_time: str, end_time: str,
                 status: str = "Booked", created_by: str = ""):
        self.id = booking_id
        self.unit = unit
        self.facility_type = facility_type
        self.date = date_str        # "YYYY-MM-DD"
        self.start_time = start_time  # "HH:MM"
        self.end_time = end_time      # "HH:MM"
        self.status = status
        # Which user created this booking (for permissions)
        self.created_by = created_by

    def to_dict(self) -> dict:
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


# ------------------------- Persistence Layer ------------------------- #

class DataStore:
    """JSON-based persistence for all entities."""

    def __init__(self, filename: str = "condo_data.json"):
        self.filename = filename
        self.data = {
            "users": [],
            "amenity_bookings": [],
            "packages": [],
            "service_requests": [],
            "announcements": [],
        }
        self.load()

    def load(self) -> None:
        if os.path.exists(self.filename):
            try:
                with open(self.filename, "r", encoding="utf-8") as f:
                    d = json.load(f)
                for key in self.data:
                    if key in d and isinstance(d[key], list):
                        self.data[key] = d[key]
            except (IOError, json.JSONDecodeError):
                # start with empty data if file is corrupted
                pass

    def save(self) -> None:
        try:
            with open(self.filename, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
        except IOError as e:
            print("Error saving data:", e)

    def next_id(self, key: str) -> int:
        items = self.data.get(key, [])
        if not items:
            return 1
        return max(item.get("id", 0) for item in items) + 1

    # Convenience getters/setters

    def get_amenity_bookings(self):
        return [AmenityBooking.from_dict(d) for d in self.data["amenity_bookings"]]

    def set_amenity_bookings(self, bookings):
        self.data["amenity_bookings"] = [b.to_dict() for b in bookings]

    def get_packages(self):
        return [PackageRecord.from_dict(d) for d in self.data["packages"]]

    def set_packages(self, packages):
        self.data["packages"] = [p.to_dict() for p in packages]

    def get_service_requests(self):
        return [ServiceRequest.from_dict(d) for d in self.data["service_requests"]]

    def set_service_requests(self, requests):
        self.data["service_requests"] = [r.to_dict() for r in requests]

    def get_announcements(self):
        return [Announcement.from_dict(d) for d in self.data["announcements"]]

    def set_announcements(self, announcements):
        self.data["announcements"] = [a.to_dict() for a in announcements]


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

        tk.Label(self, text="Condo Amenity & Service Hub",
                 font=("Arial", 18, "bold")).pack(pady=(0, 15))

        form = tk.Frame(self)
        form.pack(fill="x")

        # Username
        tk.Label(form, text="Username:").grid(row=0, column=0, sticky="e", pady=5, padx=5)
        self.username_entry = tk.Entry(form, width=25)
        self.username_entry.grid(row=0, column=1, pady=5, padx=5)

        # Unit
        tk.Label(form, text="Unit:").grid(row=1, column=0, sticky="e", pady=5, padx=5)
        self.unit_entry = tk.Entry(form, width=25)
        self.unit_entry.grid(row=1, column=1, pady=5, padx=5)

        # Role
        tk.Label(self, text="Role (for demo):").pack(anchor="w", pady=(15, 5))
        self.role_var = tk.StringVar(value="resident")
        role_frame = tk.Frame(self)
        role_frame.pack(anchor="w")
        tk.Radiobutton(role_frame, text="Resident", variable=self.role_var,
                       value="resident").pack(side="left")
        tk.Radiobutton(role_frame, text="Admin", variable=self.role_var,
                       value="admin").pack(side="left", padx=(10, 0))

        tk.Button(self, text="Login", width=18, command=self.do_login).pack(pady=20)

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

        # Top bar
        top_bar = tk.Frame(self, bg="#0f3b3a", height=50)
        top_bar.pack(fill="x")

        menu_lbl = tk.Label(top_bar, text="≡", fg="white", bg="#0f3b3a",
                            font=("Arial", 18))
        menu_lbl.pack(side="left", padx=10)

        role_text = "Admin Console" if self.user.is_admin() else "Resident Portal"
        tk.Label(top_bar, text=role_text, fg="white", bg="#0f3b3a",
                 font=("Arial", 14, "bold")).pack(side="left", padx=10)

        welcome_bits = f"{self.user.username}"
        if self.user.unit:
            welcome_bits += f" • Unit {self.user.unit}"
        tk.Label(top_bar, text=welcome_bits, fg="white", bg="#0f3b3a",
                 font=("Arial", 11)).pack(side="right", padx=10)

        # Announcement card
        announce_frame = tk.Frame(self, bg="#d9eceb")
        announce_frame.pack(fill="x", padx=20, pady=(15, 10))

        tk.Label(announce_frame, text="Today's Condo Announcement",
                 bg="#d9eceb", font=("Arial", 12, "bold")).pack(
            anchor="w", padx=10, pady=(8, 0)
        )

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
        tk.Button(btn_frame, text="View all", command=self.open_announcements) \
            .pack(side="right")
        if self.user.is_admin():
            tk.Button(btn_frame, text="Manage", command=self.open_announcements) \
                .pack(side="right", padx=(0, 5))

        # Ensure at least one "today's update" style announcement for residents
        self.ensure_default_announcement()
        self.refresh_announcement_text()

        # Tiles
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

        # Amenity tile
        tk.Label(amenity_tile, text="🏊", font=("Arial", 32), bg="white").pack(pady=(15, 5))
        tk.Label(amenity_tile, text="Book Amenities", font=("Arial", 12, "bold"),
                 bg="white").pack()
        tk.Label(amenity_tile, text="Reserve gym, pool lanes, party room.",
                 font=("Arial", 9), bg="white", fg="#555555", wraplength=200).pack(pady=(2, 4))
        tk.Button(amenity_tile, text="Open",
                  command=self.open_amenities).pack(pady=10)

        # Package tile
        tk.Label(pkg_tile, text="📦", font=("Arial", 32), bg="white").pack(pady=(15, 5))
        tk.Label(pkg_tile, text="Packages", font=("Arial", 12, "bold"),
                 bg="white").pack()
        tk.Label(pkg_tile, text="Track deliveries and pickup status.",
                 font=("Arial", 9), bg="white", fg="#555555", wraplength=200).pack(pady=(2, 4))
        tk.Button(pkg_tile, text="Open",
                  command=self.open_packages).pack(pady=10)

        # Service Requests tile
        tk.Label(srv_tile, text="🛠", font=("Arial", 32), bg="white").pack(pady=(15, 5))
        tk.Label(srv_tile, text="Service Requests", font=("Arial", 12, "bold"),
                 bg="white").pack()
        tk.Label(srv_tile, text="Submit repair and concierge requests.",
                 font=("Arial", 9), bg="white", fg="#555555", wraplength=200).pack(pady=(2, 4))
        tk.Button(srv_tile, text="Open",
                  command=self.open_service_requests).pack(pady=10)

        # Simple admin summary bar so admin view feels different
        if self.user.is_admin():
            stats_frame = tk.Frame(self, bg="#f2f2f2")
            stats_frame.pack(fill="x", padx=20, pady=(0, 15))

            bookings_count = len(self.store.get_amenity_bookings())
            packages_count = len(self.store.get_packages())
            requests_count = len(self.store.get_service_requests())

            def make_stat(parent, title, value):
                card = tk.Frame(parent, bg="white", bd=1, relief="solid")
                card.pack(side="left", expand=True, fill="x", padx=5)
                tk.Label(card, text=title, bg="white",
                         font=("Arial", 10, "bold")).pack(pady=(6, 0))
                tk.Label(card, text=str(value), bg="white",
                         font=("Arial", 14)).pack(pady=(0, 6))

            make_stat(stats_frame, "Total Amenity Bookings", bookings_count)
            make_stat(stats_frame, "Total Packages", packages_count)
            make_stat(stats_frame, "Service Requests", requests_count)

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

    def open_announcements(self):
        AnnouncementWindow(self, self.store, self.user, on_update=self.refresh_announcement_text)

    def open_amenities(self):
        AmenityWindow(self, self.store, self.user)

    def open_packages(self):
        PackageWindow(self, self.store, self.user)

    def open_service_requests(self):
        ServiceRequestWindow(self, self.store, self.user)


# ------------------------- GUI: Amenity Booking Window ------------------------- #

class AmenityWindow(tk.Toplevel):
    FACILITIES = ["Meeting Room", "Swimming Pool Lane", "Gym", "Party Room"]

    def __init__(self, master, store: DataStore, user: User):
        super().__init__(master)
        self.title("Amenity Bookings")
        self.store = store
        self.user = user
        self.bookings = self.store.get_amenity_bookings()

        self.geometry("750x420")

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

        # Listbox for bookings (simplified but larger)
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
        if not self.user.is_admin():
            messagebox.showerror("Permission", "Only admin/staff may delete bookings.")
            return
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
        self.store.set_amenity_bookings(self.bookings)
        self.store.save()
        self.refresh_listbox()


class BookingForm(tk.Toplevel):
    def __init__(self, master: AmenityWindow, store: DataStore, on_save, booking: AmenityBooking = None):
        super().__init__(master)
        self.title("Amenity Booking")
        self.store = store
        self.on_save = on_save
        self.booking = booking

        self.geometry("360x300")

        tk.Label(self, text="Unit:").grid(row=0, column=0, sticky="w", padx=10, pady=5)
        self.unit_entry = tk.Entry(self)
        self.unit_entry.grid(row=0, column=1, padx=10, pady=5)

        tk.Label(self, text="Facility:").grid(row=1, column=0, sticky="w", padx=10, pady=5)
        self.fac_var = tk.StringVar(value=AmenityWindow.FACILITIES[0])
        self.fac_menu = ttk.Combobox(self, textvariable=self.fac_var, values=AmenityWindow.FACILITIES,
                                     state="readonly")
        self.fac_menu.grid(row=1, column=1, padx=10, pady=5)

        tk.Label(self, text="Date (YYYY-MM-DD):").grid(row=2, column=0, sticky="w", padx=10, pady=5)
        self.date_entry = tk.Entry(self)
        self.date_entry.grid(row=2, column=1, padx=10, pady=5)

        tk.Label(self, text="Start time (HH:MM):").grid(row=3, column=0, sticky="w", padx=10, pady=5)
        self.start_entry = tk.Entry(self)
        self.start_entry.grid(row=3, column=1, padx=10, pady=5)

        tk.Label(self, text="End time (HH:MM):").grid(row=4, column=0, sticky="w", padx=10, pady=5)
        self.end_entry = tk.Entry(self)
        self.end_entry.grid(row=4, column=1, padx=10, pady=5)

        tk.Label(self, text="Status:").grid(row=5, column=0, sticky="w", padx=10, pady=5)
        self.status_var = tk.StringVar(value="Booked")
        self.status_menu = ttk.Combobox(self, textvariable=self.status_var,
                                        values=["Booked", "Cancelled"],
                                        state="readonly")
        self.status_menu.grid(row=5, column=1, padx=10, pady=5)

        btn_frame = tk.Frame(self)
        btn_frame.grid(row=6, column=0, columnspan=2, pady=10)
        tk.Button(btn_frame, text="Save", command=self.save).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side="left", padx=5)

        user = getattr(master, "user", None)

        if self.booking:
            # Editing an existing booking
            self.unit_entry.insert(0, self.booking.unit)
            self.fac_var.set(self.booking.facility_type)
            self.date_entry.insert(0, self.booking.date)
            self.start_entry.insert(0, self.booking.start_time)
            self.end_entry.insert(0, self.booking.end_time)
            self.status_var.set(self.booking.status)
        else:
            # New booking: for residents, pre-fill their unit and lock it
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

        # Simple date/time validation
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Error", "Date must be in YYYY-MM-DD format.")
            return

        start_m = parse_time_to_minutes(start)
        end_m = parse_time_to_minutes(end)
        if start_m < 0 or end_m < 0 or end_m <= start_m:
            messagebox.showerror("Error", "Invalid time range.")
            return

        if self.booking:
            booking_id = self.booking.id
        else:
            booking_id = self.store.next_id("amenity_bookings")

        # Determine creator
        user = getattr(self.master, "user", None)
        creator = user.username if user is not None else ""
        if self.booking:
            # Preserve original creator if editing
            creator = getattr(self.booking, "created_by", creator)

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

        is_new = self.booking is None
        ok_to_close = self.on_save(booking, is_new)
        if ok_to_close:
            self.destroy()


# ------------------------- GUI: Packages Window ------------------------- #

class PackageWindow(tk.Toplevel):
    def __init__(self, master, store: DataStore, user: User):
        super().__init__(master)
        self.title("Packages")
        self.store = store
        self.user = user
        self.packages = self.store.get_packages()
        self.current_view = []
        self.geometry("780x420")

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

        self.tree.column("unit", width=80, anchor="center")
        self.tree.column("carrier", width=180)
        self.tree.column("arrival", width=120, anchor="center")
        self.tree.column("status", width=120, anchor="center")

        self.tree.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.refresh_tree()

    def filtered_packages(self):
        # Resident can only see their own unit's packages
        pkgs = self.packages
        if not self.user.is_admin() and self.user.unit:
            pkgs = [p for p in pkgs if p.unit == self.user.unit]

        prefix = self.search_var.get().strip()
        if prefix:
            pkgs = [p for p in pkgs if p.unit.startswith(prefix)]
        return pkgs

    def refresh_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.current_view = self.filtered_packages()
        for idx, p in enumerate(self.current_view):
            status = "Picked up" if p.picked_up else "Waiting"
            self.tree.insert("", "end", iid=str(idx),
                             values=(p.unit, p.carrier, p.arrival_date, status))

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
        self.store.set_packages(self.packages)
        self.store.save()
        self.refresh_tree()


class PackageForm(tk.Toplevel):
    def __init__(self, master: PackageWindow, store: DataStore, on_save, record: PackageRecord = None):
        super().__init__(master)
        self.title("Package")
        self.store = store
        self.on_save = on_save
        self.record = record

        self.geometry("340x230")

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

    def __init__(self, master, store: DataStore, user: User):
        super().__init__(master)
        self.title("Service Requests")
        self.store = store
        self.user = user
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

        # Details area to show full description so this window looks different
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

        self.show_details()  # clear / refresh details

    def show_details(self, event=None):
        self.detail_text.config(state="normal")
        self.detail_text.delete("1.0", "end")
        r = self.get_selected()
        if r:
            self.detail_text.insert("1.0", r.description)
        self.detail_text.config(state="disabled")

    def get_selected(self):
        idx = self.listbox.curselection()
        if not idx:
            return None
        index = idx[0]
        if 0 <= index < len(self.current_view):
            return self.current_view[index]
        return None

    def new_request(self):
        ServiceRequestForm(self, self.store, on_save=self.on_saved, request=None)

    def edit_request(self):
        r = self.get_selected()
        if not r:
            messagebox.showwarning("Select", "Please select a request.")
            return
        if (not self.user.is_admin()) and r.created_by != self.user.username:
            messagebox.showerror("Permission", "You can only edit requests that you submitted.")
            return
        ServiceRequestForm(self, self.store, on_save=self.on_saved, request=r)

    def delete_request(self):
        r = self.get_selected()
        if not r:
            messagebox.showwarning("Select", "Please select a request.")
            return
        if not self.user.is_admin():
            messagebox.showerror("Permission", "Only admin/staff may delete requests.")
            return
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

        if self.user.is_admin():
            messagebox.showinfo(
                "Resident notified",
                f"Resident in Unit {req.unit} has been notified about the status update."
            )

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
        self.store.set_service_requests(self.requests)
        self.store.save()
        self.refresh_listbox()


class ServiceRequestForm(tk.Toplevel):
    def __init__(self, master: ServiceRequestWindow, store: DataStore, on_save, request: ServiceRequest = None):
        super().__init__(master)
        self.title("Service Request")
        self.store = store
        self.on_save = on_save
        self.request = request

        self.geometry("380x280")

        tk.Label(self, text="Unit:").grid(row=0, column=0, sticky="w", padx=10, pady=5)
        self.unit_entry = tk.Entry(self)
        self.unit_entry.grid(row=0, column=1, padx=10, pady=5)

        tk.Label(self, text="Type:").grid(row=1, column=0, sticky="w", padx=10, pady=5)
        self.type_var = tk.StringVar(value=ServiceRequestWindow.TYPES[0])
        self.type_menu = ttk.Combobox(self, textvariable=self.type_var,
                                      values=ServiceRequestWindow.TYPES, state="readonly")
        self.type_menu.grid(row=1, column=1, padx=10, pady=5)

        tk.Label(self, text="Description:").grid(row=2, column=0, sticky="nw", padx=10, pady=5)
        self.desc_text = tk.Text(self, height=5, width=30)
        self.desc_text.grid(row=2, column=1, padx=10, pady=5)

        btn_frame = tk.Frame(self)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=10)
        tk.Button(btn_frame, text="Save", command=self.save).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side="left", padx=5)

        user = getattr(master, "user", None)

        if self.request:
            self.unit_entry.insert(0, self.request.unit)
            self.type_var.set(self.request.req_type)
            self.desc_text.insert("1.0", self.request.description)
        else:
            # For resident, prefill their unit and lock it
            if user and not user.is_admin() and user.unit:
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
            creator = self.request.created_by
        else:
            req_id = self.store.next_id("service_requests")
            status = "Submitted"
            user = getattr(self.master, "user", None)
            creator = user.username if user is not None else ""

        req = ServiceRequest(req_id=req_id, unit=unit, req_type=req_type,
                             description=desc, status=status, created_by=creator)

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
        self.geometry("650x380")

        top = tk.Frame(self)
        top.pack(fill="x", padx=10, pady=5)

        tk.Label(top, text="Announcements", font=("Arial", 12, "bold")).pack(side="left")

        if self.user.is_admin():
            btn_frame = tk.Frame(top)
            btn_frame.pack(side="right")
            tk.Button(btn_frame, text="Add", width=10, command=self.add_announcement).pack(side="left", padx=3)
            tk.Button(btn_frame, text="Edit", width=10, command=self.edit_announcement).pack(side="left", padx=3)
            tk.Button(btn_frame, text="Delete", width=10, command=self.delete_announcement).pack(side="left", padx=3)

        self.listbox = tk.Listbox(self, height=16)
        self.listbox.pack(fill="both", expand=True, padx=10, pady=5)

        self.refresh_listbox()

    def refresh_listbox(self):
        self.listbox.delete(0, tk.END)
        for a in self.announcements:
            txt = f"#{a.id} | {a.created_at} | {a.title} | {a.content[:50]}"
            self.listbox.insert(tk.END, txt)

    def get_selected(self):
        idx = self.listbox.curselection()
        if not idx:
            return None
        return self.announcements[idx[0]]

    def add_announcement(self):
        AnnouncementForm(self, self.store, on_save=self.on_saved)

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

        self.geometry("380x260")

        tk.Label(self, text="Title:").grid(row=0, column=0, sticky="w", padx=10, pady=5)
        self.title_entry = tk.Entry(self, width=35)
        self.title_entry.grid(row=0, column=1, padx=10, pady=5)

        tk.Label(self, text="Content:").grid(row=1, column=0, sticky="nw", padx=10, pady=5)
        self.content_text = tk.Text(self, width=30, height=5)
        self.content_text.grid(row=1, column=1, padx=10, pady=5)

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
        # Make main window a bit larger so it feels more like an app dashboard
        self.geometry("900x580")
        self.minsize(820, 520)
        self.store = DataStore()
        self.current_frame = None
        self.show_login()

        # Simple menu bar (File -> Exit) for a more "app-like" feel
        menubar = tk.Menu(self)
        file_menu = tk.Menu(menubar, tearoff=False)
        file_menu.add_command(label="Exit", command=self.destroy)
        menubar.add_cascade(label="File", menu=file_menu)
        self.config(menu=menubar)

    def clear_current_frame(self):
        if self.current_frame is not None:
            self.current_frame.destroy()
            self.current_frame = None

    def show_login(self):
        self.clear_current_frame()
        self.current_frame = LoginFrame(self, app=self)
        self.current_frame.pack(fill="both", expand=True)

    def show_dashboard(self, user: User):
        self.clear_current_frame()
        self.current_frame = DashboardFrame(self, app=self, user=user, store=self.store)
        self.current_frame.pack(fill="both", expand=True)


if __name__ == "__main__":
    app = CondoApp()
    app.mainloop()
