"""Interface translations. Creative content and model data are never translated here."""
import os

LANGUAGES = [('system', 'System language'), ('en', 'English'), ('de', 'Deutsch'), ('es', 'Español'), ('fr', 'Français')]
# English | German | Spanish | French. Keep format placeholders identical.
_ROWS = '''
Review songs|Songs überprüfen|Revisar canciones|Réviser les chansons
Select songs and enter feedback.|Wähle Songs und gib Feedback ein.|Selecciona canciones e introduce comentarios.|Sélectionnez des chansons et ajoutez des commentaires.
Rewrite selected songs|Ausgewählte Songs überarbeiten|Reescribir canciones seleccionadas|Réécrire les chansons sélectionnées
Songs|Songs|Canciones|Chansons
Collections|Sammlungen|Colecciones|Collections
New song|Neuer Song|Nueva canción|Nouvelle chanson
New collection|Neue Sammlung|Nueva colección|Nouvelle collection
Settings|Einstellungen|Ajustes|Paramètres
Close|Schließen|Cerrar|Fermer
Apply|Anwenden|Aplicar|Appliquer
Cancel|Abbrechen|Cancelar|Annuler
Save|Speichern|Guardar|Enregistrer
Copy|Kopieren|Copiar|Copier
Copy song|Song kopieren|Copiar canción|Copier la chanson
Copy all|Alles kopieren|Copiar todo|Tout copier
Write song|Song schreiben|Escribir canción|Écrire la chanson
Write these songs|Diese Songs schreiben|Escribir estas canciones|Écrire ces chansons
Write remaining drafts|Fehlende Entwürfe schreiben|Escribir borradores pendientes|Écrire les brouillons restants
Stop writing|Schreiben stoppen|Detener escritura|Arrêter l’écriture
Saved on this computer|Auf diesem Computer gespeichert|Guardado en este equipo|Enregistré sur cet ordinateur
Your songs, your way.|Deine Songs, auf deine Art.|Tus canciones, a tu manera.|Vos chansons, à votre façon.
Start with a song. Organise it later.|Beginne mit einem Song. Organisiere ihn später.|Empieza con una canción. Organízala después.|Commencez par une chanson. Organisez-la ensuite.
Write independently, or gather songs around a theme and shape an album or EP.|Schreibe einzelne Songs oder sammle sie zu einem Thema für ein Album oder eine EP.|Escribe canciones independientes o reúnelas en torno a un tema para un álbum o EP.|Écrivez des chansons indépendantes ou réunissez-les autour d’un thème pour un album ou un EP.
Search songs|Songs suchen|Buscar canciones|Rechercher des chansons
No songs yet|Noch keine Songs|Aún no hay canciones|Aucune chanson pour le moment
No matching songs|Keine passenden Songs|No hay canciones coincidentes|Aucune chanson correspondante
Collection|Sammlung|Colección|Collection
Album|Album|Álbum|Album
EP|EP|EP|EP
Theme|Thema|Tema|Thème
Optional theme|Optionales Thema|Tema opcional|Thème facultatif
Manage collection|Sammlung verwalten|Gestionar colección|Gérer la collection
Songs: {n}|Songs: {n}|Canciones: {n}|Chansons : {n}
Export|Exportieren|Exportar|Exporter
Export songs|Songs exportieren|Exportar canciones|Exporter les chansons
Export song|Song exportieren|Exportar canción|Exporter la chanson
Export here|Hier exportieren|Exportar aquí|Exporter ici
Choose export folder|Exportordner wählen|Elegir carpeta de exportación|Choisir le dossier d’exportation
Save text and history|Text und Verlauf speichern|Guardar texto e historial|Enregistrer le texte et l’historique
Copied to clipboard.|In die Zwischenablage kopiert.|Copiado al portapapeles.|Copié dans le presse-papiers.
Exported to {path}|Exportiert nach {path}|Exportado a {path}|Exporté vers {path}
Song title|Songtitel|Título de la canción|Titre de la chanson
Working title|Arbeitstitel|Título provisional|Titre provisoire
Lyrics|Songtext|Letra|Paroles
Sound|Klang|Sonido|Son
Review|Überprüfen|Revisión|Révision
Style prompt|Stilbeschreibung|Descripción del estilo|Description du style
Exclusions|Ausschlüsse|Exclusiones|Exclusions
Vocal gender|Gesangsstimme|Voz|Voix
Weirdness %|Experimentierfreude %|Rareza %|Excentricité %
Style influence %|Stileinfluss %|Influencia del estilo %|Influence du style %
Variety level|Variationsgrad|Nivel de variedad|Niveau de variété
Lock|Sperren|Bloquear|Verrouiller
Lock fields to preserve them exactly during rewrites.|Sperre Felder, um sie bei Überarbeitungen exakt zu erhalten.|Bloquea campos para conservarlos exactamente al reescribir.|Verrouillez les champs à conserver exactement lors des réécritures.
Approve song|Song freigeben|Aprobar canción|Approuver la chanson
Reopen|Erneut öffnen|Reabrir|Rouvrir
Versions|Versionen|Versiones|Versions
Approved|Freigegeben|Aprobada|Approuvée
Not drafted|Noch kein Entwurf|Sin borrador|Pas encore de brouillon
Ready for review|Bereit zur Überprüfung|Lista para revisar|Prête à être révisée
Limit reached · review needed|Limit erreicht · Überprüfung nötig|Límite alcanzado · revisión necesaria|Limite atteinte · révision nécessaire
Rewrites: {used}/{limit}|Überarbeitungen: {used}/{limit}|Reescrituras: {used}/{limit}|Réécritures : {used}/{limit}
Feedback|Feedback|Comentarios|Commentaires
Describe what to change, or add listening notes from Suno.|Beschreibe Änderungen oder ergänze Hörnotizen aus Suno.|Describe los cambios o añade notas tras escuchar en Suno.|Décrivez les changements ou ajoutez vos notes d’écoute de Suno.
Rewrite song|Song überarbeiten|Reescribir canción|Réécrire la chanson
Song brief|Song-Idee|Idea de la canción|Idée de la chanson
Lyric language|Sprache des Songtexts|Idioma de la letra|Langue des paroles
Song count|Anzahl der Songs|Número de canciones|Nombre de chansons
Minimum length (seconds)|Mindestlänge (Sekunden)|Duración mínima (segundos)|Durée minimale (secondes)
Maximum length (seconds)|Höchstlänge (Sekunden)|Duración máxima (segundos)|Durée maximale (secondes)
AI rewrites per song|KI-Überarbeitungen pro Song|Reescrituras por canción|Réécritures par chanson
Collection (optional)|Sammlung (optional)|Colección (opcional)|Collection (facultative)
No collection|Keine Sammlung|Sin colección|Aucune collection
Create|Erstellen|Crear|Créer
Untitled song|Unbenannter Song|Canción sin título|Chanson sans titre
Write an original song from this brief.|Schreibe einen eigenen Song aus dieser Idee.|Escribe una canción original a partir de esta idea.|Écrivez une chanson originale à partir de cette idée.
Target: {minimum}–{maximum} seconds|Ziel: {minimum}–{maximum} Sekunden|Objetivo: {minimum}–{maximum} segundos|Objectif : {minimum}–{maximum} secondes
Duration is a writing target; Suno determines the audio length.|Die Dauer ist ein Schreibziel; Suno bestimmt die Audiolänge.|La duración orienta la escritura; Suno determina la duración del audio.|La durée guide l’écriture ; Suno détermine la durée de l’audio.
Name|Name|Nombre|Nom
Format|Format|Formato|Format
Choose songs and their running order. Their drafts and history stay intact.|Wähle Songs und Reihenfolge. Entwürfe und Verlauf bleiben erhalten.|Elige canciones y su orden. Los borradores y el historial se conservan.|Choisissez les chansons et leur ordre. Les brouillons et l’historique sont conservés.
Move up|Nach oben|Subir|Monter
Move down|Nach unten|Bajar|Descendre
Save collection|Sammlung speichern|Guardar colección|Enregistrer la collection
Organise song|Song zuordnen|Organizar canción|Organiser la chanson
Add this song to any collection. Unchecking removes only the membership.|Ordne diesen Song Sammlungen zu. Abwählen entfernt nur die Zuordnung.|Añade esta canción a cualquier colección. Desmarcar solo elimina la asociación.|Ajoutez cette chanson à des collections. Décocher retire uniquement l’association.
No collections yet. Create one from the sidebar.|Noch keine Sammlungen. Erstelle eine in der Seitenleiste.|Aún no hay colecciones. Crea una en la barra lateral.|Aucune collection. Créez-en une dans la barre latérale.
Appearance|Darstellung|Apariencia|Apparence
Colours|Farben|Colores|Couleurs
Follow Omarchy theme|Omarchy-Design folgen|Seguir tema de Omarchy|Suivre le thème d’Omarchy
Custom colours|Eigene Farben|Colores personalizados|Couleurs personnalisées
Background|Hintergrund|Fondo|Arrière-plan
Surface|Flächen|Superficie|Surfaces
Text|Text|Texto|Texte
Accent|Akzent|Acento|Accent
Restore theme colours|Designfarben wiederherstellen|Restaurar colores del tema|Restaurer les couleurs du thème
Colours affect Versework only. Theme changes are followed automatically.|Farben gelten nur für Versework. Designänderungen werden automatisch übernommen.|Los colores solo afectan a Versework. Los cambios del tema se siguen automáticamente.|Les couleurs concernent uniquement Versework. Les changements de thème sont suivis automatiquement.
Language|Sprache|Idioma|Langue
Interface language|Sprache der Oberfläche|Idioma de la interfaz|Langue de l’interface
System language|Systemsprache|Idioma del sistema|Langue du système
System language: {language}|Systemsprache: {language}|Idioma del sistema: {language}|Langue du système : {language}
Only the interface changes. Song text and lyric language stay unchanged.|Nur die Oberfläche ändert sich. Songtexte und deren Sprache bleiben unverändert.|Solo cambia la interfaz. La letra y su idioma no cambian.|Seule l’interface change. Les paroles et leur langue restent inchangées.
Local writing|Lokales Schreiben|Escritura local|Écriture locale
Local model|Lokales Modell|Modelo local|Modèle local
Check connection|Verbindung prüfen|Comprobar conexión|Vérifier la connexion
Start Ollama|Ollama starten|Iniciar Ollama|Démarrer Ollama
Checking local Ollama…|Lokales Ollama wird geprüft…|Comprobando Ollama local…|Vérification d’Ollama local…
Connected: {models}|Verbunden: {models}|Conectado: {models}|Connecté : {models}
No local models installed.|Keine lokalen Modelle installiert.|No hay modelos locales instalados.|Aucun modèle local installé.
Ollama is not installed. Run setup-ollama.sh first.|Ollama ist nicht installiert. Führe zuerst setup-ollama.sh aus.|Ollama no está instalado. Ejecuta setup-ollama.sh primero.|Ollama n’est pas installé. Exécutez d’abord setup-ollama.sh.
Ollama start requested. Check connection in a moment.|Ollama-Start angefordert. Prüfe gleich die Verbindung.|Se ha solicitado iniciar Ollama. Comprueba la conexión en un momento.|Démarrage d’Ollama demandé. Vérifiez la connexion dans un instant.
Choose a local model.|Wähle ein lokales Modell.|Elige un modelo local.|Choisissez un modèle local.
Only connects to Ollama on this computer.|Verbindet sich nur mit Ollama auf diesem Computer.|Solo se conecta a Ollama en este equipo.|Se connecte uniquement à Ollama sur cet ordinateur.
Settings saved.|Einstellungen gespeichert.|Ajustes guardados.|Paramètres enregistrés.
Edits saved.|Änderungen gespeichert.|Cambios guardados.|Modifications enregistrées.
Add feedback before requesting a rewrite.|Gib vor der Überarbeitung Feedback ein.|Añade comentarios antes de solicitar una reescritura.|Ajoutez des commentaires avant de demander une réécriture.
Finish or stop writing first.|Beende oder stoppe zuerst das Schreiben.|Termina o detén la escritura primero.|Terminez ou arrêtez d’abord l’écriture.
All drafts are written.|Alle Entwürfe sind fertig.|Todos los borradores están escritos.|Tous les brouillons sont écrits.
Connecting to {model}…|Verbinde mit {model}…|Conectando con {model}…|Connexion à {model}…
Writing song {number}/{count}…|Schreibe Song {number}/{count}…|Escribiendo canción {number}/{count}…|Écriture de la chanson {number}/{count}…
Writing song {number}/{count} · {size} characters|Schreibe Song {number}/{count} · {size} Zeichen|Escribiendo canción {number}/{count} · {size} caracteres|Écriture de la chanson {number}/{count} · {size} caractères
Drafts saved. Ready for review.|Entwürfe gespeichert. Bereit zur Überprüfung.|Borradores guardados. Listos para revisar.|Brouillons enregistrés. Prêts à être révisés.
Writing stopped. Completed drafts are saved.|Schreiben gestoppt. Fertige Entwürfe sind gespeichert.|Escritura detenida. Los borradores completos están guardados.|Écriture arrêtée. Les brouillons terminés sont enregistrés.
Stopping after Ollama responds…|Stoppe nach der Antwort von Ollama…|Deteniendo tras la respuesta de Ollama…|Arrêt après la réponse d’Ollama…
This song cannot be rewritten until reopened or its limit allows it.|Dieser Song ist gesperrt oder hat sein Limit erreicht.|Esta canción está aprobada o ha alcanzado su límite.|Cette chanson est approuvée ou a atteint sa limite.
Version history|Versionsverlauf|Historial de versiones|Historique des versions
Restoring never resets the rewrite counter.|Wiederherstellen setzt den Zähler nie zurück.|Restaurar nunca reinicia el contador de reescrituras.|La restauration ne réinitialise jamais le compteur de réécritures.
Version {number} · {kind} · {date}|Version {number} · {kind} · {date}|Versión {number} · {kind} · {date}|Version {number} · {kind} · {date}
Restore version|Version wiederherstellen|Restaurar versión|Restaurer la version
Version restored.|Version wiederhergestellt.|Versión restaurada.|Version restaurée.
initial|Erster Entwurf|Inicial|Initiale
rewrite|Überarbeitung|Reescritura|Réécriture
edit|Bearbeitung|Edición|Modification
restore|Wiederherstellung|Restauración|Restauration
male|Männlich|Masculina|Masculine
female|Weiblich|Femenina|Féminine
mixed|Gemischt|Mixta|Mixte
unspecified|Nicht festgelegt|Sin especificar|Non précisée
instrumental|Instrumental|Instrumental|Instrumentale
off|Aus|Desactivado|Désactivé
normal|Normal|Normal|Normal
high|Hoch|Alto|Élevé
extra|Extra|Extra|Extra
max|Maximum|Máximo|Maximum
'''
CATALOGUES = {code: {} for code in ['de', 'es', 'fr']}
for row in _ROWS.strip().splitlines():
    key, *values = row.split('|')
    for code, value in zip(CATALOGUES, values):
        CATALOGUES[code][key] = value
_language = 'en'


def system_language(env=None):
    env = os.environ if env is None else env
    base = env.get('LC_ALL') or env.get('LC_MESSAGES') or env.get('LANG') or 'en'
    if base in ('C', 'POSIX', 'C.UTF-8', 'C.utf8'):
        return 'en'
    candidates = (env.get('LANGUAGE', '') + ':' + base).split(':')
    for candidate in candidates:
        code = candidate.split('.')[0].split('_')[0].split('-')[0].lower()
        if code in ['en', *CATALOGUES]:
            return code
    return 'en'


def set_language(code):
    global _language
    _language = system_language() if code == 'system' else code


def t(message, **values):
    return CATALOGUES.get(_language, {}).get(message, message).format(**values)
