Attribute VB_Name = "CollectStudentEmails"
' =============================================================================
' CollectStudentEmails.bas
' Outlook 2019 VBA-Makro
'
' Funktionsweise:
'   1. Durchlaeuft alle E-Mails im Posteingang.
'   2. Sammelt alle Absenderadressen mit der Endung "@smail.th-koeln.de".
'   3. Ermittelt den Anzeigenamen des Absenders.
'   4. Schreibt die Ergebnisse in eine YAML-Datei (students.yaml) im Format:
'
'      students:
'        - name: "Max Mustermann"
'          smail: "m.mustermann@smail.th-koeln.de"
'          emails: []
'          folders: {}
'
'   Existiert die YAML-Datei bereits, werden nur neue Studierende ergaenzt
'   (bestehende Eintraege bleiben unveraendert).
'
' WICHTIG: Den Pfad zur YAML-Datei in YAML_FILE_PATH anpassen!
' =============================================================================

Option Explicit

' Pfad zur YAML-Ausgabedatei - bitte anpassen
Private Const YAML_FILE_PATH As String = "D:\TH_Koeln\academic-memory-mcp\students.yaml"

' E-Mail-Domain der Studierenden
Private Const STUDENT_DOMAIN As String = "@smail.th-koeln.de"

' =============================================================================
' Hauptprozedur
' =============================================================================

''' Scannt den Posteingang nach Studierenden-E-Mails und schreibt die
''' Ergebnisse in eine YAML-Datei. Bestehende Eintraege werden nicht
''' ueberschrieben, nur neue Studierende werden ergaenzt.
Public Sub CollectStudentEmails()
    Dim inbox      As Outlook.MAPIFolder
    Dim newStudents As Object   ' Dictionary: smail -> DisplayName
    Dim existing   As Object   ' Dictionary: smail -> True (bereits in YAML)

    Set inbox = Application.Session.GetDefaultFolder(olFolderInbox)
    If inbox Is Nothing Then
        MsgBox "Posteingang konnte nicht geoeffnet werden.", vbCritical, "CollectStudentEmails"
        Exit Sub
    End If

    ' Bereits vorhandene smail-Adressen aus YAML einlesen (um Duplikate zu vermeiden)
    Set existing = LoadExistingSmailAddresses(YAML_FILE_PATH)

    ' Neuen Studierenden aus Posteingang sammeln
    Set newStudents = CreateObject("Scripting.Dictionary")
    newStudents.CompareMode = 1 ' vbTextCompare

    Dim items As Outlook.items
    Dim item  As Object
    Dim i     As Long

    Set items = inbox.items

    For i = 1 To items.count
        Set item = items(i)
        If item.Class = olMail Then
            Dim addr As String
            Dim displayName As String
            addr = LCase(GetSenderEmailAddress(item))
            displayName = ""  ' GetSenderDisplayName(item)
            If Len(Trim(displayName)) = 0 Then
                displayName = NameFromSmailAddress(addr)
            End If

            If InStr(addr, STUDENT_DOMAIN) > 0 Then
                ' Nur aufnehmen wenn noch nicht in YAML und noch nicht gesammelt
                If Not existing.Exists(addr) And Not newStudents.Exists(addr) Then
                    newStudents.Add addr, displayName
                End If
            End If
        End If
    Next i

    If newStudents.count = 0 Then
        MsgBox "Keine neuen Studierenden-E-Mails gefunden." & vbCrLf & _
               "(Alle bekannten Adressen sind bereits in der YAML-Datei.)", _
               vbInformation, "CollectStudentEmails"
        Exit Sub
    End If

    ' Neue Studierende an YAML-Datei anhaengen
    AppendStudentsToYaml YAML_FILE_PATH, newStudents

    MsgBox "Fertig!" & vbCrLf & _
           newStudents.count & " neue Studierende in YAML geschrieben:" & vbCrLf & _
           YAML_FILE_PATH, vbInformation, "CollectStudentEmails"

    Set newStudents = Nothing
    Set existing = Nothing
End Sub

' =============================================================================
' YAML lesen / schreiben
' =============================================================================

''' Liest alle bereits vorhandenen smail-Adressen aus der YAML-Datei.
'''
''' Args:
'''     yamlPath: Pfad zur YAML-Datei.
'''
''' Returns:
'''     Dictionary mit smail-Adressen (Lowercase) als Keys, Value ist immer True.
'''     Leeres Dictionary wenn die Datei nicht existiert oder nicht lesbar ist.
Private Function LoadExistingSmailAddresses(ByVal yamlPath As String) As Object
    Dim dict As Object
    Set dict = CreateObject("Scripting.Dictionary")
    dict.CompareMode = 1

    If Len(Dir(yamlPath)) = 0 Then
        Set LoadExistingSmailAddresses = dict
        Exit Function
    End If

    Dim fso        As Object
    Dim fileStream As Object
    Set fso = CreateObject("Scripting.FileSystemObject")

    On Error GoTo ReadError
    Set fileStream = fso.OpenTextFile(yamlPath, 1, False, -2) ' -2 = SystemDefault
    
    Do While Not fileStream.AtEndOfStream
        Dim line As String
        line = Trim(fileStream.ReadLine())

        ' Suche nach "smail:" Zeilen
        If Left(line, 7) = "smail: " Then
            Dim addr As String
            addr = Trim(Mid(line, 8))
            ' Anfuehrungszeichen entfernen
            addr = Replace(addr, """", "")
            addr = LCase(addr)
            If Len(addr) > 0 And Not dict.Exists(addr) Then
                dict.Add addr, True
            End If
        End If
    Loop

    fileStream.Close

ReadError:
    Set LoadExistingSmailAddresses = dict
End Function

''' Haengt neue Studierende an die YAML-Datei an (oder erstellt sie neu).
'''
''' Schreibt UTF-8-kodiert via ADODB.Stream, damit Sonderzeichen in Namen
''' und Ordnerpfaden (ü, ö, ä, ...) korrekt gespeichert werden.
'''
''' Args:
'''     yamlPath:    Pfad zur YAML-Datei.
'''     newStudents: Dictionary mit smail (Key) -> DisplayName (Value).
Private Sub AppendStudentsToYaml(ByVal yamlPath As String, _
                                 ByVal newStudents As Object)
    On Error GoTo WriteError

    Dim fileExists As Boolean
    fileExists = (Len(Dir(yamlPath)) > 0)

    ' Bestehenden Inhalt einlesen oder Header vorbereiten
    Dim content As String
    If Not fileExists Then
        content = "students:" & vbLf
    Else
        Dim streamIn As Object
        Set streamIn = CreateObject("ADODB.Stream")
        streamIn.CharSet = "UTF-8"
        streamIn.Open
        streamIn.LoadFromFile yamlPath
        content = streamIn.ReadText
        streamIn.Close
        ' Sicherstellen dass Datei mit Zeilenumbruch endet
        If Right(content, 1) <> vbLf Then content = content & vbLf
    End If

    ' Neue Eintraege anhaengen
    Dim key As Variant
    For Each key In newStudents.Keys
        Dim smailAddr   As String
        Dim displayName As String
        smailAddr = CStr(key)
        displayName = Replace(CStr(newStudents(key)), """", "'")

        content = content & "  - name: """ & displayName & """" & vbLf
        content = content & "    smail: """ & smailAddr & """" & vbLf
        content = content & "    emails: []" & vbLf
        content = content & "    folders: []" & vbLf
        content = content & vbLf
    Next key

    ' UTF-8 ohne BOM schreiben
    Dim streamOut As Object
    Set streamOut = CreateObject("ADODB.Stream")
    streamOut.CharSet = "UTF-8"
    streamOut.Open
    streamOut.WriteText content
    ' BOM (ersten 3 Bytes) entfernen und als Binaerdatei speichern
    streamOut.Position = 0
    streamOut.Type = 1 ' adTypeBinary
    streamOut.Position = 3 ' UTF-8 BOM ueberspringen
    Dim streamFinal As Object
    Set streamFinal = CreateObject("ADODB.Stream")
    streamFinal.Type = 1
    streamFinal.Open
    streamOut.CopyTo streamFinal
    streamFinal.SaveToFile yamlPath, 2 ' 2 = adSaveCreateOverWrite
    streamOut.Close
    streamFinal.Close
    Exit Sub

WriteError:
    MsgBox "Fehler beim Schreiben der YAML-Datei: " & Err.Description, _
           vbCritical, "CollectStudentEmails"
End Sub

' =============================================================================
' Hilfsfunktionen
' =============================================================================

''' Gibt die tatsaechliche SMTP-Adresse eines Absenders zurueck.
''' (Identisch mit der gleichnamigen Funktion in EmailSorter.bas)
'''
''' Args:
'''     mail: Das MailItem, dessen Absenderadresse ermittelt werden soll.
'''
''' Returns:
'''     Die SMTP-E-Mail-Adresse als String (Lowercase), oder leerer String
'''     bei einem Fehler.
Private Function GetSenderEmailAddress(ByVal mail As Outlook.mailItem) As String
    On Error GoTo FallbackToProperty

    Dim addrEntry As Outlook.AddressEntry
    Set addrEntry = mail.Sender

    If Not addrEntry Is Nothing Then
        If addrEntry.AddressEntryUserType = olExchangeUserAddressEntry Or _
           addrEntry.AddressEntryUserType = olExchangeRemoteUserAddressEntry Then
            Dim exchUser As Outlook.ExchangeUser
            Set exchUser = addrEntry.GetExchangeUser()
            If Not exchUser Is Nothing Then
                GetSenderEmailAddress = LCase(exchUser.PrimarySmtpAddress)
                Exit Function
            End If
        End If
    End If

FallbackToProperty:
    GetSenderEmailAddress = LCase(mail.SenderEmailAddress)
End Function

''' Gibt den Anzeigenamen (DisplayName) des Absenders zurueck.
'''
''' Bevorzugt den Namen aus dem AddressEntry-Objekt; faellt auf
''' mail.SenderName zurueck wenn kein AddressEntry verfuegbar ist.
'''
''' Args:
'''     mail: Das MailItem, dessen Absendername ermittelt werden soll.
'''
''' Returns:
'''     Anzeigename als String, oder leerer String bei einem Fehler.
Private Function GetSenderDisplayName(ByVal mail As Outlook.mailItem) As String
    On Error GoTo FallbackToProperty

    Dim addrEntry As Outlook.AddressEntry
    Set addrEntry = mail.Sender

    If Not addrEntry Is Nothing Then
        If Len(Trim(addrEntry.name)) > 0 Then
            GetSenderDisplayName = Trim(addrEntry.name)
            Exit Function
        End If
    End If

FallbackToProperty:
    GetSenderDisplayName = Trim(mail.SenderName)
End Function

''' Leitet den Anzeigenamen eines Studierenden aus seiner smail-Adresse ab.
'''
''' Konvention: <vorname(n)>.<nachname(n)>@smail.th-koeln.de
'''   - "." trennt Vorname(n) von Nachname(n)
'''   - "_" trennt mehrere Vor- bzw. Nachnamen
'''
''' Beispiel:
'''   max_hans.maier_mustermann@smail.th-koeln.de
'''   -> "Max Hans Maier Mustermann"
'''
''' Args:
'''     smailAddr: Die vollstaendige smail-Adresse (Gross-/Kleinschreibung egal).
'''
''' Returns:
'''     Name als String mit kapitalisierten Woertern, oder leerer String
'''     wenn das Format nicht erkannt wird.
Private Function NameFromSmailAddress(ByVal smailAddr As String) As String
    ' Lokalteil extrahieren (vor dem @)
    Dim atPos As Long
    atPos = InStr(smailAddr, "@")
    If atPos < 2 Then
        NameFromSmailAddress = ""
        Exit Function
    End If
    Dim localPart As String
    localPart = Left(smailAddr, atPos - 1)

    ' Punkt als Trenner zwischen Vorname(n) und Nachname(n)
    Dim dotPos As Long
    dotPos = InStr(localPart, ".")
    If dotPos < 2 Then
        ' Kein Punkt -> gesamten Lokalteil als Namen verwenden
        NameFromSmailAddress = CapitalizeWords(Replace(localPart, "_", " "))
        Exit Function
    End If

    Dim firstPart  As String
    Dim secondPart As String
    firstPart = Left(localPart, dotPos - 1)
    secondPart = Mid(localPart, dotPos + 1)

    ' Unterstriche durch Leerzeichen ersetzen, dann kapitalisieren
    Dim fullName As String
    fullName = Replace(firstPart, "_", " ") & " " & Replace(secondPart, "_", " ")
    NameFromSmailAddress = CapitalizeWords(fullName)
End Function

''' Kapitalisiert jedes Wort eines durch Leerzeichen getrennten Strings.
'''
''' Args:
'''     s: Der zu bearbeitende String.
'''
''' Returns:
'''     String mit grossem Anfangsbuchstaben pro Wort.
Private Function CapitalizeWords(ByVal s As String) As String
    Dim words()  As String
    Dim i        As Long
    Dim result   As String

    s = Trim(s)
    ' Mehrfach-Leerzeichen normalisieren
    Do While InStr(s, "  ") > 0
        s = Replace(s, "  ", " ")
    Loop

    words = Split(LCase(s), " ")
    For i = 0 To UBound(words)
        If Len(words(i)) > 0 Then
            words(i) = UCase(Left(words(i), 1)) & Mid(words(i), 2)
        End If
    Next i
    CapitalizeWords = Join(words, " ")
End Function

''' Liest eine UTF-8-kodierte Textdatei zeilenweise und gibt den Inhalt
''' als String zurueck.
'''
''' FileSystemObject.OpenTextFile unterstuetzt kein UTF-8 ohne BOM auf
''' deutschen Windows-Systemen (SystemDefault = CP1252). ADODB.Stream
''' liest UTF-8 korrekt.
'''
''' Args:
'''     filePath: Vollstaendiger Pfad zur Datei.
'''
''' Returns:
'''     Gesamter Dateiinhalt als String, oder leerer String bei Fehler.
Private Function ReadUtf8File(ByVal filePath As String) As String
    On Error GoTo ReadErr
    Dim stream As Object
    Set stream = CreateObject("ADODB.Stream")
    stream.CharSet = "UTF-8"
    stream.Open
    stream.LoadFromFile filePath
    ReadUtf8File = stream.ReadText
    stream.Close
    Exit Function
ReadErr:
    ReadUtf8File = ""
End Function

