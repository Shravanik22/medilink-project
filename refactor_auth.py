import re

with open('app.py', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. replace login_required
old_login_req = '''def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to continue.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated'''

new_login_req = '''def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not any(k in session for k in ['patient_id', 'chemist_id', 'admin_id']):
            flash('Please login to continue.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated'''
text = text.replace(old_login_req, new_login_req)

# 2. replace role_required
old_role_req = '''def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('login'))
            if session.get('role') not in roles:
                flash('Access denied.', 'error')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated
    return decorator'''

new_role_req = '''def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            role_found = False
            for role in roles:
                if f'{role}_id' in session:
                    role_found = True
                    break
            if not role_found:
                flash('Access denied.', 'error')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated
    return decorator'''
text = text.replace(old_role_req, new_role_req)

# 3. replace login
old_login = '''            if user and check_password_hash(user['password'], pw):
                session['user_id'] = user['id']
                session['name']    = user['name']
                session['role']    = user['role']
                session['email']   = user['email']
                return jsonify({'success': True, 'redirect': url_for('dashboard')})'''

new_login = '''            if user and check_password_hash(user['password'], pw):
                r = user['role']
                session[f'{r}_id'] = user['id']
                session[f'{r}_name'] = user['name']
                session[f'{r}_email'] = user['email']
                # Don't set a generic role, as they can have multiple.
                return jsonify({'success': True, 'redirect': url_for('dashboard')})'''
text = text.replace(old_login, new_login)

# 4. replace index and dashboard
text = re.sub(
    r'''@app\.route\('/'\)\ndef index\(\):\n    if 'user_id' in session:\n        return redirect\(url_for\('dashboard'\)\)''',
    '''@app.route('/')\ndef index():\n    if any(k in session for k in ['patient_id', 'chemist_id', 'admin_id']):\n        return redirect(url_for('dashboard'))''',
    text
)

old_dashboard = '''@app.route('/dashboard')
@login_required
def dashboard():
    role = session.get('role')
    if role == 'patient':
        return redirect(url_for('patient_dashboard'))
    elif role == 'chemist':
        return redirect(url_for('chemist_dashboard'))
    elif role == 'admin':
        return redirect(url_for('admin_dashboard'))
    return redirect(url_for('logout'))'''

new_dashboard = '''@app.route('/dashboard')
@login_required
def dashboard():
    # If they hit generic dashboard, route them to whatever session they have.
    # If multiple, prioritize patient -> chemist -> admin
    if 'patient_id' in session: return redirect(url_for('patient_dashboard'))
    if 'chemist_id' in session: return redirect(url_for('chemist_dashboard'))
    if 'admin_id' in session: return redirect(url_for('admin_dashboard'))
    return redirect(url_for('logout'))'''
text = text.replace(old_dashboard, new_dashboard)

old_logout = '''@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))'''

new_logout = '''@app.route('/logout')
def logout():
    role = request.args.get('role')
    if role and f'{role}_id' in session:
        session.pop(f'{role}_id', None)
        session.pop(f'{role}_name', None)
        session.pop(f'{role}_email', None)
    else:
        session.clear() # fallback clears everything
    return redirect(url_for('index'))'''
text = text.replace(old_logout, new_logout)

# 5. Route by Route session['user_id'] replacements

# Patient routes: replace uid = session['user_id'] with uid = session['patient_id']
# and session['user_id'] with session['patient_id'] inside patient logic
for func in ['patient_dashboard', 'upload_prescription', 'upload_report', 'health_metrics', 'search_medicines', 'patient_orders']:
    # simple replace if it's explicitly in the function scope
    pass # we'll use a more targeted replacement below

# The file contains blocks of routes, we can just replace session['user_id'] based on route decorators.
# Let's just do text replacements for specific known lines.
text = text.replace("def patient_dashboard():\n    uid = session['user_id']", "def patient_dashboard():\n    uid = session['patient_id']")
text = text.replace("uid = session.get('patient_id') or session['user_id']", "uid = session['patient_id']")
text = text.replace("uploaded_at DESC\",\n                (session['user_id'],))", "uploaded_at DESC\",\n                (session['patient_id'],))")
text = text.replace("def patient_orders():\n    uid = session['user_id']", "def patient_orders():\n    uid = session['patient_id']")

# Upload prescription
text = text.replace("uid = session['user_id']", "uid = session['patient_id']", 1)  # We will manually fix `upload_prescription` which has `uid   = session['user_id']`
text = text.replace("uid   = session['user_id']", "uid   = session['patient_id']")

# For chemist routes
text = text.replace("def chemist_dashboard():\n    uid = session['user_id']", "def chemist_dashboard():\n    uid = session['chemist_id']")
text = text.replace("def chemist_inventory():\n    uid = session['user_id']", "def chemist_inventory():\n    uid = session['chemist_id']")
text = text.replace("def chemist_prescriptions():\n    uid = session['user_id']", "def chemist_prescriptions():\n    uid = session['chemist_id']")
text = text.replace("def chemist_orders():\n    uid = session['user_id']", "def chemist_orders():\n    uid = session['chemist_id']")

# Admin Routes
text = text.replace("def admin_dashboard():\n    uid = session['user_id']", "def admin_dashboard():\n    uid = session['admin_id']")

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("done")
