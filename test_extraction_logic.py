import re

def _norm(s: str) -> str:
    if not s:
        return ""
    s = s.lower()
    repl = {"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"}
    for k, v in repl.items():
        s = s.replace(k, v)
    return re.sub(r"[^a-z0-9]", "", s)

def _format_name(s: str) -> str:
    if not s:
        return ""
    s = s.replace("_", " ")
    parts = s.split()
    formatted = []
    for p in parts:
        if "-" in p:
            formatted.append("-".join(sub[0].upper() + sub[1:] for sub in p.split("-") if sub))
        elif any(c.isupper() for c in p) and not p.isupper():
            formatted.append(p)
        else:
            formatted.append(p[0].upper() + p[1:] if p else "")
    return " ".join(formatted)

GENERIC = {"info", "sekretariat", "service", "kontakt", "studium", "pruefungsamt", "of", "the", "f10-request"}

def extract_lastname(sender_raw: str) -> str:
    if not sender_raw or sender_raw == "(No Sender)":
        return "Unknown"
    if "im Auftrag von" in sender_raw:
        sender_raw = re.split(r";\s*im Auftrag von[;:]?\s*", sender_raw, flags=re.IGNORECASE)[-1].strip()

    match = re.match(r"^(.*?)\s*<([^>]+)>", sender_raw)
    if match:
        display_name = match.group(1).strip().strip("'").strip('"')
        local_part = match.group(2).strip().split("@")[0]
    else:
        if "@" in sender_raw:
            local_part = sender_raw.split("@")[0]
            display_name = ""
        else:
            display_name = sender_raw.strip().strip("'").strip('"')
            local_part = ""

    # Rule: "Lastname, Firstname"
    if "," in display_name:
        parts = [p.strip() for p in display_name.split(",")]
        if len(parts) > 1:
            return _format_name(parts[0])

    clean_display = re.sub(r"[\(\)\|]", " ", display_name)
    if "//" in clean_display:
        clean_display = clean_display.split("//")[-1].strip()
    clean_display = re.sub(r"\b(B\.Sc\.|M\.Sc\.|Dr\.|Prof\.|Dipl\.-Ing\.)\b", "", clean_display)
    name_parts = [p for p in clean_display.split() if p]

    if name_parts and local_part:
        norm_lp = _norm(local_part)
        # HWester check
        if _norm(name_parts[0]) not in norm_lp and len(name_parts) > 1:
            return _format_name(local_part)

        # Greedy match from right
        for i in range(len(name_parts)):
            for j in range(len(name_parts), i, -1):
                cand = " ".join(name_parts[i:j])
                if _norm(cand) in norm_lp:
                    # Is this the sequence matching the end of LP?
                    if _norm(cand) == norm_lp or norm_lp.endswith(_norm(cand)):
                        return _format_name(cand)
                    # Or just greedily match from right
                    return _format_name(cand)

    if local_part:
        if "." in local_part:
            segs = local_part.split(".")
            for s in reversed(segs):
                if _norm(s) not in GENERIC:
                    return _format_name(s)
        if _norm(local_part) not in GENERIC:
            return _format_name(local_part)

    if name_parts:
        return _format_name(name_parts[-1])
    return "Unknown"

def extract_firstname(sender_raw: str) -> str:
    name_parts, local_part = [], ""
    if "im Auftrag von" in sender_raw:
        sender_raw = re.split(r";\s*im Auftrag von[;:]?\s*", sender_raw, flags=re.IGNORECASE)[-1].strip()
    match = re.match(r"^(.*?)\s*<([^>]+)>", sender_raw)
    if match:
        display_name = match.group(1).strip().strip("'").strip('"')
        local_part = match.group(2).strip().split("@")[0]
    else:
        if "@" in sender_raw:
            local_part = sender_raw.split("@")[0]
            display_name = ""
        else:
            display_name = sender_raw.strip().strip("'").strip('"')
            local_part = ""
    clean_display = re.sub(r"[\(\),\|]", " ", display_name)
    clean_display = re.sub(r"\b(B\.Sc\.|M\.Sc\.|Dr\.|Prof\.|Dipl\.-Ing\.)\b", "", clean_display)
    name_parts = [p for p in clean_display.split() if p]
    
    if name_parts and local_part:
        lp_n = _norm(local_part)
        lastname = extract_lastname(sender_raw)
        ln_n = _norm(lastname)
        firsts = []
        for p in name_parts:
            if _norm(p) == ln_n:
                break
            if _norm(p) in lp_n or (len(_norm(p))==1 and lp_n.startswith(_norm(p))):
                firsts.append(p)
        if firsts:
            return _format_name(" ".join(firsts))
    
    if local_part and "." in local_part:
        return _format_name(local_part.split(".")[0])
    if name_parts:
        return _format_name(name_parts[0])
    return "Unknown"

if __name__ == "__main__":
    test_cases = [
        ("max.muster@smail.th-koeln.de", "Max", "Muster"),
        ("max_hans.muster@smail.th-koeln.de", "Max Hans", "Muster"),
        ("max.muster_hase@smail.th-koeln.de", "Max", "Muster Hase"),
        ("max.muster-hase@smail.th-koeln.de", "Max", "Muster-Hase"),
        ("hans-peter.muster-hase@smail.th-koeln.de", "Hans-Peter", "Muster-Hase"),
        ("max_hans.muster_hase@smail.th-koeln.de", "Max Hans", "Muster Hase"),
        ("Angela Spaß (aspass) <angela.spass@smail.th-koeln.de>", "Angela", "Spaß"),
        ("studium-gm@th-koeln.de", "Unknown", "Studium-Gm"),
        ("f10-request@f10.th-koeln.de; im Auftrag von; Marcel Mueller, B.Sc. <marcel.mueller@th-koeln.de>", "Marcel", "Mueller"),
        ("Sabrina Tuba <stuba@fft.com>", "Sabrina", "Tuba"),
        ("stuba@fft.com", "Unknown", "Stuba"),
        ("Mustermann Max <mustermann@example.com>", "Max", "Mustermann"),
        ("Max Mustermann <mustermann@example.com>", "Max", "Mustermann"),
        ("Wester Helmut <HWester@tuev.com>", "Helmut", "HWester"),
        ("A B C D <a_b.c_d@smail.th-koeln.de>", "A B", "C D"),
        ("'Anna Pizza Sibel' <anna.pizza_sibel@smail.th-koeln.de>", "Anna", "Pizza Sibel"),
        ("'Digital Sciences (Ma) Management Board' <digital-sciences@f10.th-koeln.de>", "Unknown", "Digital-Sciences"),
        ("eRechnung TH Köln <kreditorenbuchhaltung@th-koeln.de>", "Unknown", "Kreditorenbuchhaltung"),
        ("TH // chris.hase@th-koeln.de", "Chris", "Hase"),
        ("'Eva Adam | Hans GmbH' <eva.adam@hans-gmbh.com>", "Eva", "Adam"),
        ("Dampf, Hans <dampf@fh-aachen.de>", "Hans", "Dampf"),
    ]

    for inp, exp_f, exp_l in test_cases:
        res_f = extract_firstname(inp)
        res_l = extract_lastname(inp)
        status = "PASS" if res_f==exp_f and res_l==exp_l else "FAIL"
        print(f"{status} | In: {inp[:40]:40} | Exp: {exp_f:10}, {exp_l:15} | Got: {res_f:10}, {res_l:15}")
