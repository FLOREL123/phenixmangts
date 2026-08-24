
"""
Routes administrateur - Gestion des demandes et des stagiaires
"""
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash, Response, current_app
from app.extensions import db, mail
from app.models import Stagiaire, Pointage, Absence, Notification, HistoriquePresence
from datetime import datetime, timedelta
import os
import io
from werkzeug.utils import secure_filename
from flask_mail import Message
from sqlalchemy import func

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Configuration des extensions autorisées pour les fichiers
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def send_email(to, subject, body, html=None):
    """Envoyer un email"""
    try:
        msg = Message(
            subject=subject,
            recipients=[to],
            body=body,
            html=html or body
        )
        mail.send(msg)
        return True
    except Exception as e:
        print(f"❌ Erreur d'envoi d'email: {e}")
        return False

# ============================================================
# ADMIN - TABLEAU DE BORD PRINCIPAL
# ============================================================
@admin_bp.route('/')
@admin_bp.route('/dashboard')
def dashboard():
    """Tableau de bord administrateur"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('auth.admin_login'))
    
    total_stagiaires = Stagiaire.query.count()
    stagiaires_actifs = Stagiaire.query.filter_by(statut='actif').count()
    demandes_attente = Stagiaire.query.filter_by(statut_demande='en_attente', demande_envoyee=True).count()
    demandes_approuvees = Stagiaire.query.filter_by(statut_demande='approuve').count()
    demandes_rejetees = Stagiaire.query.filter_by(statut_demande='rejete').count()
    
    aujourdhui = datetime.now().date()
    pointages = Pointage.query.filter_by(date=aujourdhui).all()
    presents_aujourdhui = len(pointages)
    
    heure_limite = datetime.strptime('09:00', '%H:%M').time()
    retards = len([p for p in pointages if p.heure_arrivee and p.heure_arrivee > heure_limite])
    
    stagiaires_actifs_list = Stagiaire.query.filter_by(statut='actif').all()
    stagiaires_actifs_ids = [s.id for s in stagiaires_actifs_list]
    pointages_aujourdhui_ids = [p.stagiaire_id for p in pointages]
    absents_aujourdhui = len([s for s in stagiaires_actifs_ids if s not in pointages_aujourdhui_ids])
    
    dernieres_demandes = Stagiaire.query.filter_by(demande_envoyee=True).order_by(Stagiaire.date_demande.desc()).limit(5).all()
    
    mois, annee = HistoriquePresence.get_mois_annee()
    historique = HistoriquePresence.query.filter_by(mois=mois, annee=annee).first()
    
    stats = {
        'total_stagiaires': total_stagiaires,
        'stagiaires_actifs': stagiaires_actifs,
        'demandes_attente': demandes_attente,
        'demandes_approuvees': demandes_approuvees,
        'demandes_rejetees': demandes_rejetees,
        'presents_aujourdhui': presents_aujourdhui,
        'retards_aujourdhui': retards,
        'absents_aujourdhui': absents_aujourdhui,
        'total_presences_mois': historique.total_presences if historique else 0
    }
    
    return render_template('admin/dashboard.html',
        stats=stats,
        dernieres_demandes=dernieres_demandes,
        today=aujourdhui
    )

# ============================================================
# ADMIN - PRÉSENCES DU JOUR
# ============================================================
@admin_bp.route('/presences')
def presences():
    """Page des présences du jour"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('auth.admin_login'))
    
    aujourdhui = datetime.now().date()
    heure_limite = datetime.strptime('09:00', '%H:%M').time()
    
    tous_pointages = Pointage.query.filter_by(date=aujourdhui).all()
    
    presences = []
    retards = []
    stagiaires_actifs = Stagiaire.query.filter_by(statut='actif').all()
    stagiaires_absents = []
    
    pointages_ids = [p.stagiaire_id for p in tous_pointages]
    
    for p in tous_pointages:
        stagiaire = Stagiaire.query.get(p.stagiaire_id)
        if stagiaire:
            est_retard = p.heure_arrivee and p.heure_arrivee > heure_limite
            presences.append({
                'id': p.id,
                'stagiaire': stagiaire,
                'heure_arrivee': p.heure_arrivee,
                'heure_depart': p.heure_depart,
                'est_retard': est_retard,
                'latitude': p.latitude,
                'longitude': p.longitude
            })
            if est_retard:
                retards.append({
                    'id': p.id,
                    'stagiaire': stagiaire,
                    'heure_arrivee': p.heure_arrivee,
                    'heure_depart': p.heure_depart,
                    'latitude': p.latitude,
                    'longitude': p.longitude
                })
    
    for s in stagiaires_actifs:
        if s.id not in pointages_ids:
            stagiaires_absents.append(s)
    
    return render_template('admin/presences.html',
        presences=presences,
        retards=retards,
        stagiaires_absents=stagiaires_absents,
        today=aujourdhui
    )

# ============================================================
# ADMIN - HISTORIQUE DES PRÉSENCES
# ============================================================
@admin_bp.route('/historique')
def historique():
    """Page d'historique des présences"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('auth.admin_login'))
    
    historiques = HistoriquePresence.query.order_by(
        HistoriquePresence.annee.desc(), 
        HistoriquePresence.mois.desc()
    ).all()
    
    total_presences = sum(h.total_presences for h in historiques)
    total_retards = sum(h.total_retards for h in historiques)
    total_absents = sum(h.total_absents for h in historiques)
    
    mois_fr = {
        1: 'Janvier', 2: 'Février', 3: 'Mars', 4: 'Avril',
        5: 'Mai', 6: 'Juin', 7: 'Juillet', 8: 'Août',
        9: 'Septembre', 10: 'Octobre', 11: 'Novembre', 12: 'Décembre'
    }
    
    return render_template('admin/historique.html',
        historiques=historiques,
        mois_fr=mois_fr,
        total_presences=total_presences,
        total_retards=total_retards,
        total_absents=total_absents
    )

# ============================================================
# ADMIN - VOIR LES PRÉSENCES D'UN MOIS
# ============================================================
@admin_bp.route('/historique/<int:mois>/<int:annee>')
def historique_detail(mois, annee):
    """Voir les détails des présences d'un mois"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('auth.admin_login'))
    
    debut_mois = datetime(annee, mois, 1).date()
    if mois == 12:
        fin_mois = datetime(annee + 1, 1, 1).date() - timedelta(days=1)
    else:
        fin_mois = datetime(annee, mois + 1, 1).date() - timedelta(days=1)
    
    pointages = Pointage.query.filter(
        Pointage.date >= debut_mois,
        Pointage.date <= fin_mois
    ).order_by(Pointage.date).all()
    
    heure_limite = datetime.strptime('09:00', '%H:%M').time()
    
    details = []
    stagiaires_actifs = Stagiaire.query.filter_by(statut='actif').all()
    stagiaires_ids = [s.id for s in stagiaires_actifs]
    pointages_par_jour = {}
    
    for p in pointages:
        date_str = p.date.strftime('%Y-%m-%d')
        if date_str not in pointages_par_jour:
            pointages_par_jour[date_str] = []
        pointages_par_jour[date_str].append(p)
    
    jours_ouvrables = []
    jour = debut_mois
    while jour <= fin_mois:
        if jour.weekday() < 5:  # Lundi à vendredi
            jours_ouvrables.append(jour)
        jour += timedelta(days=1)
    
    for jour in jours_ouvrables:
        date_str = jour.strftime('%Y-%m-%d')
        pointages_jour = pointages_par_jour.get(date_str, [])
        
        presents = []
        retards_jour = []
        absents_jour = []
        
        pointages_ids_jour = [p.stagiaire_id for p in pointages_jour]
        
        for s in stagiaires_actifs:
            if s.id in pointages_ids_jour:
                p = next((x for x in pointages_jour if x.stagiaire_id == s.id), None)
                if p:
                    est_retard = p.heure_arrivee and p.heure_arrivee > heure_limite
                    presents.append({
                        'stagiaire': s,
                        'heure_arrivee': p.heure_arrivee,
                        'est_retard': est_retard
                    })
                    if est_retard:
                        retards_jour.append(s)
            else:
                absents_jour.append(s)
        
        details.append({
            'date': jour,
            'date_fr': jour.strftime('%d/%m/%Y'),
            'presents': presents,
            'retards': retards_jour,
            'absents': absents_jour,
            'total_presents': len(presents),
            'total_retards': len(retards_jour),
            'total_absents': len(absents_jour)
        })
    
    mois_fr = {
        1: 'Janvier', 2: 'Février', 3: 'Mars', 4: 'Avril',
        5: 'Mai', 6: 'Juin', 7: 'Juillet', 8: 'Août',
        9: 'Septembre', 10: 'Octobre', 11: 'Novembre', 12: 'Décembre'
    }
    
    total_presents = sum(d['total_presents'] for d in details)
    total_retards = sum(d['total_retards'] for d in details)
    total_absents = sum(d['total_absents'] for d in details)
    
    return render_template('admin/historique_detail.html',
        details=details,
        mois=mois,
        annee=annee,
        mois_nom=mois_fr[mois],
        total_presents=total_presents,
        total_retards=total_retards,
        total_absents=total_absents
    )

# ============================================================
# ADMIN - EFFACER L'HISTORIQUE D'UN MOIS
# ============================================================
@admin_bp.route('/historique/<int:id>/effacer', methods=['POST'])
def effacer_historique(id):
    """Effacer l'historique d'un mois"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Accès refusé'}), 401
    
    historique = HistoriquePresence.query.get_or_404(id)
    mois_nom = {1: 'Janvier', 2: 'Février', 3: 'Mars', 4: 'Avril',
                5: 'Mai', 6: 'Juin', 7: 'Juillet', 8: 'Août',
                9: 'Septembre', 10: 'Octobre', 11: 'Novembre', 12: 'Décembre'}.get(historique.mois, '')
    
    db.session.delete(historique)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f"✅ Historique de {mois_nom} {historique.annee} effacé avec succès"
    })

# ============================================================
# ADMIN - API POUR METTRE À JOUR L'HISTORIQUE
# ============================================================
@admin_bp.route('/api/mettre-a-jour-historique', methods=['POST'])
def mettre_a_jour_historique():
    """Met à jour l'historique des présences pour le mois en cours"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Accès refusé'}), 401
    
    mois, annee = HistoriquePresence.get_mois_annee()
    
    debut_mois = datetime(annee, mois, 1).date()
    if mois == 12:
        fin_mois = datetime(annee + 1, 1, 1).date() - timedelta(days=1)
    else:
        fin_mois = datetime(annee, mois + 1, 1).date() - timedelta(days=1)
    
    pointages_mois = Pointage.query.filter(
        Pointage.date >= debut_mois,
        Pointage.date <= fin_mois
    ).all()
    
    total_presences = len(pointages_mois)
    
    heure_limite = datetime.strptime('09:00', '%H:%M').time()
    retards_mois = len([p for p in pointages_mois if p.heure_arrivee and p.heure_arrivee > heure_limite])
    
    stagiaires_actifs = Stagiaire.query.filter_by(statut='actif').count()
    jours_ouvrables = sum(1 for d in range((fin_mois - debut_mois).days + 1) 
                         if (debut_mois + timedelta(days=d)).weekday() < 5)
    absents_mois = max(0, (stagiaires_actifs * jours_ouvrables) - total_presences)
    
    historique = HistoriquePresence.query.filter_by(mois=mois, annee=annee).first()
    
    if historique:
        historique.total_presences = total_presences
        historique.total_retards = retards_mois
        historique.total_absents = absents_mois
    else:
        historique = HistoriquePresence(
            mois=mois,
            annee=annee,
            total_presences=total_presences,
            total_retards=retards_mois,
            total_absents=absents_mois
        )
        db.session.add(historique)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f"✅ Historique du mois mis à jour"
    })

# ============================================================
# ADMIN - GESTION DES DEMANDES
# ============================================================
@admin_bp.route('/demandes')
def demandes():
    """Liste des demandes de stage"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('auth.admin_login'))
    
    statut = request.args.get('statut', 'tous')
    
    # Une demande soumise est identifiée par son indicateur ou sa date d'envoi.
    # Cette compatibilité récupère les anciennes demandes enregistrées avant
    # l'ajout fiable de demande_envoyee.
    query = Stagiaire.query.filter(
        db.or_(
            Stagiaire.demande_envoyee.is_(True),
            Stagiaire.date_demande.isnot(None)
        )
    )
    
    if statut != 'tous':
        query = query.filter_by(statut_demande=statut)
    
    demandes = query.order_by(Stagiaire.date_demande.desc()).all()
    
    stats = {
        'en_attente': query.filter(Stagiaire.statut_demande == 'en_attente').count(),
        'approuve': query.filter(Stagiaire.statut_demande == 'approuve').count(),
        'rejete': query.filter(Stagiaire.statut_demande == 'rejete').count(),
        'total': query.count()
    }
    
    return render_template('admin/demandes.html',
        demandes=demandes,
        stats=stats,
        statut_actif=statut
    )

# ============================================================
# ADMIN - DETAIL D'UNE DEMANDE
# ============================================================
@admin_bp.route('/demande/<int:id>')
def demande_detail(id):
    """Détail d'une demande de stage"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('auth.admin_login'))
    
    stagiaire = Stagiaire.query.get_or_404(id)
    
    if not stagiaire.demande_envoyee:
        flash('❌ Ce stagiaire n\'a pas encore envoyé de demande', 'warning')
        return redirect(url_for('admin.demandes'))
    
    return render_template('admin/demande_detail.html', stagiaire=stagiaire)

# ============================================================
# ADMIN - APPROUVER UNE DEMANDE
# ============================================================
@admin_bp.route('/demande/<int:id>/approuver', methods=['POST'])
def approuver_demande(id):
    """Approuver une demande et programmer un entretien"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Accès refusé'}), 401
    
    stagiaire = Stagiaire.query.get_or_404(id)
    data = request.get_json(silent=True) or {}
    
    if stagiaire.statut_demande != 'en_attente':
        return jsonify({'success': False, 'message': 'Cette demande a déjà été traitée'}), 400
    
    date_entretien = data.get('date_entretien')
    heure_entretien = data.get('heure_entretien')
    
    if not date_entretien or not heure_entretien:
        return jsonify({'success': False, 'message': 'Veuillez spécifier la date et l\'heure de l\'entretien'}), 400
    
    try:
        entretien_datetime = datetime.strptime(f"{date_entretien} {heure_entretien}", '%Y-%m-%d %H:%M')
    except ValueError:
        return jsonify({'success': False, 'message': 'Format de date/heure invalide'}), 400
    
    stagiaire.statut_demande = 'approuve'
    stagiaire.entretien_programme = entretien_datetime
    stagiaire.date_validation = datetime.now()
    db.session.commit()
    
    date_entretien_fr = stagiaire._date_fr(entretien_datetime)
    heure_entretien_str = entretien_datetime.strftime('%H:%M')
    
    sujet = "📅 Entretien programmé - PHENIX MANAGEMENT"
    corps = f"""
Bonjour {stagiaire.prenom} {stagiaire.nom},

Votre demande de stage a été approuvée par l'administrateur.

📅 Un entretien est programmé le {date_entretien_fr} à {heure_entretien_str}.

Veuillez vous présenter à l'adresse suivante :
PHENIX MANAGEMENT
Gbégamey-Cotonou, Bénin
Maison DANSOU PASCAL

Pour toute question, contactez-nous.

Cordialement,
L'équipe PHENIX MANAGEMENT
"""
    
    send_email(stagiaire.email, sujet, corps)
    
    return jsonify({
        'success': True,
        'message': f'Demande approuvée. Entretien programmé le {date_entretien_fr} à {heure_entretien_str}'
    })

# ============================================================
# ADMIN - REJETER UNE DEMANDE
# ============================================================
@admin_bp.route('/demande/<int:id>/rejeter', methods=['POST'])
def rejeter_demande(id):
    """Rejeter une demande de stage"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Accès refusé'}), 401
    
    stagiaire = Stagiaire.query.get_or_404(id)
    data = request.get_json(silent=True) or {}
    
    if stagiaire.statut_demande != 'en_attente':
        return jsonify({'success': False, 'message': 'Cette demande a déjà été traitée'}), 400
    
    motif = data.get('motif', 'Motif non spécifié')
    
    stagiaire.statut_demande = 'rejete'
    stagiaire.date_validation = datetime.now()
    db.session.commit()
    
    sujet = "❌ Demande de stage - PHENIX MANAGEMENT"
    corps = f"""
Bonjour {stagiaire.prenom} {stagiaire.nom},

Nous regrettons de vous informer que votre demande de stage n'a pas été retenue.

Motif : {motif}

Vous pouvez soumettre une nouvelle demande à tout moment.

Cordialement,
L'équipe PHENIX MANAGEMENT
"""
    
    send_email(stagiaire.email, sujet, corps)
    
    return jsonify({
        'success': True,
        'message': 'Demande rejetée'
    })

# ============================================================
# ADMIN - ENTRETIEN PASSÉ
# ============================================================
@admin_bp.route('/stagiaire/<int:id>/entretien-passe', methods=['POST'])
def entretien_passe(id):
    """Marquer l'entretien comme passé"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Accès refusé'}), 401
    
    stagiaire = Stagiaire.query.get_or_404(id)
    
    if stagiaire.statut_demande != 'approuve':
        return jsonify({'success': False, 'message': 'La demande doit d\'abord être approuvée'}), 400
    
    stagiaire.entretien_passe = True
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Entretien marqué comme passé'
    })

# ============================================================
# ADMIN - VALIDER UN STAGIAIRE
# ============================================================
@admin_bp.route('/stagiaire/<int:id>/valider', methods=['POST'])
def valider_stagiaire(id):
    """Valider un stagiaire après l'entretien"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Accès refusé'}), 401
    
    stagiaire = Stagiaire.query.get_or_404(id)
    data = request.get_json(silent=True) or {}
    
    if stagiaire.statut_demande != 'approuve':
        return jsonify({'success': False, 'message': 'La demande doit d\'abord être approuvée'}), 400
    
    if not stagiaire.entretien_passe:
        return jsonify({'success': False, 'message': 'L\'entretien doit d\'abord avoir lieu'}), 400
    
    annee = datetime.now().strftime('%y')
    count = Stagiaire.query.filter(Stagiaire.matricule.isnot(None)).count() + 1
    matricule = f"STU{annee}{count:04d}"
    
    stagiaire.approuve_definitif = True
    stagiaire.matricule = matricule
    stagiaire.statut = 'actif'
    
    stagiaire.date_debut = datetime.now().date()
    duree_mois = stagiaire.duree_stage_mois or 3
    stagiaire.date_fin = stagiaire.date_debut + timedelta(days=duree_mois * 30)
    
    stagiaire.type_stage = data.get('type_stage', 'professionnel')
    
    stagiaire.dossiers_deposes = True
    stagiaire.date_depot_dossiers = datetime.now()
    
    db.session.commit()
    
    numero_notification = f"000{stagiaire.id:04d}/{datetime.now().strftime('%m')}{datetime.now().strftime('%y')}/PHM"
    stagiaire.numero_notification = numero_notification
    stagiaire.notification_generee = True
    stagiaire.date_notification = datetime.now()
    db.session.commit()
    
    date_debut_fr = stagiaire.date_debut_fr()
    date_fin_fr = stagiaire.date_fin_fr()
    
    sujet = "🎉 Félicitations ! Vous êtes officiellement stagiaire - PHENIX MANAGEMENT"
    
    corps = f"""
Bonjour {stagiaire.prenom} {stagiaire.nom},

Nous avons le plaisir de vous informer que votre candidature a été acceptée et que vous êtes désormais officiellement stagiaire au sein de PHENIX MANAGEMENT.

📋 Récapitulatif :
- Matricule : {matricule}
- Type de stage : {stagiaire.type_stage}
- Durée du stage : {duree_mois} mois
- Date de début : {date_debut_fr}
- Date de fin : {date_fin_fr}

📄 Notification de stage : {numero_notification}

Veuillez imprimer cette notification et la présenter lors de votre arrivée.

Nous vous souhaitons une excellente expérience au sein de notre cabinet.

Cordialement,
L'équipe PHENIX MANAGEMENT
---
PHENIX MANAGEMENT
Management - Finances - Fiscalité - Contrôle de Gestion
Gbégamey-Cotonou, Bénin
"""
    
    send_email(stagiaire.email, sujet, corps)
    
    notification = Notification(
        stagiaire_id=stagiaire.id,
        titre="Validation définitive - Stage",
        message=f"Félicitations ! Vous êtes officiellement stagiaire. Matricule: {matricule}",
        type="validation",
        email_envoye=True
    )
    db.session.add(notification)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'Stagiaire validé avec matricule {matricule}'
    })

# ============================================================
# ADMIN - LISTE DES STAGIAIRES
# ============================================================
@admin_bp.route('/stagiaires')
def stagiaires():
    """Liste des stagiaires validés"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('auth.admin_login'))
    
    aujourdhui = datetime.now().date()
    stagiaires = Stagiaire.query.filter_by(statut='actif').order_by(Stagiaire.nom).all()
    
    return render_template('admin/stagiaires.html', 
        stagiaires=stagiaires,
        today=aujourdhui
    )

# ============================================================
# ADMIN - API STAGIAIRES PAR PÉRIODE
# ============================================================
@admin_bp.route('/api/stagiaires/periode')
def api_stagiaires_periode():
    """API pour récupérer les stagiaires sur une période donnée"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Accès refusé'}), 401
    
    date_debut = request.args.get('date_debut')
    date_fin = request.args.get('date_fin')
    
    if not date_debut or not date_fin:
        aujourdhui = datetime.now().date()
        date_debut = aujourdhui.replace(day=1).strftime('%Y-%m-%d')
        date_fin = aujourdhui.strftime('%Y-%m-%d')
    
    try:
        debut = datetime.strptime(date_debut, '%Y-%m-%d').date()
        fin = datetime.strptime(date_fin, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Format de date invalide'}), 400
    
    query = Stagiaire.query.filter(
        Stagiaire.statut == 'actif',
        Stagiaire.date_debut <= fin,
        Stagiaire.date_fin >= debut
    ).order_by(Stagiaire.nom)
    
    stagiaires = query.all()
    
    return jsonify([{
        'id': s.id,
        'matricule': s.matricule,
        'nom': s.nom,
        'prenom': s.prenom,
        'genre': s.genre,
        'email': s.email,
        'telephone': s.telephone,
        'adresse': s.adresse,
        'ecole': s.ecole,
        'niveau_etude': s.niveau_etude,
        'telephone_parents': s.telephone_parents,
        'type_stage': s.type_stage,
        'date_debut': s.date_debut.strftime('%d/%m/%Y') if s.date_debut else '-',
        'date_fin': s.date_fin.strftime('%d/%m/%Y') if s.date_fin else '-',
        'statut': s.statut,
        'dossiers_deposes': s.dossiers_deposes,
        'notification_generee': s.notification_generee,
        'attestation_generee': s.attestation_generee,
        'photo': s.photo
    } for s in stagiaires])

# ============================================================
# ADMIN - EXPORT PDF
# ============================================================
@admin_bp.route('/export/stagiaires-periode-pdf')
def export_stagiaires_periode_pdf():
    """Exporte la liste des stagiaires en PDF"""
    if not session.get('admin_logged_in'):
        return "Accès refusé", 401
    
    date_debut = request.args.get('date_debut')
    date_fin = request.args.get('date_fin')
    
    query = Stagiaire.query.filter_by(statut='actif')
    
    if date_debut and date_fin:
        try:
            debut = datetime.strptime(date_debut, '%Y-%m-%d').date()
            fin = datetime.strptime(date_fin, '%Y-%m-%d').date()
            query = query.filter(
                Stagiaire.date_debut <= fin,
                Stagiaire.date_fin >= debut
            )
        except ValueError:
            pass
    
    stagiaires = query.order_by(Stagiaire.nom).all()
    
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.enums import TA_CENTER
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4),
                          rightMargin=40, leftMargin=40,
                          topMargin=40, bottomMargin=40)
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=colors.HexColor('#E67E22'),
        alignment=TA_CENTER,
        spaceAfter=6
    )
    
    story = []
    
    story.append(Paragraph("PHENIX MANAGEMENT", title_style))
    story.append(Paragraph("Liste des stagiaires", styles['Normal']))
    
    if date_debut and date_fin:
        debut_formate = datetime.strptime(date_debut, '%Y-%m-%d').strftime('%d/%m/%Y')
        fin_formate = datetime.strptime(date_fin, '%Y-%m-%d').strftime('%d/%m/%Y')
        periode_text = f"Période du {debut_formate} au {fin_formate}"
    else:
        periode_text = "Tous les stagiaires actifs"
    
    story.append(Paragraph(f"<b>{periode_text}</b>", styles['Normal']))
    story.append(Paragraph(f"Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}", styles['Normal']))
    story.append(Spacer(1, 0.2*inch))
    
    if stagiaires:
        data = [['N°', 'Matricule', 'Nom', 'Prénom', 'Email', 'Téléphone', 'École', 'Niveau', 'Début', 'Fin']]
        
        for i, s in enumerate(stagiaires, 1):
            data.append([
                str(i),
                s.matricule or '-',
                s.nom[:20],
                s.prenom[:20],
                s.email[:25],
                s.telephone or '-',
                (s.ecole or '-')[:25],
                s.niveau_etude or '-',
                s.date_debut.strftime('%d/%m/%Y') if s.date_debut else '-',
                s.date_fin.strftime('%d/%m/%Y') if s.date_fin else '-'
            ])
        
        col_widths = [0.3*inch, 0.7*inch, 1*inch, 1*inch, 1.2*inch, 0.8*inch, 1.2*inch, 0.7*inch, 0.7*inch, 0.7*inch]
        table = Table(data, colWidths=col_widths, repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E67E22')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('PADDING', (0, 0), (-1, -1), 3),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#fafafa')]),
        ]))
        story.append(table)
        story.append(Spacer(1, 0.1*inch))
        story.append(Paragraph(f"Total: {len(stagiaires)} stagiaires", styles['Normal']))
    else:
        story.append(Paragraph("Aucun stagiaire trouvé.", styles['Normal']))
    
    doc.build(story)
    
    pdf_content = buffer.getvalue()
    buffer.close()
    
    return Response(pdf_content, 
                   content_type='application/pdf',
                   headers={'Content-Disposition': 'attachment; filename=liste_stagiaires.pdf'})

# ============================================================
# ADMIN - GÉNÉRER LA NOTIFICATION
# ============================================================
@admin_bp.route('/notification/<int:stagiaire_id>')
def generer_notification(stagiaire_id):
    """Génère la notification de stage"""
    if not session.get('admin_logged_in'):
        return "Accès refusé", 401
    
    stagiaire = Stagiaire.query.get_or_404(stagiaire_id)
    
    if not stagiaire.dossiers_deposes:
        return "❌ Les dossiers de stage n'ont pas encore été déposés.", 400
    
    if not stagiaire.numero_notification:
        numero = f"000{stagiaire_id:04d}/{datetime.now().strftime('%m')}{datetime.now().strftime('%y')}/PHM"
        stagiaire.numero_notification = numero
        stagiaire.notification_generee = True
        stagiaire.date_notification = datetime.now()
        db.session.commit()
    
    date_entretien_fr = ""
    if stagiaire.entretien_programme:
        date_entretien_fr = stagiaire._date_fr(stagiaire.entretien_programme)
    else:
        date_entretien_fr = datetime.now().strftime('%d %B %Y')
        mois_fr = {
            'January': 'Janvier', 'February': 'Février', 'March': 'Mars',
            'April': 'Avril', 'May': 'Mai', 'June': 'Juin',
            'July': 'Juillet', 'August': 'Août', 'September': 'Septembre',
            'October': 'Octobre', 'November': 'Novembre', 'December': 'Décembre'
        }
        for en, fr in mois_fr.items():
            date_entretien_fr = date_entretien_fr.replace(en, fr)
    
    return render_template('autorisation.html',
        stagiaire=stagiaire,
        numero=stagiaire.numero_notification,
        date_aujourdhui=datetime.now().strftime('%d %B %Y'),
        date_entretien_fr=date_entretien_fr,
        type_stage=stagiaire.type_stage
    )

# ============================================================
# ADMIN - GÉNÉRER L'ATTESTATION
# ============================================================
@admin_bp.route('/attestation/<int:stagiaire_id>')
def generer_attestation(stagiaire_id):
    """Génère l'attestation de fin de stage"""
    if not session.get('admin_logged_in'):
        return "Accès refusé", 401
    
    stagiaire = Stagiaire.query.get_or_404(stagiaire_id)
    
    if stagiaire.statut != 'actif' and stagiaire.statut != 'termine':
        return "❌ Le stagiaire n'est pas actif.", 400
    
    if not stagiaire.dossiers_deposes:
        return "❌ Les dossiers de stage n'ont pas été déposés.", 400
    
    if not stagiaire.notification_generee:
        return "❌ La notification de stage n'a pas été générée.", 400
    
    if not stagiaire.numero_attestation:
        numero = f"N°00{stagiaire_id:04d}/PHM/{datetime.now().strftime('%Y')}"
        stagiaire.numero_attestation = numero
        stagiaire.attestation_generee = True
        stagiaire.date_attestation = datetime.now()
        db.session.commit()
    
    return render_template('attestation_fin_stage.html',
        stagiaire=stagiaire,
        numero=stagiaire.numero_attestation,
        date_aujourdhui=datetime.now().strftime('%d %B %Y'),
        type_stage=stagiaire.type_stage
    )

# ============================================================
# ADMIN - API PRÉSENCES
# ============================================================
@admin_bp.route('/api/presences')
def api_presences():
    """Récupère les présences du jour avec localisation"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Accès refusé'}), 401
    
    aujourdhui = datetime.now().date()
    pointages = Pointage.query.filter_by(date=aujourdhui).all()
    heure_limite = datetime.strptime('09:00', '%H:%M').time()
    
    resultats = []
    retards = []
    stagiaires_actifs = Stagiaire.query.filter_by(statut='actif').all()
    stagiaires_absents = []
    
    pointages_ids = [p.stagiaire_id for p in pointages]
    
    for p in pointages:
        stagiaire = Stagiaire.query.get(p.stagiaire_id)
        if stagiaire:
            est_retard = p.heure_arrivee and p.heure_arrivee > heure_limite
            resultats.append({
                'id': p.id,
                'stagiaire': f"{stagiaire.prenom} {stagiaire.nom}",
                'matricule': stagiaire.matricule,
                'heure_arrivee': p.heure_arrivee.strftime('%H:%M') if p.heure_arrivee else '-',
                'heure_depart': p.heure_depart.strftime('%H:%M') if p.heure_depart else '-',
                'latitude': p.latitude,
                'longitude': p.longitude,
                'statut': p.statut or 'Présent',
                'est_retard': est_retard
            })
            if est_retard:
                retards.append({
                    'id': p.id,
                    'stagiaire': f"{stagiaire.prenom} {stagiaire.nom}",
                    'matricule': stagiaire.matricule,
                    'heure_arrivee': p.heure_arrivee.strftime('%H:%M') if p.heure_arrivee else '-',
                    'heure_depart': p.heure_depart.strftime('%H:%M') if p.heure_depart else '-',
                    'latitude': p.latitude,
                    'longitude': p.longitude
                })
    
    for s in stagiaires_actifs:
        if s.id not in pointages_ids:
            stagiaires_absents.append({
                'id': s.id,
                'nom': s.nom,
                'prenom': s.prenom,
                'matricule': s.matricule,
                'email': s.email
            })
    
    return jsonify({
        'presences': resultats,
        'retards': retards,
        'absents': stagiaires_absents,
        'total_presences': len(resultats),
        'total_retards': len(retards),
        'total_absents': len(stagiaires_absents)
    })
