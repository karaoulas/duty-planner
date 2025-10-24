# Duty Planner

A Flask web application for military unit duty rotation management. This system assigns daily duties (σκοπιά, θαλαμοφύλακας, κουζίνα, etc.) to soldiers on a fair, rotating basis.

## Features

- **Soldier Management**: Register soldiers with rank, role, and availability status.
- **Fair Rotation Algorithm**: Automatically assigns duties based on past workload (lowest service count gets priority).
- **Unavailability Tracking**: Mark soldiers as unavailable for specific dates (leave, illness, etc.).
- **Schedule Management**: View, generate, and confirm duty schedules for any date.
- **Role-Based Assignment**: Matches soldiers to duties based on their assigned roles.
- **Clean UI**: Bootstrap 5 responsive interface with intuitive navigation.

## Tech Stack

- **Backend**: Flask 3.x, Python 3.x
- **Database**: SQLite with Flask-SQLAlchemy 3.x ORM
- **Frontend**: Jinja2 templates, Bootstrap 5 (CDN), vanilla JavaScript
- **Production**: Gunicorn WSGI server

## Project Structure

```
duty-planner/
├── app.py                      # Main Flask application and routes
├── models.py                   # SQLAlchemy models (Soldier, Assignment, Unavailability)
├── requirements.txt            # Python dependencies
├── Procfile                    # Production deployment configuration
├── README.md                   # This file
│
├── instance/
│   └── dutyplanner.db         # SQLite database (auto-created on first run)
│
├── templates/
│   ├── base.html              # Base template with navbar and footer
│   ├── dashboard.html         # Dashboard with overview and quick links
│   ├── soldiers.html          # Soldier list and add form
│   ├── edit_soldier.html      # Soldier edit form
│   ├── schedule.html          # View and confirm duty schedule
│   └── unavailability.html    # Manage soldier unavailability
│
└── static/
    └── style.css              # Custom CSS styling
```

## Installation & Setup

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Local Development

1. **Clone or navigate to the project**:
   ```bash
   cd duty-planner
   ```

2. **Create a virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**:
   ```bash
   python app.py
   ```

   The app will be available at `http://localhost:5000`.

   **Note**: The SQLite database (`instance/dutyplanner.db`) is automatically created on the first request if it doesn't exist.

### Database

- The database is stored in `instance/dutyplanner.db` (SQLite format).
- Tables are automatically created on the first request via the `@app.before_request` hook.
- No manual migration is needed.

## Usage

### 1. Manage Soldiers

- Go to **Soldiers** page to add, edit, or delete soldiers.
- Each soldier has:
  - **Name**: Soldier's full name
  - **Rank**: Military rank (e.g., Στρατιώτης, Δεκανέας)
  - **Role**: Type of duties they can perform (e.g., Σκοπιά, Θαλαμοφύλακας, Κουζίνα)
  - **Availability**: Toggle whether they are generally available
  - **Total Services**: Auto-tracked count of duty assignments

### 2. Track Unavailability

- Go to **Unavailability** page to mark soldiers as unavailable for specific dates.
- Useful for leave, illness, special assignments, etc.
- The fair rotation algorithm will skip unavailable soldiers when generating schedules.

### 3. Generate a Schedule

- From the **Dashboard**, click "Generate schedule for [date]".
- Or manually navigate to `/generate/YYYY-MM-DD`.
- The fair rotation algorithm will:
  1. Define required duty slots for the day
  2. For each slot, select the soldier with the lowest `total_services` count (tie-breaker: lowest ID)
  3. Only assign soldiers who are available and not marked unavailable
  4. Match soldiers to duties based on their role
  5. Prevent double-shifting (no soldier assigned twice on the same day)

### 4. View & Confirm Schedule

- Go to **Schedule** and enter a date to view that day's assignments.
- Each assignment shows the shift type, soldier name, and confirmation status.
- Click "Mark all as confirmed" to confirm all assignments for the day.

## Fair Rotation Algorithm

The core logic in `generate_schedule_for_date()`:

1. For each required duty slot (e.g., "Σκοπιά 00:00-02:00"):
2. Filter soldiers by:
   - General availability (`is_available == True`)
   - Not marked unavailable for that date
   - Compatible role for the duty type
   - Not already assigned another shift that day
3. From the filtered pool, choose the soldier with the **lowest `total_services`** count.
4. Increment that soldier's `total_services` counter.
5. Create an `Assignment` record in the database.

This ensures fair, balanced workload distribution across the unit.

## Deployment to Render

### Prerequisites

- A Render account (https://render.com)
- GitHub repository with your code

### Steps

1. **Push code to GitHub**:
   ```bash
   git init
   git add .
   git commit -m "Initial Duty Planner commit"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/duty-planner.git
   git push -u origin main
   ```

2. **Create a Render Web Service**:
   - Log in to Render dashboard
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Select the `duty-planner` branch

3. **Configure Build & Start Commands**:

   - **Build Command**:
     ```
     pip install -r requirements.txt
     ```

   - **Start Command**:
     ```
     gunicorn app:app
     ```

4. **Environment Variables**:
   - Under "Environment", set `PYTHON_VERSION` to `3.11` (or your version)
   - (Optional) Set `SECRET_KEY` for production security

5. **Deploy**:
   - Click "Create Web Service"
   - Render will automatically build and deploy your app
   - Your app will be live at `https://your-app-name.onrender.com`

### Database Persistence on Render

- Render's file system is ephemeral (resets on every deploy).
- For production, consider migrating to PostgreSQL:
  - Add a Render PostgreSQL database
  - Update `SQLALCHEMY_DATABASE_URI` in `app.py` to use PostgreSQL
  - Example: `postgresql://user:password@host:port/dbname`

For now, the SQLite database will work for testing but will reset on redeploy.

## Code Structure

### Models (`models.py`)

- **Soldier**: Represents a soldier with name, rank, role, and service count.
- **Assignment**: Links a soldier to a duty shift on a specific date.
- **Unavailability**: Marks a soldier as unavailable on a specific date.

### Routes (`app.py`)

- `GET /`: Dashboard with overview and quick links
- `GET/POST /soldiers`: List soldiers and add new ones
- `GET/POST /soldiers/<id>/edit`: Edit soldier details
- `POST /soldiers/<id>/delete`: Delete a soldier
- `GET/POST /unavailability`: Manage unavailability records
- `GET /schedule/<date>`: View schedule for a date
- `POST /schedule/<date>/confirm`: Mark assignments as confirmed
- `GET /generate/<date>`: Generate fair schedule for a date

### Templates

All templates extend `base.html`, which provides navbar, footer, and Bootstrap styling.

## Troubleshooting

### Database Issues

- **Database file not created?** Check that `instance/` directory exists and is writable.
- **Tables not created?** The app creates tables automatically on first request. Refresh the browser.
- **Want to reset the database?** Delete `instance/dutyplanner.db` and restart the app.

### Schedule Generation Not Working

- Ensure soldiers exist and are marked as available.
- Check that at least one soldier has a compatible role for each slot type.
- Review the browser console for error messages.

## Future Enhancements

- Multi-team/company support
- Custom duty slot templates per day
- REST API for external integrations
- Email notifications for assignments
- Shift history and statistics
- Advanced filtering and search

## License

This project is provided as-is for internal military unit use.

## Support

For issues or questions, review the Flask documentation at https://flask.palletsprojects.com/ or the SQLAlchemy docs at https://docs.sqlalchemy.org/.

---

**Duty Planner** – Inspired by military daily duty rotation systems. Built with Flask and SQLAlchemy.
