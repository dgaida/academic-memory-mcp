"""Utilities for semester and name normalization."""
import re
from datetime import datetime

def get_semester(date: datetime) -> str:
    """Bestimmt das Semester basierend auf dem Datum.

    Das Sommersemester (SoSe) läuft von April bis September.
    Das Wintersemester (WS) läuft von Oktober bis März.

    Args:
        date (datetime): Das Datum, für das das Semester bestimmt werden soll.

    Returns:
        str: Die Semesterbezeichnung im Format 'YYYY_SoSe' oder 'YYYY_YY_WS'.
    """
    year = date.year
    month = date.month
    if 4 <= month <= 9:
        return f"{year}_SoSe"
    else:
        if month <= 3:
            return f"{year-1}_{str(year)[2:]}_WS"
        else:
            return f"{year}_{str(year+1)[2:]}_WS"

def normalize_name(name: str) -> str:
    """Normalisiert Namen durch Ersetzung von Umlauten und Sonderzeichen.

    Ersetzt deutsche Umlaute (ä, ö, ü, ß) durch ihre ASCII-Entsprechungen
    und wandelt alle nicht-alphanumerischen Zeichen in Unterstriche um.

    Args:
        name (str): Der zu normalisierende Name.

    Returns:
        str: Der normalisierte Name.
    """
    replacements = {
        'ä': 'ae', 'ö': 'oe', 'ü': 'ue',
        'Ä': 'Ae', 'Ö': 'Oe', 'Ü': 'Ue',
        'ß': 'ss'
    }
    res = name
    for k, v in replacements.items():
        res = res.replace(k, v)
    # Entferne Sonderzeichen
    res = re.sub(r'[^a-zA-Z0-9_]', '_', res)
    return res
