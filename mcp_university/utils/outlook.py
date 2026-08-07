"""Outlook-spezifische Hilfsfunktionen."""

import html
import logging
import platform
import re
import subprocess
from pathlib import Path
from typing import List

try:
    import win32com.client
    OUTLOOK_AVAILABLE = True
except ImportError:
    OUTLOOK_AVAILABLE = False

from mcp_university.config import get_config

logger = logging.getLogger(__name__)

def is_outlook_open() -> bool:
    """Prüft, ob Outlook aktuell geöffnet ist.

    Returns:
        bool: True wenn Outlook läuft, sonst False.
    """
    system = platform.system()
    try:
        if system == "Windows":
            # Prüfe mit tasklist unter Windows
            output = subprocess.check_output(
                'tasklist /FI "IMAGENAME eq outlook.exe"',
                shell=True,
                stderr=subprocess.STDOUT,
            )
            return b"outlook.exe" in output.lower()
        elif system == "Darwin":  # macOS
            # Prüfe mit pgrep unter macOS
            try:
                subprocess.check_call(["pgrep", "-x", "Microsoft Outlook"])
                return True
            except subprocess.CalledProcessError:
                return False
        else:
            return False
    except Exception:
        return False

def create_outlook_draft(
    subject: str,
    body: str,
    recipient: str = "",
    cc: List[str] = None,
    attachments: List[Path] = None,
    use_signature: bool = True,
) -> bool:
    """Erstellt einen E-Mail-Entwurf in Outlook.

    Args:
        subject (str): Betreff der E-Mail.
        body (str): Inhalt der E-Mail (Flachtext/Markdown).
        recipient (str): Empfänger-Adresse.
        cc (List[str], optional): Liste der CC-Adressen. Defaults to None.
        attachments (List[Path], optional): Liste der Dateipfade für Anhänge. Defaults to None.
        use_signature (bool, optional): Ob die Standard-Outlook-Signatur geladen und angehängt werden soll. Defaults to True.

    Returns:
        bool: True wenn erfolgreich, sonst False.
    """
    if not OUTLOOK_AVAILABLE:
        logger.info("pywin32 nicht installiert. Outlook-Draft nicht möglich.")
        return False

    if not is_outlook_open():
        logger.info("Outlook ist nicht geöffnet.")
        return False

    try:
        outlook = win32com.client.Dispatch("Outlook.Application")
        namespace = outlook.GetNamespace("MAPI")

        target_account = get_config().user.email
        target_folder_name = "Work in Progress"

        # Versuche den spezifischen Ordner zu finden
        target_folder = None
        try:
            for store in namespace.Stores:
                if store.DisplayName == target_account:
                    root = store.GetRootFolder()
                    logger.info(f"Verfügbare Ordner in {target_account}:")
                    for folder in root.Folders:
                        logger.info(f" - {folder.Name}")
                        if folder.Name.lower() == target_folder_name.lower():
                            target_folder = folder
                            break

                    if not target_folder:
                        # Suche in Posteingang
                        for folder in root.Folders:
                            if folder.Name.lower() in ["posteingang", "inbox"]:
                                logger.info(f"Suche in {folder.Name}...")
                                for sub in folder.Folders:
                                    logger.info(f"   - {sub.Name}")
                                    if sub.Name.lower() == target_folder_name.lower():
                                        target_folder = sub
                                        break
                            if target_folder:
                                break
                    if target_folder:
                        break
        except Exception as e:
            logger.warning(f"Fehler beim Suchen des Zielordners: {e}")

        if target_folder:
            mail = target_folder.Items.Add(0)  # 0 = olMailItem
            logger.info(
                f"Erstelle Entwurf direkt in {target_account} -> {target_folder_name}."
            )
        else:
            mail = outlook.CreateItem(0)
            logger.warning(
                f"Zielordner {target_folder_name} nicht gefunden. Erstelle in Standard-Entwürfen."
            )

        mail.Subject = subject

        if use_signature:
            try:
                # GetInspector initialisiert die Mail und lädt die Standard-Signatur
                _ = mail.GetInspector

                sig_html = mail.HTMLBody
                sig_text = mail.Body

                # HTML Formatierung vorbereiten (Sonderzeichen escapen, Zeilenumbrüche konvertieren)
                body_html = html.escape(body).replace("\n", "<br/>")

                # Wenn eine HTML-Signatur vorhanden ist, fügen wir den Text davor ein
                if sig_html and "<body" in sig_html.lower():
                    body_match = re.search(r"<body[^>]*>", sig_html, re.IGNORECASE)
                    if body_match:
                        index = body_match.end()
                        mail.HTMLBody = sig_html[:index] + body_html + "<br/><br/>" + sig_html[index:]
                    else:
                        mail.HTMLBody = body_html + "<br/><br/>" + sig_html
                else:
                    if sig_html:
                        mail.HTMLBody = body_html + "<br/><br/>" + sig_html
                    elif sig_text:
                        mail.Body = body + "\n\n" + sig_text
                    else:
                        mail.Body = body
            except Exception as sig_err:
                logger.warning(f"Fehler beim Abrufen/Einfügen der Signatur: {sig_err}. Verwende Standard-Body.")
                mail.Body = body
        else:
            mail.Body = body

        if attachments:
            for attachment_path in attachments:
                if attachment_path.exists():
                    mail.Attachments.Add(str(attachment_path))
        if recipient:
            mail.To = recipient
        if cc:
            mail.CC = "; ".join(cc)

        mail.Save()
        mail.Display(False)

        return True
    except Exception as e:
        logger.error(f"Fehler beim Erstellen des Outlook-Entwurfs: {e}")
        return False
