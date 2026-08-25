"""
Authentification des utilisateurs
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db, login_manager
from app.models import Stagiaire
import re

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@login_manager.user_loader
def load_user(user_id):
    return Stagiaire.query.get(int(user_id))

def is_valid_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Inscription des nouveaux stagiaires"""
    if current_user.is_authenticated:
        return redirect(url_for('routes.dashboard'))
    
    if request.method == 'POST':
        nom = request.form.get('nom', '').strip()
        prenom = request.form.get('prenom', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        telephone = request.form.get('telephone', '').strip()
        adresse = request.form.get('adresse', '').strip()
        genre = request.form.get('genre', 'M.')
        duree_stage = request.form.get('duree_stage', 3)
        
        ecole = request.form.get('ecole', '').strip()
        niveau_etude = request.form.get('niveau_etude', '').strip()
        telephone_parents = request.form.get('telephone_parents', '').strip()
        
        if not all([nom, prenom, email, password, ecole, niveau_etude, telephone_parents]):
            flash('❌ Tous les champs sont obligatoires', 'danger')
            return render_template('register.html')
        
        if not is_valid_email(email):
            flash('❌ Email invalide', 'danger')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('❌ Les mots de passe ne correspondent pas', 'danger')
            return render_template('register.html')
        
        if len(password) < 4:
            flash('❌ Le mot de passe doit contenir au moins 4 caractères', 'danger')
            return render_template('register.html')
        
        if Stagiaire.query.filter_by(email=email).first():
            flash('❌ Cet email est déjà utilisé', 'danger')
            return render_template('register.html')
        
        stagiaire = Stagiaire(
            nom=nom,
            prenom=prenom,
            email=email,
            genre=genre,
            telephone=telephone,
            adresse=adresse,
            statut='en_attente',
            matricule=None,
            duree_stage_mois=int(duree_stage),
            ecole=ecole,
            niveau_etude=niveau_etude,
            telephone_parents=telephone_parents
        )
        stagiaire.set_password(password)
        
        db.session.add(stagiaire)
        db.session.commit()
        
        flash('✅ Compte créé avec succès ! Connectez-vous pour déposer vos dossiers.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('routes.dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        stagiaire = Stagiaire.query.filter_by(email=email).first()
        
        if stagiaire and stagiaire.check_password(password):
            login_user(stagiaire)
            session['stagiaire_id'] = stagiaire.id
            session['stagiaire_nom'] = f"{stagiaire.prenom} {stagiaire.nom}"
            return redirect(url_for('routes.dashboard'))
        else:
            flash('❌ Email ou mot de passe incorrect', 'danger')
    
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    flash('✅ Vous êtes déconnecté', 'success')
    return redirect(url_for('auth.login'))

@auth_bp.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form.get('password')
        # Changez '123456' par un mot de passe plus sécurisé
        if password == '123456':  # Mot de passe admin
            session['admin_logged_in'] = True
            return redirect(url_for('admin.dashboard'))
        else:
            flash('❌ Mot de passe incorrect', 'danger')
    
    return render_template('admin_login.html')
