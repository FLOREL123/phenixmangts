"""
Authentification des utilisateurs
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db, login_manager
from app.models import AdminCredential, Stagiaire
from hmac import compare_digest
from sqlalchemy.exc import SQLAlchemyError
import re

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@login_manager.user_loader
def load_user(user_id):
    try:
        return Stagiaire.query.get(int(user_id))
    except (TypeError, ValueError):
        return None

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
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        telephone = request.form.get('telephone', '').strip()
        adresse = request.form.get('adresse', '').strip()
        genre = request.form.get('genre', 'M.')
        duree_stage = request.form.get('duree_stage', '3')
        
        # NOUVEAUX CHAMPS OBLIGATOIRES
        ecole = request.form.get('ecole', '').strip()
        niveau_etude = request.form.get('niveau_etude', '').strip()
        telephone_parents = request.form.get('telephone_parents', '').strip()
        
        # Validation - Tous les champs sont obligatoires
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

        try:
            duree_stage = int(duree_stage)
        except (TypeError, ValueError):
            flash('❌ Durée de stage invalide', 'danger')
            return render_template('register.html')
        if duree_stage not in {1, 2, 3, 4, 5, 6, 12}:
            flash('❌ Durée de stage invalide', 'danger')
            return render_template('register.html')
        
        try:
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
                duree_stage_mois=duree_stage,
                ecole=ecole,
                niveau_etude=niveau_etude,
                telephone_parents=telephone_parents
            )
            stagiaire.set_password(password)

            db.session.add(stagiaire)
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            current_app.logger.exception('Erreur lors de la création du compte')
            flash('❌ Impossible de créer le compte pour le moment. Vérifiez la configuration de la base de données.', 'danger')
            return render_template('register.html')
        
        flash('✅ Compte créé avec succès ! Connectez-vous pour déposer vos dossiers.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('routes.dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        
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
        password = request.form.get('password', '')
        credential = AdminCredential.query.first()
        admin_password = current_app.config.get('ADMIN_PASSWORD')
        password_valid = credential.check_password(password) if credential else (
            admin_password and compare_digest(password, admin_password))
        if password_valid:
            session['admin_logged_in'] = True
            return redirect(url_for('admin.dashboard'))
        else:
            flash('❌ Mot de passe incorrect', 'danger')
    
    return render_template('admin_login.html')

@auth_bp.route('/admin/forgot-password', methods=['GET', 'POST'])
def admin_forgot_password():
    if request.method == 'POST':
        answer = request.form.get('answer', '').strip().casefold()
        expected_answer = 'jaune'
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not compare_digest(answer, expected_answer):
            flash('❌ Réponse incorrecte. Le mot de passe ne peut pas être modifié.', 'danger')
        elif len(new_password) < 8:
            flash('❌ Le nouveau mot de passe doit contenir au moins 8 caractères.', 'danger')
        elif new_password != confirm_password:
            flash('❌ Les mots de passe ne correspondent pas.', 'danger')
        else:
            credential = AdminCredential.query.first()
            if credential is None:
                credential = AdminCredential()
                db.session.add(credential)
            try:
                credential.set_password(new_password)
                db.session.commit()
            except SQLAlchemyError:
                db.session.rollback()
                current_app.logger.exception('Erreur lors de la réinitialisation du mot de passe admin')
                flash('❌ Impossible de modifier le mot de passe pour le moment.', 'danger')
                return render_template('admin_forgot_password.html')
            flash('✅ Mot de passe modifié. Vous pouvez maintenant vous connecter.', 'success')
            return redirect(url_for('auth.admin_login'))

    return render_template('admin_forgot_password.html')

@auth_bp.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    flash('✅ Vous êtes déconnecté', 'success')
    return redirect(url_for('auth.admin_login'))
