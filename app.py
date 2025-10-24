"""
Duty Planner - Flask web application for military unit duty rotation.
Manages soldiers, assignments, and unavailability with a fair rotation algorithm.
"""

import os
from datetime import datetime, date, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash
from models import db, Soldier, Assignment, Unavailability

app = Flask(__name__)

# Configuration
basedir = os.path.abspath(os.path.dirname(__file__))
instance_path = os.path.join(basedir, 'instance')
os.makedirs(instance_path, exist_ok=True)

app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(instance_path, "dutyplanner.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Initialize database
db.init_app(app)


@app.before_request
def create_tables():
    """Create database tables if they don't exist."""
    if not hasattr(app, 'db_initialized'):
        with app.app_context():
            db.create_all()
            app.db_initialized = True


@app.context_processor
def inject_now():
    """Make datetime available in all templates."""
    return {
        'now': datetime.now(),
        'today': date.today()
    }


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def generate_schedule_for_date(target_date_str):
    """
    Generate a fair schedule for the given date.
    
    Algorithm:
    1. Define required duty slots for the day
    2. For each slot:
       - Build a candidate pool of soldiers that:
         * are available (is_available == True)
         * are not unavailable on that date
         * have a compatible role for the shift
         * haven't already been assigned another shift that day
       - Choose the soldier with the LOWEST total_services (tie-breaker: lowest id)
       - Create Assignment and increment total_services
    
    Behavior on duplicate: If assignments already exist for this date, we DELETE
    them first and regenerate. This allows rescheduling without manual cleanup.
    
    Args:
        target_date_str: Date string in format "YYYY-MM-DD"
    """
    try:
        target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
    except ValueError:
        flash(f"Invalid date format: {target_date_str}", "danger")
        return False
    
    # Define required duty slots for the day
    slots = [
        "Σκοπιά 00:00-02:00",
        "Σκοπιά 02:00-04:00",
        "Σκοπιά 04:00-06:00",
        "Θαλαμοφύλακας Ημέρας",
        "Κουζίνα Πρωί"
    ]
    
    # Check if assignments already exist for this date
    existing_assignments = Assignment.query.filter_by(date=target_date).all()
    if existing_assignments:
        # Delete existing assignments to allow regeneration
        for assignment in existing_assignments:
            db.session.delete(assignment)
        db.session.commit()
    
    # Get all unavailability records for that date
    unavailable_soldier_ids = set(
        u.soldier_id for u in Unavailability.query.filter_by(date=target_date).all()
    )
    
    # Get all soldiers
    all_soldiers = Soldier.query.all()
    
    # Track soldiers already assigned on this date (in-memory)
    already_assigned_today = set()
    
    # For each slot, assign the best available soldier
    for shift_type in slots:
        # Build candidate pool
        candidates = []
        for soldier in all_soldiers:
            # Check all conditions
            if not soldier.is_available:
                continue
            if soldier.id in unavailable_soldier_ids:
                continue
            if soldier.id in already_assigned_today:
                continue
            
            # Check role compatibility: if slot contains role keyword, soldier must have it
            # Simple substring matching
            role_keywords = ["Σκοπιά", "Θαλαμοφύλακας", "Κουζίνα"]
            shift_has_keyword = False
            soldier_has_matching_role = False
            
            for keyword in role_keywords:
                if keyword in shift_type:
                    shift_has_keyword = True
                    if keyword in soldier.role:
                        soldier_has_matching_role = True
                    break
            
            # If shift has a keyword requirement and soldier doesn't match, skip
            if shift_has_keyword and not soldier_has_matching_role:
                continue
            
            candidates.append(soldier)
        
        # Choose the best candidate: lowest total_services, then lowest id
        if candidates:
            best_soldier = min(candidates, key=lambda s: (s.total_services, s.id))
            
            # Create assignment
            assignment = Assignment(
                soldier_id=best_soldier.id,
                date=target_date,
                shift_type=shift_type,
                confirmed=False
            )
            db.session.add(assignment)
            
            # Increment total_services for fair rotation
            best_soldier.total_services += 1
            db.session.add(best_soldier)
            
            # Mark as assigned today
            already_assigned_today.add(best_soldier.id)
    
    db.session.commit()
    return True


# ============================================================================
# ROUTES
# ============================================================================

@app.route('/')
def dashboard():
    """Dashboard: show overview and quick links."""
    total_soldiers = Soldier.query.count()
    today = date.today()
    tomorrow = today + timedelta(days=1)
    
    return render_template('dashboard.html',
                           total_soldiers=total_soldiers,
                           today=today,
                           tomorrow=tomorrow)


@app.route('/soldiers', methods=['GET', 'POST'])
def soldiers():
    """List all soldiers and allow adding new ones."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        rank = request.form.get('rank', '').strip()
        role = request.form.get('role', '').strip()
        is_available = request.form.get('is_available') == 'on'
        
        if name and role:
            soldier = Soldier(name=name, rank=rank, role=role, is_available=is_available)
            db.session.add(soldier)
            db.session.commit()
            flash(f"Soldier {name} added successfully!", "success")
            return redirect(url_for('soldiers'))
        else:
            flash("Name and role are required.", "danger")
    
    all_soldiers = Soldier.query.order_by(Soldier.name).all()
    return render_template('soldiers.html', soldiers=all_soldiers)


@app.route('/soldiers/<int:soldier_id>/edit', methods=['GET', 'POST'])
def edit_soldier(soldier_id):
    """Edit a soldier's details."""
    soldier = Soldier.query.get_or_404(soldier_id)
    
    if request.method == 'POST':
        soldier.rank = request.form.get('rank', '').strip()
        soldier.role = request.form.get('role', '').strip()
        soldier.is_available = request.form.get('is_available') == 'on'
        
        if soldier.role:
            db.session.commit()
            flash(f"Soldier {soldier.name} updated successfully!", "success")
            return redirect(url_for('soldiers'))
        else:
            flash("Role is required.", "danger")
    
    return render_template('edit_soldier.html', soldier=soldier)


@app.route('/soldiers/<int:soldier_id>/delete', methods=['POST'])
def delete_soldier(soldier_id):
    """Delete a soldier."""
    soldier = Soldier.query.get_or_404(soldier_id)
    name = soldier.name
    
    db.session.delete(soldier)
    db.session.commit()
    
    flash(f"Soldier {name} deleted successfully!", "success")
    return redirect(url_for('soldiers'))


@app.route('/unavailability', methods=['GET', 'POST'])
def unavailability():
    """Show and manage unavailability records."""
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add':
            soldier_id = request.form.get('soldier_id', type=int)
            unavail_date = request.form.get('date', '').strip()
            reason = request.form.get('reason', '').strip()
            
            if soldier_id and unavail_date and reason:
                try:
                    unavail_date_obj = datetime.strptime(unavail_date, "%Y-%m-%d").date()
                    unavail = Unavailability(
                        soldier_id=soldier_id,
                        date=unavail_date_obj,
                        reason=reason
                    )
                    db.session.add(unavail)
                    db.session.commit()
                    flash("Unavailability record added successfully!", "success")
                except ValueError:
                    flash("Invalid date format.", "danger")
            else:
                flash("Please fill in all fields.", "danger")
        
        elif action == 'delete':
            unavail_id = request.form.get('unavail_id', type=int)
            unavail = Unavailability.query.get(unavail_id)
            if unavail:
                db.session.delete(unavail)
                db.session.commit()
                flash("Unavailability record deleted.", "success")
        
        return redirect(url_for('unavailability'))
    
    # Show future or today's unavailability records
    today = date.today()
    records = Unavailability.query.filter(Unavailability.date >= today).order_by(Unavailability.date).all()
    soldiers = Soldier.query.order_by(Soldier.name).all()
    
    return render_template('unavailability.html', records=records, soldiers=soldiers)


@app.route('/schedule/<date_str>')
def schedule(date_str):
    """Display the schedule for a specific date."""
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        flash("Invalid date format.", "danger")
        return redirect(url_for('dashboard'))
    
    assignments = Assignment.query.filter_by(date=target_date).order_by(Assignment.id).all()
    
    return render_template('schedule.html', date=target_date, assignments=assignments)


@app.route('/schedule/<date_str>/confirm', methods=['POST'])
def confirm_schedule(date_str):
    """Mark all assignments for a date as confirmed."""
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        flash("Invalid date format.", "danger")
        return redirect(url_for('dashboard'))
    
    assignments = Assignment.query.filter_by(date=target_date).all()
    for assignment in assignments:
        assignment.confirmed = True
    db.session.commit()
    
    flash(f"All assignments for {target_date} confirmed!", "success")
    return redirect(url_for('schedule', date_str=date_str))


@app.route('/generate/<date_str>', methods=['GET', 'POST'])
def generate(date_str):
    """Generate a schedule for the given date using the fair rotation algorithm."""
    if generate_schedule_for_date(date_str):
        flash(f"Schedule generated for {date_str}!", "success")
    else:
        flash(f"Failed to generate schedule for {date_str}.", "danger")
    
    return redirect(url_for('schedule', date_str=date_str))


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return render_template('base.html'), 404


if __name__ == '__main__':
    app.run(debug=True)
