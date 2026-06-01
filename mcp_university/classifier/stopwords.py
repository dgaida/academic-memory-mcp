"""Stoppwörter für die E-Mail-Klassifizierung."""

GERMAN_STOP_WORDS = [
    "aber", "alle", "allem", "allen", "aller", "alles", "als", "also", "am", "an",
    "ander", "andere", "anderem", "anderen", "anderer", "anderes", "anderm",
    "andern", "anderr", "anders", "auch", "auf", "aus", "bei", "bin", "bis",
    "bist", "da", "damit", "dann", "der", "den", "des", "dem", "die", "das",
    "daß", "dass", "derselbe", "derselben", "denselben", "desselben", "demselben",
    "dieselbe", "dieselben", "dasselbe", "dazu", "dein", "deine", "deinem",
    "deinen", "deiner", "deines", "denn", "derer", "dessen", "dich", "dir",
    "du", "dies", "diese", "diesem", "diesen", "dieser", "dieses", "doch",
    "dort", "durch", "ein", "eine", "einem", "einen", "einer", "eines",
    "einig", "einige", "einigem", "einigen", "einiger", "einiges", "einmal",
    "er", "ihn", "ihm", "es", "etwas", "euch", "euer", "eure", "eurem",
    "euren", "eurer", "eures", "für", "gegen", "gewesen", "hab", "habe",
    "haben", "hat", "hatte", "hatten", "hier", "hin", "hinter", "ich",
    "mich", "mir", "ihr", "ihre", "ihrem", "ihren", "ihrer", "ihres",
    "im", "in", "indem", "ins", "ist", "jede", "jedem", "jeden", "jeder",
    "jedes", "jene", "jenem", "jenen", "jener", "jenes", "jetzt", "kann",
    "kein", "keine", "keinem", "keinen", "keiner", "keines", "können",
    "könnte", "machen", "man", "manche", "manchem", "manchen", "mancher",
    "manches", "mein", "meine", "meinem", "meinen", "meiner", "meines",
    "mit", "muss", "musste", "nach", "nicht", "nichts", "noch", "nun",
    "nur", "ob", "oder", "ohne", "sehr", "sein", "seine", "seinem",
    "seinen", "seiner", "seines", "selbst", "sich", "sie", "ihnen",
    "sind", "so", "solche", "solchem", "solchen", "solcher", "solches",
    "soll", "sollte", "sondern", "sonst", "über", "uhr", "um", "und", "uns",
    "unsere", "unserem", "unseren", "unser", "unseres", "unter", "viel",
    "vom", "von", "vor", "während", "war", "waren", "warst", "was",
    "weg", "weil", "weiter", "welche", "welchem", "welchen", "welcher",
    "welches", "wenn", "werde", "werden", "wie", "wieder", "will",
    "wir", "wird", "wirst", "wo", "wollen", "wollte", "würde", "würden", "www", 
    "zu", "zum", "zur", "zwar", "zwischen"
]

ENGLISH_STOP_WORDS = [
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "as", "at", "be", "because", "been", "before", "being", "below",
    "between", "both", "but", "by", "can", "could", "date", "did", "do", "does", "doing",
    "down", "during", "each", "few", "for", "from", "further", "had", "has",
    "have", "having", "he", "her", "here", "hers", "herself", "him", "himself",
    "his", "how", "i", "if", "in", "into", "is", "it", "its", "itself", "just",
    "me", "more", "most", "my", "myself", "no", "nor", "not", "now", "of", "off",
    "on", "once", "only", "or", "other", "ought", "our", "ours", "ourselves",
    "out", "over", "own", "same", "she", "should", "so", "some", "such", "than",
    "that", "the", "their", "theirs", "them", "themselves", "then", "there",
    "these", "they", "this", "those", "through", "to", "too", "under", "until",
    "up", "very", "was", "we", "were", "what", "when", "where", "which", "while",
    "who", "whom", "why", "with", "would", "you", "your", "yours", "yourself",
    "yourselves"
]

UNIVERSITY_STOP_WORDS = [
    "th", "koeln", "de", "gaida", "viele", "grüße", "grüßen", "signatur", "nachricht",
    "mail", "smail", "mailto", "hallo", "geehrte", "geehrter", "mfg", "vg", "daniel", "professor",
    "hochschule", "technische", "re", "aw", "fwd", "gesendet", "gm", "gummersbach", 
    "datum", "betreff", "an", "von", "herr", "frau", "mit", "vielen", "herzlichen",
    "max", "mustermann", "prof", "subject", "49", "freundlichen", "https", "http"
]

ALL_STOP_WORDS = list(set(GERMAN_STOP_WORDS + ENGLISH_STOP_WORDS + UNIVERSITY_STOP_WORDS))
