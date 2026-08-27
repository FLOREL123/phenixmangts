"""
Modèles de base de données
"""
from app.extensions import db
from datetime import datetime
import bcrypt

class Stagiaire(db.Model):
    __tablename__ = 'stagiaires'
    
    # ============================================================
    # CLÉ PRIMAIRE
    # ============================================================
    id = db.Column(db.Integer, primary_key=True)
    
    # ============================================================
    # INFORMATIONS PERSONNELLES
    # ============================================================
    matricule = db.Column(db.String(20), unique=True, nullable=True)
    nom = db.Column(db.String(100), nullable=False)
    prenom = db.Column(db.String(100), nullable=False)
    genre = db.Column(db.String(10), default='M.')
    email = db.Column(db.String(100), unique=True, nullable=False)
    mot_de_passe = db.Column(db.String(255), nullable=False)
    telephone = db.Column(db.String(20))
    adresse = db.Column(db.String(255))
    photo = db.Column(db.String(255), nullable=True)
    
    # ============================================================
    # INFORMATIONS SCOLAIRES (NOUVEAUX CHAMPS)
    # ============================================================
    ecole = db.Column(db.String(255), nullable=True)
    niveau_etude = db.Column(db.String(100), nullable=True)
    telephone_parents = db.Column(db.String(20), nullable=True)
    
    # ============================================================
    # INFORMATIONS DE STAGE
    # ============================================================
    duree_stage_mois = db.Column(db.Integer, default=3)
    date_debut = db.Column(db.Date, nullable=True)
    date_fin = db.Column(db.Date, nullable=True)
    type_stage = db.Column(db.String(50), nullable=True)
    statut = db.Column(db.String(50), default='en_attente')
    
    # ============================================================
    # DOCUMENTS ET DOSSIERS
    # ============================================================
    cv = db.Column(db.String(255), nullable=True)
    lettre_demande = db.Column(db.String(255), nullable=True)
    dernier_diplome = db.Column(db.String(255), nullable=True)
    
    dossier_complet = db.Column(db.Boolean, default=False)
    date_soumission = db.Column(db.DateTime, nullable=True)
    
    demande_envoyee = db.Column(db.Boolean, default=False)
    date_demande = db.Column(db.DateTime, nullable=True)
    
    statut_demande = db.Column(db.String(50), default='en_attente')
    date_validation = db.Column(db.DateTime, nullable=True)
    entretien_programme = db.Column(db.DateTime, nullable=True)
    entretien_passe = db.Column(db.Boolean, default=False)
    approuve_definitif = db.Column(db.Boolean, default=False)
    
    # ============================================================
    # GÉNÉRATION DES DOCUMENTS
    # ============================================================
    autorisation_generee = db.Column(db.Boolean, default=False)
    date_autorisation = db.Column(db.DateTime)
    numero_autorisation = db.Column(db.String(50))
    notification_generee = db.Column(db.Boolean, default=False)
    date_notification = db.Column(db.DateTime)
    numero_notification = db.Column(db.String(50))
    attestation_generee = db.Column(db.Boolean, default=False)
    date_attestation = db.Column(db.DateTime)
    numero_attestation = db.Column(db.String(50))
    
    # ============================================================
    # DOCUMENTS PHYSIQUES
    # ============================================================
    dossiers_deposes = db.Column(db.Boolean, default=False)
    date_depot_dossiers = db.Column(db.DateTime)
    documents_physiques = db.Column(db.Boolean, default=False)
    date_depot_physique = db.Column(db.DateTime)
    
    # ============================================================
    # CHAMPS FLASK-LOGIN
    # ============================================================
    is_active = db.Column(db.Boolean, default=True)
    
    # ============================================================
    # TIMESTAMPS
    # ============================================================
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    # ============================================================
    # MÉTHODES FLASK-LOGIN
    # ============================================================
    def get_id(self):
        return str(self.id)
    
    @property
    def is_authenticated(self):
        return True
    
    @property
    def is_anonymous(self):
        return False
    
    # ============================================================
    # MÉTHODES DE GESTION DES MOTS DE PASSE
    # ============================================================
    def set_password(self, password):
        self.mot_de_passe = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def check_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.mot_de_passe.encode('utf-8'))
    
    # ============================================================
    # MÉTHODES DE GESTION DU GENRE
    # ============================================================
    def get_titre(self):
        return 'Mme' if self.genre == 'Mme' else 'M.'
    
    def get_genre_complet(self):
        if self.genre == 'Mme':
            return 'Madame'
        return 'Monsieur'
    
    # ============================================================
    # MÉTHODES DE GESTION DES DATES EN FRANÇAIS
    # ============================================================
    def _date_fr(self, date):
        if not date:
            return ""
        mois_fr = {
            'January': 'Janvier', 'February': 'Février', 'March': 'Mars',
            'April': 'Avril', 'May': 'Mai', 'June': 'Juin',
            'July': 'Juillet', 'August': 'Août', 'September': 'Septembre',
            'October': 'Octobre', 'November': 'Novembre', 'December': 'Décembre'
        }
        date_str = date.strftime('%d %B %Y')
        for en, fr in mois_fr.items():
            date_str = date_str.replace(en, fr)
        return date_str
    
    def date_debut_fr(self):
        return self._date_fr(self.date_debut)
    
    def date_fin_fr(self):
        return self._date_fr(self.date_fin)
    
    def date_entretien_fr(self):
        return self._date_fr(self.entretien_programme)


class AdminCredential(db.Model):
    __tablename__ = 'admin_credentials'

    id = db.Column(db.Integer, primary_key=True)
    password_hash = db.Column(db.String(255), nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    def set_password(self, password):
        self.password_hash = bcrypt.hashpw(
            password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def check_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
    
    # ============================================================
    # MÉTHODES DE GESTION DES DOCUMENTS
    # ============================================================
    def get_documents_requis(self):
        return ['photo', 'cv', 'lettre_demande', 'dernier_diplome']
    
    def documents_soumis(self):
        docs = self.get_documents_requis()
        for doc in docs:
            if not getattr(self, doc):
                return False
        return True
    
    @property
    def dossier_uploaded(self):
        return all([self.photo, self.cv, self.lettre_demande, self.dernier_diplome])
    
    def peut_pointer(self):
        if self.statut != 'actif':
            return False
        if self.date_fin and self.date_fin < datetime.now().date():
            return False
        return True
    
    # ============================================================
    # MÉTHODE POUR OBTENIR LES INFORMATIONS COMPLÈTES
    # ============================================================
    def get_infos_completes(self):
        """Retourne toutes les informations du stagiaire"""
        return {
            'nom': self.nom,
            'prenom': self.prenom,
            'genre': self.genre,
            'email': self.email,
            'telephone': self.telephone,
            'adresse': self.adresse,
            'ecole': self.ecole,
            'niveau_etude': self.niveau_etude,
            'telephone_parents': self.telephone_parents,
            'duree_stage_mois': self.duree_stage_mois,
            'matricule': self.matricule,
            'statut': self.statut,
            'date_debut': self.date_debut_fr() if self.date_debut else None,
            'date_fin': self.date_fin_fr() if self.date_fin else None,
            'type_stage': self.type_stage
        }
    
    def __repr__(self):
        return f"{self.prenom} {self.nom}"


# ============================================================
# MODÈLE POINTAGE
# ============================================================
class Pointage(db.Model):
    __tablename__ = 'pointages'
    
    id = db.Column(db.Integer, primary_key=True)
    stagiaire_id = db.Column(db.Integer, db.ForeignKey('stagiaires.id'), nullable=False)
    date = db.Column(db.Date, default=datetime.now().date)
    heure_arrivee = db.Column(db.Time)
    heure_depart = db.Column(db.Time)
    statut = db.Column(db.String(50), default='Présent')
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    commentaire = db.Column(db.String(255))
    justifie = db.Column(db.Boolean, default=False)
    
    stagiaire = db.relationship('Stagiaire', backref='pointages', lazy=True)
    
    @property
    def est_retard(self):
        if not self.heure_arrivee:
            return False
        heure_limite = datetime.strptime('09:00', '%H:%M').time()
        return self.heure_arrivee > heure_limite


# ============================================================
# MODÈLE ABSENCE
# ============================================================
class Absence(db.Model):
    __tablename__ = 'absences'
    
    id = db.Column(db.Integer, primary_key=True)
    stagiaire_id = db.Column(db.Integer, db.ForeignKey('stagiaires.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    justifiee = db.Column(db.Boolean, default=False)
    motif = db.Column(db.String(255))
    date_justification = db.Column(db.DateTime)
    
    stagiaire = db.relationship('Stagiaire', backref='absences', lazy=True)


# ============================================================
# MODÈLE NOTIFICATION
# ============================================================
class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    stagiaire_id = db.Column(db.Integer, db.ForeignKey('stagiaires.id'), nullable=False)
    titre = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(50))
    lu = db.Column(db.Boolean, default=False)
    email_envoye = db.Column(db.Boolean, default=False)
    date_envoi = db.Column(db.DateTime, default=datetime.now)
    
    stagiaire = db.relationship('Stagiaire', backref='notifications', lazy=True)


# ============================================================
# MODÈLE HISTORIQUE DES PRÉSENCES
# ============================================================
class HistoriquePresence(db.Model):
    __tablename__ = 'historique_presences'
    
    id = db.Column(db.Integer, primary_key=True)
    mois = db.Column(db.Integer, nullable=False)
    annee = db.Column(db.Integer, nullable=False)
    total_presences = db.Column(db.Integer, default=0)
    total_retards = db.Column(db.Integer, default=0)
    total_absents = db.Column(db.Integer, default=0)
    date_creation = db.Column(db.DateTime, default=datetime.now)
    
    @staticmethod
    def get_mois_annee():
        now = datetime.now()
        return now.month, now.year
