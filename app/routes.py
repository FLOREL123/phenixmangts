
"""
Routes de l'application - Stagiaires
"""
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Stagiaire, Pointage, Absence, Notification
from datetime import datetime, timedelta
import os
import uuid
from math import sqrt
from werkzeug.utils import secure_filename

routes_bp = Blueprint('routes', __name__)

# Configuration pour les uploads
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ============================================================
# PAGE D'ACCUEIL / DASHBOARD STAGIAIRE
# ============================================================
@routes_bp.route('/')
@routes_bp.route('/dashboard')
@login_required
def dashboard():
    """Tableau de bord du stagiaire"""
    # Si le stagiaire n'est pas encore actif, rediriger vers la page de dossier
    if current_user.statut == 'en_attente' and not current_user.demande_envoyee:
        return redirect(url_for('routes.mon_dossier'))
    
    if current_user.statut == 'en_attente' and current_user.demande_envoyee:
        return redirect(url_for('routes.mon_dossier'))
    
    # Vérifier si le stagiaire peut encore pointer
    peut_pointer = current_user.peut_pointer()
    
    pointages = Pointage.query.filter_by(stagiaire_id=current_user.id).order_by(Pointage.date.desc()).all()
    dernier = pointages[0] if pointages else None
    
    stats = {
        'total_pointages': len(pointages),
        'presences': len([p for p in pointages if p.statut == 'Présent']),
        'absences': len([p for p in pointages if p.statut == 'Absent'])
    }
    
    jours_restants = (current_user.date_fin - datetime.now().date()).days if current_user.date_fin else None
    stage_termine = current_user.date_fin and current_user.date_fin < datetime.now().date()
    
    return render_template('dashboard.html',
        pointages=pointages,
        dernier_pointage=dernier,
        stats=stats,
        jours_restants=jours_restants,
        stage_termine=stage_termine,
        peut_pointer=peut_pointer
    )

# ============================================================
# MON DOSSIER - GESTION DES DOCUMENTS
# ============================================================
@routes_bp.route('/mon-dossier', methods=['GET', 'POST'])
@login_required
def mon_dossier():
    """Gestion du dossier de stage"""
    if current_user.statut == 'actif':
        flash('✅ Vous êtes déjà un stagiaire actif', 'info')
        return redirect(url_for('routes.dashboard'))
    
    if request.method == 'POST':
        # Récupérer les fichiers
        photo = request.files.get('photo')
        cv = request.files.get('cv')
        lettre = request.files.get('lettre_demande')
        diplome = request.files.get('dernier_diplome')
        
        # Vérifier que tous les fichiers sont présents
        if not all([photo, cv, lettre, diplome]):
            flash('❌ Tous les documents sont obligatoires', 'danger')
            return redirect(url_for('routes.mon_dossier'))
        
        # Vérifier les extensions
        if not all([allowed_file(f.filename) for f in [photo, cv, lettre, diplome]]):
            flash('❌ Format de fichier non autorisé. Utilisez PDF, PNG, JPG, JPEG, GIF, DOC ou DOCX', 'danger')
            return redirect(url_for('routes.mon_dossier'))
        
        # Créer le dossier de l'utilisateur
        user_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], str(current_user.id))
        os.makedirs(user_folder, exist_ok=True)
        
        # Sauvegarder les fichiers
        def save_file(file, prefix):
            filename = secure_filename(file.filename)
            unique_name = f"{prefix}_{uuid.uuid4().hex}_{filename}"
            filepath = os.path.join(user_folder, unique_name)
            file.save(filepath)
            return '/'.join((str(current_user.id), unique_name))
        
        current_user.photo = save_file(photo, 'photo')
        current_user.cv = save_file(cv, 'cv')
        current_user.lettre_demande = save_file(lettre, 'lettre')
        current_user.dernier_diplome = save_file(diplome, 'diplome')
        
        current_user.dossier_complet = True
        current_user.date_soumission = datetime.now()
        db.session.commit()
        
        flash('✅ Dossiers déposés avec succès ! Vous pouvez maintenant envoyer votre demande.', 'success')
        return redirect(url_for('routes.mon_dossier'))
    
    return render_template('dossier.html', stagiaire=current_user)

# ============================================================
# ENVOYER LA DEMANDE DE STAGE
# ============================================================
@routes_bp.route('/envoyer-demande', methods=['POST'])
@login_required
def envoyer_demande():
    """Envoyer la demande de stage"""
    if current_user.statut == 'actif':
        return jsonify({'success': False, 'message': 'Vous êtes déjà un stagiaire actif'}), 400
    
    if not current_user.dossier_complet:
        return jsonify({'success': False, 'message': 'Veuillez d\'abord déposer tous vos documents'}), 400
    
    if current_user.demande_envoyee:
        return jsonify({'success': False, 'message': 'Vous avez déjà envoyé votre demande'}), 400
    
    current_user.demande_envoyee = True
    current_user.date_demande = datetime.now()
    current_user.statut_demande = 'en_attente'
    db.session.commit()
    
    # TODO: Envoyer un email à l'admin
    
    return jsonify({
        'success': True,
        'message': '✅ Votre demande a été envoyée avec succès ! L\'administrateur va l\'examiner.'
    })

# ============================================================
# STATUT DE LA DEMANDE (API)
# ============================================================
@routes_bp.route('/api/statut-demande')
@login_required
def api_statut_demande():
    """Récupérer le statut de la demande"""
    return jsonify({
        'statut': current_user.statut_demande,
        'entretien_programme': current_user.entretien_programme.strftime('%d/%m/%Y à %H:%M') if current_user.entretien_programme else None,
        'approuve_definitif': current_user.approuve_definitif,
        'matricule': current_user.matricule,
        'date_debut': current_user.date_debut_fr() if current_user.date_debut else None,
        'date_fin': current_user.date_fin_fr() if current_user.date_fin else None,
        'duree_stage': current_user.duree_stage_mois,
        'stage_termine': current_user.date_fin and current_user.date_fin < datetime.now().date()
    })

@routes_bp.route('/api/historique')
@login_required
def api_historique():
    """Retourne l'historique paginé du stagiaire connecté."""
    try:
        page = max(1, int(request.args.get('page', 1)))
    except (TypeError, ValueError):
        page = 1

    pagination = Pointage.query.filter_by(
        stagiaire_id=current_user.id
    ).order_by(Pointage.date.desc()).paginate(page=page, per_page=10, error_out=False)

    return jsonify({
        'pointages': [{
            'date': pointage.date.strftime('%d/%m/%Y'),
            'heure_arrivee': pointage.heure_arrivee.strftime('%H:%M') if pointage.heure_arrivee else None,
            'heure_depart': pointage.heure_depart.strftime('%H:%M') if pointage.heure_depart else None,
            'statut': pointage.statut,
        } for pointage in pagination.items],
        'has_more': pagination.has_next,
    })

# ============================================================
# POINTAGE AVEC GÉOLOCALISATION
# ============================================================
@routes_bp.route('/api/pointer', methods=['POST'])
@login_required
def api_pointer():
    """Enregistre un pointage avec géolocalisation"""
    # Vérifier si le stagiaire peut pointer
    if not current_user.peut_pointer():
        return jsonify({'success': False, 'message': '❌ Vous ne pouvez plus pointer. Votre stage est terminé.'}), 400
    
    if current_user.statut != 'actif':
        return jsonify({'success': False, 'message': '❌ Vous n\'êtes pas encore un stagiaire actif'}), 400
    
    data = request.get_json(silent=True) or {}
    type_pointage = data.get('type')
    latitude = data.get('latitude')
    longitude = data.get('longitude')
    
    if type_pointage not in {'arrivee', 'depart'}:
        return jsonify({'success': False, 'message': 'Type de pointage invalide'}), 400
    if latitude is None or longitude is None:
        return jsonify({'success': False, 'message': 'Géolocalisation requise'}), 400
    try:
        latitude = float(latitude)
        longitude = float(longitude)
    except (TypeError, ValueError):
        return jsonify({'success': False, 'message': 'Coordonnées invalides'}), 400

    distance = sqrt(
        (latitude - current_app.config['ENTREPRISE_LAT']) ** 2
        + (longitude - current_app.config['ENTREPRISE_LNG']) ** 2
    )
    if distance > current_app.config['RAYON_POINTAGE']:
        return jsonify({
            'success': False,
            'message': "Vous devez être dans la zone de l'entreprise pour pointer",
        }), 400
    
    aujourdhui = datetime.now().date()
    pointage_existant = Pointage.query.filter_by(
        stagiaire_id=current_user.id,
        date=aujourdhui
    ).first()
    
    if type_pointage == 'arrivee':
        if pointage_existant and pointage_existant.heure_arrivee:
            return jsonify({'success': False, 'message': 'Arrivée déjà pointée aujourd\'hui'}), 400
        if pointage_existant:
            pointage_existant.heure_arrivee = datetime.now().time()
            pointage_existant.latitude = latitude
            pointage_existant.longitude = longitude
            pointage_existant.statut = 'Présent'
        else:
            pointage = Pointage(
                stagiaire_id=current_user.id,
                date=aujourdhui,
                heure_arrivee=datetime.now().time(),
                latitude=latitude,
                longitude=longitude,
                statut='Présent'
            )
            db.session.add(pointage)
    
    elif type_pointage == 'depart':
        if not pointage_existant or not pointage_existant.heure_arrivee:
            return jsonify({'success': False, 'message': 'Vous devez d\'abord pointer votre arrivée'}), 400
        if pointage_existant.heure_depart:
            return jsonify({'success': False, 'message': 'Départ déjà pointé aujourd\'hui'}), 400
        pointage_existant.heure_depart = datetime.now().time()
    
    db.session.commit()
    return jsonify({'success': True, 'message': f'{type_pointage} enregistré avec succès'})

# ============================================================
# TÉLÉCHARGER UN FICHIER (pour visualisation)
# ============================================================
@routes_bp.route('/uploads/<path:filename>')
def uploaded_file(filename):
    """Permet de visualiser les fichiers uploadés"""
    # Les anciennes versions stockaient le préfixe "uploads/" en base.
    filename = filename.removeprefix('uploads/')

    # Vérifier que l'utilisateur est connecté en tant qu'admin ou le propriétaire du fichier
    if not session.get('admin_logged_in'):
        # Si c'est un stagiaire, vérifier que c'est son fichier
        if current_user.is_authenticated:
            # Extraire l'ID du stagiaire du chemin
            parts = filename.split('/')
            if len(parts) >= 2 and parts[0].isdigit():
                if int(parts[0]) != current_user.id:
                    return "Accès refusé", 403
        else:
            return "Accès refusé", 403
    
    upload_dir = current_app.config['UPLOAD_FOLDER']
    return send_from_directory(upload_dir, filename)

# ============================================================
# IMPORT POUR send_from_directory
# ============================================================
from flask import send_from_directory
