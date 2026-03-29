import os

# --- Render/Production Initialization ---
# Apply monkey patching ONLY on Render to avoid local Windows/MySQL conflicts
if os.environ.get('RENDER'):
    import eventlet
    eventlet.monkey_patch()

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file
from sqlalchemy.exc import IntegrityError
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import re
import uuid
from authlib.integrations.flask_client import OAuth
from flask_socketio import SocketIO, emit, join_room, leave_room
from werkzeug.middleware.proxy_fix import ProxyFix
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your_secret_key')

# Tell Flask to trust the X-Forwarded-Proto header from the proxy
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Ensure OAuth works even if the proxy reports HTTP internally
if os.environ.get('RENDER'):
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

socketio = SocketIO(app, cors_allowed_origins="*")

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = 'uploads'

# Deployment-ready DB URI (Agnostic Handler)
DATABASE_URL = os.environ.get('DATABASE_URL', 'mysql+pymysql://root:your_password@localhost/project_db')
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

from datetime import datetime, timedelta

def view_tasks(username=None):
    if not username: return "📋 Cannot find user."
    user = User.query.filter_by(username=username).first()
    if not user: return "📋 Found no user."
    tasks = Task.query.filter_by(assigned_to=user.id).all()
    if not tasks: return "📋 No tasks assigned to you."
    msg = "📋 Your tasks:<br>"
    for t in tasks:
        msg += f"- <b>{t.title}</b> ({t.status})<br>"
    return msg

def help_action():
    return "📞 For assistance, please contact our official helpline: <b>+91 7989031165</b>. We are available 24/7 to help you with ConnectX!"

def add_task():
    return "COMMAND:MODAL:ADD_TASK"

def delete_task():
    return "COMMAND:MODAL:DELETE_TASK"

def project_status():
    return "COMMAND:REDIRECT:/reports"

def exit_action():
    return "This conversation is closed. Click the chat icon to start a new conversation."

actions = {
    "view_tasks": view_tasks,
    "add_task": add_task,
    "delete_task": delete_task,
    "project_status": project_status,
    "help": help_action,
    "exit" : exit_action
}

db = SQLAlchemy(app)

oauth = OAuth(app)

google = oauth.register(
    name='google',
    client_id=os.environ.get('GOOGLE_CLIENT_ID', 'your_google_client_id'),
    client_secret=os.environ.get('GOOGLE_CLIENT_SECRET', 'your_google_client_secret'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=True)
    role = db.Column(db.String(50), nullable=False)
    google_id = db.Column(db.String(200))

class Project(db.Model):
    __tablename__ = 'projects'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150))
    description = db.Column(db.Text)
    created_by = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

class Task(db.Model):
    __tablename__ = 'tasks'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150))
    description = db.Column(db.Text)
    status = db.Column(db.String(50), default='To Do')
    priority = db.Column(db.String(50))
    deadline = db.Column(db.Date)
    
    assigned_to = db.Column(db.Integer)
    project_id = db.Column(db.Integer)
    tags = db.Column(db.String(255), nullable=True)

    created_at = db.Column(db.DateTime, server_default=db.func.now())

class File(db.Model):
    __tablename__ = 'files'

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200))
    filepath = db.Column(db.String(300))
    project_id = db.Column(db.Integer, nullable=True)
    task_id = db.Column(db.Integer, nullable=True)
    uploaded_at = db.Column(db.DateTime, server_default=db.func.now())

class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, nullable=True) # None = global chat
    sender_id = db.Column(db.Integer, nullable=False)
    text = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, server_default=db.func.now())

class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    text = db.Column(db.String(255), nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

class Activity(db.Model):
    __tablename__ = 'activities'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, nullable=True)
    action = db.Column(db.String(255), nullable=False)
    user_id = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, server_default=db.func.now())

class Subtask(db.Model):
    __tablename__ = 'subtasks'
    id = db.Column(db.Integer, primary_key=True)
    parent_task_id = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(150), nullable=False)
    is_completed = db.Column(db.Boolean, default=False)

class Meeting(db.Model):
    __tablename__ = 'meetings'
    id = db.Column(db.Integer, primary_key=True)
    meeting_id = db.Column(db.String(50), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    created_by = db.Column(db.Integer)

with app.app_context():
    db.create_all()
    try:
        db.session.execute(db.text('ALTER TABLE tasks ADD COLUMN tags VARCHAR(255)'))
    except Exception:
        db.session.rollback()
    try:
        db.session.execute(db.text('ALTER TABLE files ADD COLUMN project_id INT'))
    except Exception:
        db.session.rollback()
    try:
        db.session.execute(db.text('ALTER TABLE files ADD COLUMN task_id INT'))
    except Exception:
        db.session.rollback()
    
    # --- Auto-promote Super Admin via Env Var (Render fix for Shell access) ---
    sa_username = os.environ.get('SUPER_ADMIN_USERNAME')
    if sa_username:
        sa_user = User.query.filter_by(username=sa_username).first()
        if sa_user:
            sa_user.role = 'super_admin'
            
    db.session.commit()


# --- Socket.io Events for Meetings ---
@socketio.on('join_meeting')
def on_join_meeting(data):
    room = data['room']
    join_room(room)
    # Broadcast to others in the room that this user joined
    emit('user-joined', {'sid': request.sid, 'room': room}, room=room, include_self=False)

@socketio.on('signal')
def handle_signal(data):
    # Relay signal to specific user or room
    target_sid = data.get('to')
    if target_sid:
        emit('signal', {'sid': request.sid, 'data': data['data']}, room=target_sid)
    else:
        emit('signal', {'sid': request.sid, 'data': data['data']}, room=data['room'], include_self=False)

def cleanup_old_data():
    """Delete items older than 24 hours from Notifications, Activities, and Global Chat."""
    cutoff = datetime.now() - timedelta(hours=24)
    try:
        # 1. Notifications
        Notification.query.filter(Notification.created_at < cutoff).delete()
        # 2. Activities
        Activity.query.filter(Activity.timestamp < cutoff).delete()
        # 3. Global Chat Messages (project_id is None)
        Message.query.filter(Message.project_id == None, Message.timestamp < cutoff).delete()
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Cleanup Error: {e}")

@app.before_request
def before_request():
    # Run cleanup periodically or on every request in small/dev apps
    # For production, this should ideally be a background task (e.g. Celery)
    # but here we'll run it to keep things updated for the user.
    if request.endpoint and 'static' not in request.endpoint:
        cleanup_old_data()

@app.route('/login', methods=['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST':
        username = request.form.get("username")
        password = request.form.get("password")
        role = request.form.get("role")
        
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            # If user is super_admin, they can bypass the specific role match.
            # Otherwise, the chosen role must match the database role.
            if user.role != role and user.role != 'super_admin':
                 msg = "Invalid credentials or role mismatch"
            else:
                 session['user'] = user.username
                 session['role'] = user.role
                 if user.role in ['team_leader', 'super_admin']:
                     return redirect(url_for('tl_dashboard'))
                 else:
                     return redirect(url_for('dashboard'))
        else:
            msg = "Invalid credentials or role mismatch"



    return render_template('login.html', message=msg)

@app.route('/login/google')
def login_google():
    redirect_uri = url_for('google_callback', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/google/callback')
def google_callback():
    token = google.authorize_access_token()
    user_info = google.get('https://www.googleapis.com/oauth2/v3/userinfo').json()

    email = user_info['email']
    google_id = user_info['sub']
    name = user_info.get('name')

    user = User.query.filter_by(email=email).first()

    if not user:
        # First-time Google user: store info in session and redirect to role selection
        session['google_temp'] = {
            'email': email,
            'google_id': google_id,
            'username': name
        }
        return redirect(url_for('google_role_selection'))

    session['user'] = user.username
    session['role'] = user.role

    # Redirect based on role
    if user.role == 'super_admin' or user.role == 'team_leader':
        return redirect(url_for('tl_dashboard'))
    return redirect(url_for('dashboard'))

@app.route('/google/role-selection', methods=['GET', 'POST'])
def google_role_selection():
    if 'google_temp' not in session:
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        role = request.form.get('role')
        if role not in ['team_leader', 'team_member']:
            return "Invalid role selection", 400
            
        temp_info = session.pop('google_temp')
        
        # Ensure unique username
        base_username = temp_info['username']
        username = base_username
        counter = 1
        while User.query.filter_by(username=username).first():
            username = f"{base_username}{counter}"
            counter += 1

        new_user = User(
            username=username,
            email=temp_info['email'],
            google_id=temp_info['google_id'],
            role=role
        )
        db.session.add(new_user)
        db.session.commit()
        
        session['user'] = new_user.username
        session['role'] = new_user.role
        
        if role == 'team_leader':
            return redirect(url_for('tl_dashboard'))
        return redirect(url_for('dashboard'))
        
    return render_template('google_role.html', name=session['google_temp']['username'])


@app.route('/register', methods=['GET', 'POST'])
def register():
    msg = ''
    if request.method == 'POST':
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        cpassword = request.form.get("cpassword")
        role = request.form.get("role")
        
        email_pattern = r'^[a-zA-Z0-9._%+-]+@gmail\.com$'
        if not re.match(email_pattern, email):
            msg = "Invalid email format (must be @gmail.com)"
            return render_template('register.html', message=msg)
        
        password_pattern = r'^(?=.*[A-Za-z])(?=.*\d)(?=.*[@$!%*#?&]).{8,}$'
        if not re.match(password_pattern, password):
            msg = "Password must be 8+ chars with letters, numbers & special chars"
            return render_template('register.html', message=msg)

        if password != cpassword:
            msg = "Passwords do not match"
            return render_template('register.html', message=msg)
            
        hashed_password = generate_password_hash(password)
        try:
            new_user = User(
                username=username,
                email=email,
                password=hashed_password,
                role=role
            )
            db.session.add(new_user)
            db.session.commit()
            msg = "Registered Successfully"
            return redirect(url_for('login'))
        except IntegrityError:
            db.session.rollback()
            msg = "Username or Email already exists"

    return render_template('register.html', message=msg)

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))

    user = User.query.filter_by(username=session['user']).first()
    search_query = request.args.get('search')

    if search_query:
        projects = Project.query.filter(
            Project.title.ilike(f"%{search_query}%")
        ).all()
    else:
        projects = Project.query.all()

    tasks = Task.query.filter_by(assigned_to=user.id).all() if user else []
    activities = Activity.query.order_by(Activity.timestamp.desc()).limit(10).all()

    return render_template(
        'tm_dashboard.html',
        projects=projects,
        tasks=tasks,
        activities=activities,
        today=datetime.now().date()
    )

@app.route('/tl_dashboard')
def tl_dashboard():
    if 'user' not in session:
        return redirect(url_for('home'))

    status_filter = request.args.get('status')
    if status_filter:
        tasks = Task.query.filter_by(status=status_filter).all()
    else:
        tasks = Task.query.all()

    projects = Project.query.all()
    
    # If super_admin, show both leads and members
    if session.get('role') == 'super_admin':
        users = User.query.filter(User.role != 'super_admin').all() # don't list other super_admins (though there's only one)
    else:
        users = User.query.filter_by(role='team_member').all()
        
    activities = Activity.query.order_by(Activity.timestamp.desc()).limit(10).all()

    return render_template(
        'tl_dashboard.html',
        tasks=tasks,
        projects=projects,
        users=users,
        activities=activities,
        today=datetime.now().date(),
        is_super_admin=(session.get('role') == 'super_admin')
    )


@app.route('/members')
def members():
    if 'user' not in session:
        return redirect(url_for('home'))
    
    all_users = User.query.all()
    # Sort: team_leader first (False sorts before True in sorted)
    sorted_users = sorted(all_users, key=lambda x: x.role != 'team_leader')
    
    return render_template('members.html', members=sorted_users)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route("/chat-action", methods=["POST"])
def chat_action():
    data = request.get_json()
    action = data.get("action")
    role = session.get('role')
    
    # 1. Standard Button Actions
    func = actions.get(action)
    if func:
        # Role-based restriction for sensitive button actions
        if role == 'team_member' and action in ['add_task', 'delete_task']:
            return jsonify({"response": "🚫 I'm sorry, only Team Leaders can perform this action."})
            
        if action == 'view_tasks':
            if role == 'team_leader':
                return jsonify({"response": "COMMAND:MODAL:VIEW_PROJECT_TASKS"})
            response = func(session.get('user'))
        else:
            response = func()
        return jsonify({"response": response})

    # 2. Intelligent Text Parsing
    text = str(action).lower().strip()
    
    if "show my tasks" in text or "view tasks" in text:
        if role == 'team_leader':
            return jsonify({"response": "COMMAND:MODAL:VIEW_PROJECT_TASKS"})
        return jsonify({"response": view_tasks(session.get('user'))})
    
    # Text-based creation/deletion also requires role check
    if "create task" in text or "add task" in text:
        if role == 'team_member':
             return jsonify({"response": "🚫 Access Denied: Only Team Leaders can create tasks."})
        # If lead, trigger the modal instead of parsing text for now (user requested popups)
        return jsonify({"response": "COMMAND:MODAL:ADD_TASK"})
    
    if "delete task" in text:
        if role == 'team_member':
             return jsonify({"response": "🚫 Access Denied: Only Team Leaders can delete tasks."})
        return jsonify({"response": "COMMAND:MODAL:DELETE_TASK"})

    if "project status" in text or "report" in text:
        return jsonify({"response": "COMMAND:REDIRECT:/reports"})
        
    if "help" in text:
        return jsonify({"response": help_action()})
        
    return jsonify({"response": "🤖 I didn't quite catch that. Try 'help'."})

# --- New Features Routes ---

@app.route('/create_project', methods=['POST'])
def create_project():
    title = request.form.get('project_name') or request.form.get('title')
    description = request.form.get('description', '')

    user = User.query.filter_by(username=session.get('user')).first()
    created_by_id = user.id if user else 1

    project = Project(
        title=title,
        description=description,
        created_by=created_by_id
    )

    db.session.add(project)
    db.session.commit()

    if user:
        act = Activity(project_id=project.id, action=f"Project '{title}' created", user_id=user.id)
        db.session.add(act)
        db.session.commit()

    if session.get('role') == 'team_leader':
        # Check if form was submitted from workspace/project view
        if request.form.get('redirect_to'):
            return redirect(request.form.get('redirect_to'))
        return redirect(url_for('tl_dashboard'))
    return redirect(url_for('dashboard'))

@app.route('/delete_project/<int:project_id>')
def delete_project(project_id):
    if session.get('role') != 'team_leader':
        return redirect(url_for('dashboard'))
    
    project = Project.query.get(project_id)
    if project:
        # Delete associated tasks
        Task.query.filter_by(project_id=project.id).delete()
        # Delete project
        db.session.delete(project)
        db.session.commit()
        
        # Log activity
        user = User.query.filter_by(username=session.get('user')).first()
        if user:
            act = Activity(action=f"Deleted project ID {project_id}", user_id=user.id)
            db.session.add(act)
            db.session.commit()

    return redirect(url_for('workspace'))

@app.route('/create_task', methods=['POST'])
def create_task():
    assigned_to = request.form.get('assigned_to')
    # Handle empty string or 'None' as actual None for DB
    if assigned_to == "" or assigned_to == "None" or not assigned_to:
        assigned_to = None

    task = Task(
        title=request.form.get('title'),
        description=request.form.get('description'),
        priority=request.form.get('priority'),
        deadline=request.form.get('deadline'),
        assigned_to=assigned_to,
        project_id=request.form.get('project_id')
    )

    db.session.add(task)
    db.session.commit()
    
    user = User.query.filter_by(username=session.get('user')).first()
    if user:
        act = Activity(project_id=task.project_id, action=f"Task '{task.title}' created", user_id=user.id)
        db.session.add(act)
        # Only notify if assigned
        if task.assigned_to:
            notif = Notification(user_id=task.assigned_to, text=f"New task assigned: {task.title}")
            db.session.add(notif)
        db.session.commit()

    # Redirection logic
    if request.form.get('redirect_to'):
        return redirect(request.form.get('redirect_to'))
    return redirect(request.referrer or url_for('tl_dashboard'))

@app.route('/update_task_status/<int:id>/<status>')
def update_task_status(id, status):
    task = Task.query.get(id)
    status = status.replace("_", " ")
    task.status = status
    db.session.commit()
    
    user = User.query.filter_by(username=session.get('user')).first()
    if user:
        act = Activity(project_id=task.project_id, action=f"Task '{task.title}' status changed to {status}", user_id=user.id)
        db.session.add(act)
        if task.assigned_to and task.assigned_to != user.id:
            notif = Notification(user_id=task.assigned_to, text=f"Task '{task.title}' status updated to {status}")
            db.session.add(notif)
        db.session.commit()
    return redirect(request.referrer or url_for('dashboard'))

@app.route('/edit_task/<int:id>', methods=['GET', 'POST'])
def edit_task(id):
    if session.get('role') != 'team_leader':
        return "Unauthorized", 403
    task = Task.query.get(id)

    if request.method == 'POST':
        task.title = request.form.get('title')
        task.description = request.form.get('description')
        task.priority = request.form.get('priority')
        task.deadline = request.form.get('deadline')

        db.session.commit()
        if task.project_id:
            return redirect(url_for('project_tasks', project_id=task.project_id))
        return redirect(url_for('tl_dashboard'))

    return render_template('edit_task.html', task=task)

@app.route('/assign_task/<int:id>', methods=['POST'])
def assign_task(id):
    if session.get('role') != 'team_leader':
        return "Unauthorized", 403
    
    task = Task.query.get(id)
    if not task:
        return "Task not found", 404
        
    user_id = request.form.get('user_id')
    if user_id:
        task.assigned_to = int(user_id)
        db.session.commit()
        
        # Log activity
        user = User.query.filter_by(username=session.get('user')).first()
        assigned_user = User.query.get(user_id)
        if user and assigned_user:
            act = Activity(project_id=task.project_id, action=f"Assigned task '{task.title}' to {assigned_user.username}", user_id=user.id)
            db.session.add(act)
            # Notification for assigned user
            notif = Notification(user_id=assigned_user.id, text=f"You have been assigned to task: '{task.title}'")
            db.session.add(notif)
            db.session.commit()
            
    return redirect(request.referrer or url_for('project_tasks', project_id=task.project_id))

@app.route('/delete_task/<int:id>')
def delete_task(id):
    if session.get('role') not in ['team_leader', 'super_admin']:
        return "Unauthorized", 403
    task = Task.query.get(id)
    if not task:
        return "Task not found", 404
    project_id = task.project_id
    db.session.delete(task)
    db.session.commit()
    if project_id:
        return redirect(url_for('project_tasks', project_id=project_id))
    return redirect(url_for('tl_dashboard'))

@app.route('/delete_user/<int:id>')
def delete_user(id):
    if session.get('role') != 'super_admin':
        return "Unauthorized", 403
        
    user = User.query.get(id)
    if not user:
        return "User not found", 404
        
    # Set assigned tasks to unassigned
    Task.query.filter_by(assigned_to=user.id).update({'assigned_to': None})
    
    db.session.delete(user)
    db.session.commit()
    
    return redirect(url_for('tl_dashboard'))


@app.route('/workspace')
def workspace():
    if 'user' not in session:
        return redirect(url_for('home'))

    projects = Project.query.all()
    
    return render_template('workspace.html', projects=projects)

@app.route('/workspace/project/<int:project_id>')
def project_tasks(project_id):
    if 'user' not in session:
        return redirect(url_for('home'))
    
    project = Project.query.get_or_404(project_id)
    tasks = Task.query.filter_by(project_id=project_id).all()
    # Only allow team members to be assigned to tasks
    members = User.query.filter_by(role='team_member').all()
    # Keep user_map for display purposes (mapping ID to Name)
    all_users = User.query.all()
    user_map = {u.id: u.username for u in all_users}
    
    return render_template('project_tasks.html', project=project, tasks=tasks, users=members, user_map=user_map)

@app.route('/notifications/clear', methods=['POST'])
def clear_notifications():
    if 'user' not in session:
        return redirect(url_for('home'))
    user = User.query.filter_by(username=session['user']).first()
    if user:
        Notification.query.filter_by(user_id=user.id).delete()
        db.session.commit()
    return redirect(url_for('notifications'))

@app.route('/activities/clear', methods=['POST'])
def clear_activities():
    if session.get('role') != 'team_leader':
        return "Unauthorized", 403
    Activity.query.delete()
    db.session.commit()
    return redirect(url_for('tl_dashboard'))

@app.route('/chat/global/clear', methods=['POST'])
def clear_global_chat():
    if session.get('role') != 'team_leader':
        return "Unauthorized", 403
    # Clear only messages where project_id is None (global chat)
    Message.query.filter_by(project_id=None).delete()
    db.session.commit()
    return redirect(url_for('global_chat'))

@app.route('/upload_file', methods=['POST'])
def upload_file():
    file = request.files['file']

    if file:
        filepath = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(filepath)

        new_file = File(filename=file.filename, filepath=filepath)
        db.session.add(new_file)
        db.session.commit()
        msg = "File uploaded successfully"
    else:
        msg = "No file selected"

    return render_template('upload_file.html', msg=msg)  

@app.route('/upload_page')
def upload_page():
    return render_template('upload_file.html')

@app.route('/view_files')
def view_files():
    files = File.query.all()
    return render_template('view_files.html', files=files)
    
@app.route('/view_file/<int:id>')
def view_file(id):
    file = db.session.get(File, id)

    if file:
        filepath = os.path.abspath(file.filepath)
        if os.path.exists(filepath):
            return send_file(filepath)
        else:
            return f"File not found on disk: {filepath}"
    
    return "File not found in DB"

@app.route('/delete_file/<int:id>')
def delete_file(id):
    if session.get('role') != 'team_leader':
        return "Unauthorized", 403
    file = File.query.get(id)

    if file:
        if os.path.exists(file.filepath):
            os.remove(file.filepath)

        db.session.delete(file)
        db.session.commit()

    return redirect(url_for('view_files'))

@app.route('/global_chat')
def global_chat():
    if 'user' not in session:
        return redirect(url_for('login'))
    user = User.query.filter_by(username=session['user']).first()
    messages = Message.query.filter_by(project_id=None).order_by(Message.timestamp.asc()).all()
    msg_data = []
    for m in messages:
        sender = db.session.get(User, m.sender_id)
        msg_data.append({'sender': sender.username if sender else 'Unknown', 'text': m.text, 'timestamp': m.timestamp.strftime('%H:%M %p') if m.timestamp else ''})
    return render_template('global_chat.html', messages=msg_data, current_user=user.username)

@socketio.on('join')
def on_join(data):
    room = data['room']
    join_room(room)

@socketio.on('send_message')
def on_send_message(data):
    room = data['room']
    text = data['text']
    user = User.query.filter_by(username=session['user']).first()
    if not user:
        return
    project_id = data.get('project_id', None)
    
    msg = Message(project_id=project_id, sender_id=user.id, text=text)
    db.session.add(msg)
    db.session.commit()

    # Handle @mention notifications
    import re as _re
    mentioned_names = _re.findall(r'@(\w+)', text)
    for name in mentioned_names:
        mentioned_user = User.query.filter_by(username=name).first()
        if mentioned_user and mentioned_user.id != user.id:
            notif = Notification(
                user_id=mentioned_user.id,
                text=f"{user.username} mentioned you in Global Chat: \"{text[:80]}{'...' if len(text)>80 else ''}\""
            )
            db.session.add(notif)
    db.session.commit()
    
    emit('receive_message', {
        'sender': user.username,
        'text': text,
        'timestamp': msg.timestamp.strftime('%H:%M %p') if msg.timestamp else datetime.now().strftime('%H:%M %p')
    }, room=room)

@app.context_processor
def inject_notifications():
    if 'user' in session:
        user = User.query.filter_by(username=session['user']).first()
        if user:
            notifs = Notification.query.filter_by(user_id=user.id, is_read=False).order_by(Notification.created_at.desc()).limit(5).all()
            return dict(user_notifications=notifs)
    return dict(user_notifications=[])

@app.route('/read_notification/<int:id>')
def read_notification(id):
    notif = Notification.query.get(id)
    if notif:
        notif.is_read = True
        db.session.commit()
    return redirect(request.referrer or url_for('dashboard'))

@app.route('/notifications')
def notifications_page():
    if 'user' not in session:
        return redirect(url_for('login'))
    user = User.query.filter_by(username=session['user']).first()
    if not user:
        return redirect(url_for('login'))
    notifications = Notification.query.filter_by(user_id=user.id).order_by(Notification.created_at.desc()).all()
    return render_template('notifications.html', notifications=notifications)

@app.route('/mark_all_notifications_read')
def mark_all_notifications_read():
    if 'user' not in session:
        return redirect(url_for('login'))
    user = User.query.filter_by(username=session['user']).first()
    if user:
        Notification.query.filter_by(user_id=user.id, is_read=False).update({'is_read': True})
        db.session.commit()
    return redirect(url_for('notifications_page'))

@app.route('/users_list')
def users_list():
    """API endpoint for @mention autocomplete in global chat."""
    if 'user' not in session:
        return jsonify([])
    users = User.query.with_entities(User.id, User.username).all()
    return jsonify([{'id': u.id, 'username': u.username} for u in users])

@app.route('/reports')
def reports():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('reports.html')

@app.route('/api/reports/data')
def reports_data():
    if 'user' not in session:
        return jsonify({"error": "Unauthorized"}), 403

    # 1. Project Progress
    projects = Project.query.all()
    project_metrics = []
    for p in projects:
        total_tasks = Task.query.filter_by(project_id=p.id).count()
        done_tasks = Task.query.filter_by(project_id=p.id, status='Done').count()
        progress = (done_tasks / total_tasks * 100) if total_tasks > 0 else 0
        project_metrics.append({
            "id": p.id,
            "title": p.title,
            "progress": round(progress, 1),
            "total": total_tasks,
            "done": done_tasks
        })

    # 2. Global Status Distribution
    status_counts = {
        "To Do": Task.query.filter_by(status='To Do').count(),
        "In Progress": Task.query.filter_by(status='In Progress').count(),
        "Done": Task.query.filter_by(status='Done').count()
    }

    # 3. Team Workload
    users = User.query.filter_by(role='team_member').all()
    workload = []
    for u in users:
        task_count = Task.query.filter_by(assigned_to=u.id).count()
        workload.append({
            "username": u.username,
            "count": task_count
        })

    # 4. Summary Stats
    summary = {
        "total_projects": len(projects),
        "total_tasks": Task.query.count(),
        "total_members": len(users),
        "avg_completion": round(sum(p['progress'] for p in project_metrics) / len(projects), 1) if projects else 0
    }

    return jsonify({
        "projects": project_metrics,
        "status_distribution": status_counts,
        "workload": workload,
        "summary": summary
    })

@app.route('/api/project/<int:project_id>/tasks')
def get_project_tasks(project_id):
    if 'user' not in session:
        return jsonify({"error": "Unauthorized"}), 403
    
    tasks = Task.query.filter_by(project_id=project_id).all()
    # Map user IDs to usernames for readability
    all_users = {u.id: u.username for u in User.query.all()}
    
    task_list = [{
        "id": t.id,
        "title": t.title,
        "status": t.status,
        "assigned_to": all_users.get(t.assigned_to, "Unassigned")
    } for t in tasks]
    
    return jsonify(task_list)

# --- Meeting Routes ---
@app.route('/meetings')
def meetings_dashboard():
    if 'user' not in session:
        return redirect(url_for('home'))
    
    # Get recent meetings
    recent_meetings = Meeting.query.order_by(Meeting.created_at.desc()).limit(5).all()
    user = User.query.filter_by(username=session['user']).first()
    
    return render_template('meetings.html', meetings=recent_meetings, user=user)

@app.route('/create_meeting', methods=['POST'])
def create_meeting():
    if 'user' not in session:
        return redirect(url_for('home'))
        
    if session.get('role') not in ['team_leader', 'super_admin']:
        return "Only Team Leaders can create meetings", 403
        
    user = User.query.filter_by(username=session['user']).first()
    # Generate random 9-char ID
    new_meeting_id = str(uuid.uuid4())[:9]
    new_meeting = Meeting(meeting_id=new_meeting_id, created_by=user.id)
    
    db.session.add(new_meeting)
    db.session.commit()
    
    return redirect(url_for('meeting_room', room_id=new_meeting_id))


@app.route('/join_meeting', methods=['POST'])
def join_meeting():
    if 'user' not in session:
        return redirect(url_for('home'))
        
    room_id = request.form.get('room_id', '').strip()
    if not room_id:
        return redirect(url_for('meetings_dashboard'))
        
    meeting_exists = Meeting.query.filter_by(meeting_id=room_id).first()
    if meeting_exists:
        return redirect(url_for('meeting_room', room_id=room_id))
        
    return redirect(url_for('meetings_dashboard'))

@app.route('/meeting/<room_id>')
def meeting_room(room_id):
    if 'user' not in session:
        return redirect(url_for('home'))
        
    meeting_exists = Meeting.query.filter_by(meeting_id=room_id).first()
    if not meeting_exists:
        return redirect(url_for('meetings_dashboard'))
        
    return render_template('meeting_room.html', room_id=room_id)

if __name__ == '__main__':
    socketio.run(app, debug=True)