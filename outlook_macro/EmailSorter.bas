' =============================================================================
' EmailSorter.bas
' Outlook 2019 VBA-Makro
'
' Funktionsweise:
'   1. Liest eine YAML-Datei (students.yaml) ein, die fuer jeden Studierenden
'      Name, smail, weitere E-Mails sowie einen Ordner-Map mit Keywords enthaelt.
'   2. Durchlaeuft alle E-Mails im Posteingang und in Gesendeten Elementen.
'   3. Ordnet jede Mail einem Studierenden zu (ueber Absender-/Empfaengeradresse).
'   4. Sucht den Betreff und Textkoerper der Mail nach den Ordner-Keywords ab.
'      Der erste Treffer bestimmt den Zielordner.
'   5. Speichert die Mail als .msg-Datei im gefundenen Ordner.
'   6. Behaelt pro Absender nur die neueste Mail; aeltere werden nach dem Export
'      geloescht.
'
' YAML-Format (students.yaml):
'   students:
'     - name: "Max Mustermann"
'       smail: "m.mustermann@smail.th-koeln.de"
'       emails:
'         - "max@privat.de"
'       folders:
'         Bachelorthesis: "C:\\Ablage\\Mustermann\\Bachelorthesis"
'         Praxisprojekt:  "C:\\Ablage\\Mustermann\\Praxisprojekt"
'
' WICHTIG: Den Pfad zur YAML-Datei in YAML_FILE_PATH anpassen!
' =============================================================================

Option Explicit

' Pfad zur YAML-Konfigurationsdatei - bitte anpassen
Private Const YAML_FILE_PATH As String = "D:\TH_Koeln\academic-memory-mcp\students.yaml"

' Trennzeichen zwischen E-Mail-Adresse und Ordnerpfad (wird nur noch fuer
' den Legacy-Fallback ReadEmailConfig benoetigt, falls jemand die MD-Datei
' weiterhin nutzen moechte)
Private Const MIN_SPACES_AS_SEPARATOR As Integer = 2

' =============================================================================
' Hauptprozedur - Einstiegspunkt des Makros
' =============================================================================

''' Hauptprozedur: Liest die YAML-Konfiguration und exportiert E-Mails aus dem
''' Posteingang und den Gesendeten Elementen als .msg-Dateien auf das Dateisystem.
'''
''' Fuer jeden Studierenden wird der Betreff und Textkoerper jeder E-Mail nach
''' den in der YAML definierten Ordner-Keywords durchsucht.  Der erste Treffer
''' bestimmt den Zielordner.
Public Sub SortInboxByConfig()
    Dim studentMap As Object    ' Dictionary: email_lower -> StudentEntry-Array
    Dim inbox      As Outlook.MAPIFolder
    Dim sentItems  As Outlook.MAPIFolder

    If Not FileExists(YAML_FILE_PATH) Then
        MsgBox "YAML-Datei nicht gefunden:" & vbCrLf & YAML_FILE_PATH, _
               vbCritical, "EmailSorter"
        Exit Sub
    End If

    Set studentMap = ReadStudentMap(YAML_FILE_PATH)
    If studentMap Is Nothing Then
        MsgBox "Fehler beim Einlesen der YAML-Datei.", vbCritical, "EmailSorter"
        Exit Sub
    End If

    If studentMap.Count = 0 Then
        MsgBox "Keine gueltigen Eintraege in der YAML-Datei gefunden.", _
               vbExclamation, "EmailSorter"
        Exit Sub
    End If

    Set inbox = Application.Session.GetDefaultFolder(olFolderInbox)
    Set sentItems = Application.Session.GetDefaultFolder(olFolderSentMail)

    If inbox Is Nothing Or sentItems Is Nothing Then
        MsgBox "Posteingang oder Gesendete Elemente konnten nicht gefunden werden.", _
               vbCritical, "EmailSorter"
        Exit Sub
    End If

    Dim savedCount   As Long
    Dim deletedCount As Long

    ProcessFolder inbox, studentMap, "Inbox", False, savedCount, deletedCount
    ProcessFolder sentItems, studentMap, "SentItems", True, savedCount, deletedCount

    MsgBox "Fertig!" & vbCrLf & _
           "Exportiert: " & savedCount & " E-Mail(s)" & vbCrLf & _
           "Geloescht (Duplikate): " & deletedCount & " E-Mail(s)", _
           vbInformation, "EmailSorter"

    Set studentMap = Nothing
End Sub

' =============================================================================
' YAML-Konfiguration einlesen
' =============================================================================

''' Liest die students.yaml ein und gibt ein Dictionary zurueck, das jede
''' bekannte E-Mail-Adresse auf ein foldersDict abbildet.
'''
''' foldersDict: Scripting.Dictionary  keyword_lower -> folder_path
'''   Alle Keywords aus der keys-Liste jedes folder-Eintrags werden als
'''   einzelne Keys eingetragen und zeigen auf denselben Ordnerpfad.
'''
''' Args:
'''     yamlPath: Vollstaendiger Pfad zur YAML-Datei.
'''
''' Returns:
'''     Scripting.Dictionary  email_lower -> foldersDict,
'''     oder Nothing bei einem Fehler.
Private Function ReadStudentMap(ByVal yamlPath As String) As Object
    Dim result As Object
    Set result = CreateObject("Scripting.Dictionary")
    result.CompareMode = 1 ' vbTextCompare

    Dim fso        As Object
    Dim fileStream As Object
    Set fso = CreateObject("Scripting.FileSystemObject")

    On Error GoTo ReadError
    ' Set fileStream = fso.OpenTextFile(yamlPath, 1, False, -2)
    Dim fileContent As String
    fileContent = ReadUtf8File(yamlPath)
    If Len(fileContent) = 0 Then GoTo ReadError

    Dim allLines() As String
    allLines = Split(fileContent, vbLf)

    ' Zustand des Parsers
    ' foldersDict: keyword_lower -> folder_path
    '   Jeder Eintrag der keys-Liste wird als eigenstaendiger Key gespeichert,
    '   alle zeigen auf denselben Pfad.
    Dim smailAddr   As String
    Dim allAddrs    As Object   ' Collection aller Adressen dieses Studierenden
    Dim foldersDict As Object   ' keyword_lower -> folder_path
    Dim inFolders   As Boolean
    Dim inEmails    As Boolean
    Dim inFolderEntry As Boolean
    Dim currentEntryPath As String  ' Pfad des aktuellen folder-Eintrags
    Dim currentEntryKeys As String  ' Kommagetrennte Keys des aktuellen Eintrags

    smailAddr = ""
    Set allAddrs = New Collection
    Set foldersDict = CreateObject("Scripting.Dictionary")
    foldersDict.CompareMode = 1
    inFolders = False
    inEmails = False
    inFolderEntry = False
    currentEntryPath = ""
    currentEntryKeys = ""

    ' Do While Not fileStream.AtEndOfStream
    Dim iLine As Long
    For iLine = 0 To UBound(allLines)
        Dim line    As String
        Dim trimmed As String
        Dim lineIndent As Long
        ' line = fileStream.ReadLine()
        line = allLines(iLine)
        ' Windows-Zeilenenden: \r\n -> \r entfernen
        If Right(line, 1) = vbCr Then line = Left(line, Len(line) - 1)
        trimmed = Trim(line)
        lineIndent = Len(line) - Len(LTrim(line))

        ' Studierenden-Block (Einrueckung 2)
        If Left(trimmed, 2) = "- " And lineIndent = 2 Then
            ' Laufenden folder-Eintrag abschliessen
            CommitFolderEntry foldersDict, currentEntryKeys, currentEntryPath
            currentEntryKeys = ""
            currentEntryPath = ""
            ' Vorherigen Studierenden speichern
            If Len(smailAddr) > 0 And foldersDict.Count > 0 Then
                CommitStudentEntry result, smailAddr, allAddrs, foldersDict
            End If
            ' Zustand zuruecksetzen
            smailAddr = ""
            Set allAddrs = New Collection
            Set foldersDict = CreateObject("Scripting.Dictionary")
            foldersDict.CompareMode = 1
            inFolders = False
            inEmails = False
            inFolderEntry = False
            GoTo NextLine
        End If

        If Left(trimmed, 6) = "smail:" Then
            smailAddr = LCase(Replace(Trim(Mid(trimmed, 7)), """", ""))
            If Len(smailAddr) > 0 Then allAddrs.Add smailAddr
            inFolders = False
            inEmails = False
            inFolderEntry = False
            GoTo NextLine
        End If

        If Left(trimmed, 7) = "emails:" Then
            Dim emailsRaw As String
            emailsRaw = Trim(Mid(trimmed, 8))
            If Left(emailsRaw, 1) = "[" Then
                emailsRaw = Replace(Replace(emailsRaw, "[", ""), "]", "")
                emailsRaw = Replace(emailsRaw, """", "")
                Dim emailParts() As String
                emailParts = Split(emailsRaw, ",")
                Dim ep As Variant
                For Each ep In emailParts
                    Dim eAddr As String
                    eAddr = LCase(Trim(CStr(ep)))
                    If Len(eAddr) > 0 Then allAddrs.Add eAddr
                Next ep
                inEmails = False
            Else
                inEmails = True
            End If
            inFolders = False
            inFolderEntry = False
            GoTo NextLine
        End If

        If inEmails And Left(trimmed, 2) = "- " Then
            Dim blockAddr As String
            blockAddr = LCase(Replace(Trim(Mid(trimmed, 3)), """", ""))
            If Len(blockAddr) > 0 Then allAddrs.Add blockAddr
            GoTo NextLine
        End If

        If Left(trimmed, 8) = "folders:" Then
            Dim foldersRaw As String
            foldersRaw = Trim(Mid(trimmed, 9))
            ' folders: []  oder  folders:  -> Listenstruktur erwartet
            inFolders = True
            inEmails = False
            inFolderEntry = False
            GoTo NextLine
        End If

        ' Neuer folder-Eintrag (Einrueckung 6, beginnt mit "- ")
        If inFolders And Left(trimmed, 2) = "- " And lineIndent = 6 Then
            ' Vorherigen Eintrag abschliessen
            CommitFolderEntry foldersDict, currentEntryKeys, currentEntryPath
            currentEntryKeys = ""
            currentEntryPath = ""
            inFolderEntry = True
            Dim afterDash As String
            afterDash = Trim(Mid(trimmed, 3))
            If Left(afterDash, 5) = "keys:" Then
                currentEntryKeys = Trim(Mid(afterDash, 6))
            ElseIf Left(afterDash, 5) = "path:" Then
                currentEntryPath = Replace(Replace(Trim(Mid(afterDash, 6)), """", ""), "\\", "\")
            End If
            GoTo NextLine
        End If

        ' Felder innerhalb eines folder-Eintrags (Einrueckung 8)
        If inFolderEntry And lineIndent = 8 Then
            If Left(trimmed, 5) = "keys:" Then
                currentEntryKeys = Trim(Mid(trimmed, 6))
            ElseIf Left(trimmed, 5) = "path:" Then
                currentEntryPath = Replace(Replace(Trim(Mid(trimmed, 6)), """", ""), "\\", "\")
            End If
            GoTo NextLine
        End If

NextLine:
    Next iLine  ' Loop

    ' Letzten folder-Eintrag und Studierenden abschliessen
    CommitFolderEntry foldersDict, currentEntryKeys, currentEntryPath
    If Len(smailAddr) > 0 And foldersDict.Count > 0 Then
        CommitStudentEntry result, smailAddr, allAddrs, foldersDict
    End If

    ' fileStream.Close
    Set ReadStudentMap = result
    Exit Function

ReadError:
    MsgBox "Fehler beim Lesen der YAML-Datei: " & Err.Description, vbCritical, "EmailSorter"
    If Not fileStream Is Nothing Then fileStream.Close
    Set ReadStudentMap = Nothing
End Function

''' Parst die keys-Liste eines folder-Eintrags und traegt alle Keywords mit
''' dem zugehoerigen Pfad in foldersDict ein.
'''
''' Args:
'''     foldersDict: Ziel-Dictionary keyword_lower -> folder_path.
'''     keysRaw:     Roher keys-String, z.B. ["Bachelorthesis", "Bachelorarbeit"].
'''     folderPath:  Der zugehoerige Ordnerpfad.
Private Sub CommitFolderEntry(ByVal foldersDict As Object, _
                              ByVal keysRaw As String, _
                              ByVal folderPath As String)
    If Len(Trim(keysRaw)) = 0 Or Len(Trim(folderPath)) = 0 Then Exit Sub

    ' Eckige Klammern und Anfuehrungszeichen entfernen
    Dim cleaned As String
    cleaned = Replace(Replace(keysRaw, "[", ""), "]", "")
    cleaned = Replace(cleaned, """", "")

    Dim parts() As String
    parts = Split(cleaned, ",")
    Dim p As Variant
    For Each p In parts
        Dim kw As String
        kw = LCase(Trim(CStr(p)))
        If Len(kw) > 0 Then
            If Not foldersDict.Exists(kw) Then
                foldersDict.Add kw, folderPath
            End If
        End If
    Next p
End Sub

''' Traegt alle Adressen eines Studierenden mit ihrem foldersDict in das
''' Ergebnis-Dictionary ein.
'''
''' Das foldersDict bildet keyword_lower -> folder_path ab; jedes Keyword
''' aus der keys-Liste eines Ordner-Eintrags ist ein eigener Key.
'''
''' Args:
'''     result:      Das Ziel-Dictionary (email -> foldersDict).
'''     smailAddr:   Die smail-Adresse des Studierenden.
'''     allAddrs:    Collection aller bekannten Adressen (inkl. smail).
'''     foldersDict: Dictionary keyword_lower -> folder_path.
Private Sub CommitStudentEntry(ByVal result As Object, _
                               ByVal smailAddr As String, _
                               ByVal allAddrs As Collection, _
                               ByVal foldersDict As Object)
    Dim addr As Variant
    For Each addr In allAddrs
        Dim addrStr As String
        addrStr = LCase(CStr(addr))
        If Len(addrStr) > 0 And Not result.Exists(addrStr) Then
            result.Add addrStr, foldersDict
        End If
    Next addr
End Sub

' =============================================================================
' Posteingang / Gesendete verarbeiten
' =============================================================================

''' Durchlaeuft einen Outlook-Ordner und exportiert E-Mails gemaess YAML-Config.
'''
''' Fuer jeden Studierenden wird der Betreff und Textkoerper jeder E-Mail nach
''' den Ordner-Keywords durchsucht.  Der erste Treffer bestimmt den Zielordner.
''' Pro Absender/Empfaenger wird nur die neueste Mail in Outlook behalten.
'''
''' Args:
'''     folder:       Der zu durchsuchende Outlook-Ordner.
'''     studentMap:   Dictionary email_lower -> StudentEntry-Array.
'''     subFolder:    Unterordner-Name, der an den konfigurierten Pfad angehaengt wird.
'''     isSent:       True = Empfaengeradresse pruefen, False = Absender.
'''     savedCount:   Zaehler exportierter Mails (wird hochgezaehlt).
'''     deletedCount: Zaehler geloeschter Mails (wird hochgezaehlt).
Private Sub ProcessFolder(ByVal folder As Outlook.MAPIFolder, _
                          ByVal studentMap As Object, _
                          ByVal subFolder As String, _
                          ByVal isSent As Boolean, _
                          ByRef savedCount As Long, _
                          ByRef deletedCount As Long)

    Dim senderMails As Object
    Set senderMails = CreateObject("Scripting.Dictionary")
    senderMails.CompareMode = 1

    Dim items      As Outlook.items
    Dim item       As Object
    Dim matchEmail As String

    Set items = folder.items

    Dim i As Long
    For i = 1 To items.Count
        Set item = items(i)

        If item.Class = olMail Then
            If isSent Then
                matchEmail = GetFirstRecipientAddress(item)
            Else
                matchEmail = LCase(GetSenderEmailAddress(item))
            End If

            If studentMap.Exists(matchEmail) Then
                If Not senderMails.Exists(matchEmail) Then
                    senderMails.Add matchEmail, New Collection
                End If
                senderMails(matchEmail).Add item
            End If
        End If
    Next i

    Dim key As Variant
    For Each key In senderMails.Keys
        Dim mailCollection As Collection
        Set mailCollection = senderMails(key)

        ' foldersDict direkt aus studentMap holen (keyword_lower -> folder_path)
        Dim foldersDict As Object
        Set foldersDict = studentMap(key)

        ' Neueste Mail ermitteln
        Dim newestMail  As Outlook.mailItem
        Dim currentMail As Outlook.mailItem
        Set newestMail = mailCollection(1)

        Dim j As Long
        For j = 2 To mailCollection.Count
            Set currentMail = mailCollection(j)
            If currentMail.ReceivedTime > newestMail.ReceivedTime Then
                Set newestMail = currentMail
            End If
        Next j

        ' Alle Mails exportieren
        For j = 1 To mailCollection.Count
            Set currentMail = mailCollection(j)

            ' Zielordner per Keyword-Suche bestimmen
            Dim targetFolder As String
            targetFolder = FindFolderByKeyword(currentMail, foldersDict)

            If Len(targetFolder) = 0 Then
                ' Kein Keyword-Treffer -> erstes verfuegbares Verzeichnis nutzen
                Dim firstKey As Variant
                firstKey = foldersDict.Keys
                If UBound(firstKey) >= 0 Then
                    targetFolder = foldersDict(firstKey(0))
                End If
            End If

            If Len(targetFolder) = 0 Then
                MsgBox "Kein Zielordner fuer Mail von " & key & " gefunden." & vbCrLf & _
                       "Betreff: " & currentMail.Subject, vbExclamation, "EmailSorter"
                GoTo NextMail
            End If

            Dim fullTargetPath As String
            fullTargetPath = targetFolder & "\" & subFolder

            If Not EnsureDirectory(fullTargetPath) Then
                MsgBox "Ordner konnte nicht erstellt werden:" & vbCrLf & fullTargetPath, _
                       vbExclamation, "EmailSorter"
                GoTo NextMail
            End If

            Dim filePath As String
            filePath = BuildMsgFilePath(fullTargetPath, currentMail)

            If SaveMailToFile(currentMail, fullTargetPath, filePath) Then
                savedCount = savedCount + 1
                If currentMail.EntryID <> newestMail.EntryID Then
                    currentMail.Delete
                    deletedCount = deletedCount + 1
                End If
            Else
                MsgBox "Export fehlgeschlagen!" & vbCrLf & _
                       "Betreff: " & currentMail.Subject & vbCrLf & _
                       "Zielpfad: " & filePath, vbExclamation, "EmailSorter"
            End If

NextMail:
        Next j
    Next key

    Set senderMails = Nothing
End Sub

''' Sucht im Betreff und Textkoerper einer Mail nach bekannten Ordner-Keywords
''' und gibt den zugehoerigen Ordnerpfad zurueck.
'''
''' Das foldersDict bildet keyword_lower -> folder_path ab; alle Keywords aus
''' der keys-Liste jedes Ordner-Eintrags sind einzelne Eintraege im Dict.
''' Es wird case-insensitiv gesucht; der erste Treffer gewinnt.
'''
''' Args:
'''     mail:        Das zu pruefende MailItem.
'''     foldersDict: Dictionary keyword_lower -> folder_path.
'''
''' Returns:
'''     Den Ordnerpfad des ersten Keyword-Treffers, oder leerer String.
Private Function FindFolderByKeyword(ByVal mail As Outlook.mailItem, _
                                     ByVal foldersDict As Object) As String
    Dim searchText As String
    searchText = LCase(mail.Subject & " " & mail.Body)

    Dim kw As Variant
    For Each kw In foldersDict.Keys
        If InStr(searchText, CStr(kw)) > 0 Then
            FindFolderByKeyword = foldersDict(kw)
            Exit Function
        End If
    Next kw

    FindFolderByKeyword = ""
End Function

' =============================================================================
' Hilfsfunktionen
' (unveraendert gegenueber der Originalversion, soweit nicht anders vermerkt)
' =============================================================================

''' Baut den vollstaendigen Dateipfad fuer eine .msg-Datei zusammen.
'''
''' Der Dateiname setzt sich aus Empfangsdatum/-zeit und dem Betreff zusammen.
''' Ungueltige Zeichen fuer Dateinamen werden entfernt.
'''
''' Args:
'''     folderPath: Zielordner auf dem Dateisystem.
'''     mail:       Das zu speichernde MailItem.
'''
''' Returns:
'''     Vollstaendiger Dateipfad als String.
Private Function BuildMsgFilePath(ByVal folderPath As String, _
                                  ByVal mail As Outlook.mailItem) As String
    Dim datePart    As String
    Dim subjectPart As String
    Dim fileName    As String

    datePart = Format(mail.ReceivedTime, "YYYYMMDD_HHMMSS")
    subjectPart = SanitizeFileName(mail.Subject)

    If Len(subjectPart) > 80 Then subjectPart = Left(subjectPart, 80)

    fileName = datePart & " - " & subjectPart & ".msg"

    Do While Right(folderPath, 1) = "\"
        folderPath = Left(folderPath, Len(folderPath) - 1)
    Loop

    BuildMsgFilePath = folderPath & "\" & fileName
End Function

''' Entfernt Zeichen, die in Windows-Dateinamen nicht erlaubt sind.
'''
''' Args:
'''     name: Der zu bereinigende String.
'''
''' Returns:
'''     Bereinigter String ohne die Zeichen \ / : * ? " < > |
Private Function SanitizeFileName(ByVal name As String) As String
    Dim invalidChars As String
    Dim result       As String
    Dim i            As Long

    invalidChars = "\/:*?""<>|"
    result = name

    For i = 1 To Len(invalidChars)
        result = Join(Split(result, Mid(invalidChars, i, 1)), "_")
    Next i

    result = Trim(result)
    Do While Right(result, 1) = "."
        result = Left(result, Len(result) - 1)
    Loop

    If Len(result) = 0 Then result = "kein_Betreff"

    SanitizeFileName = result
End Function

''' Erstellt einen Ordner auf dem Dateisystem, einschliesslich aller Elternordner.
'''
''' Args:
'''     path: Vollstaendiger Pfad des zu erstellenden Ordners.
'''
''' Returns:
'''     True wenn der Ordner existiert oder erfolgreich erstellt wurde.
Private Function EnsureDirectory(ByVal path As String) As Boolean
    Do While Right(path, 1) = "\"
        path = Left(path, Len(path) - 1)
    Loop

    Dim fso As Object
    Set fso = CreateObject("Scripting.FileSystemObject")

    If fso.FolderExists(path) Then
        EnsureDirectory = True
        Exit Function
    End If

    Dim parentPath As String
    parentPath = fso.GetParentFolderName(path)

    If Len(parentPath) = 0 Or parentPath = path Then
        EnsureDirectory = False
        Exit Function
    End If

    If Not EnsureDirectory(parentPath) Then
        EnsureDirectory = False
        Exit Function
    End If

    On Error GoTo DirError
    fso.CreateFolder path
    EnsureDirectory = True
    Exit Function

DirError:
    EnsureDirectory = False
End Function

''' Gibt die tatsaechliche SMTP-Adresse eines Absenders zurueck.
'''
''' Args:
'''     mail: Das MailItem.
'''
''' Returns:
'''     SMTP-Adresse (Lowercase).
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

''' Gibt die SMTP-Adresse des ersten Empfaengers einer gesendeten Mail zurueck.
'''
''' Args:
'''     mail: Das MailItem.
'''
''' Returns:
'''     SMTP-Adresse des ersten Empfaengers (Lowercase).
Private Function GetFirstRecipientAddress(ByVal mail As Outlook.mailItem) As String
    On Error GoTo RecipError

    If mail.Recipients.Count = 0 Then
        GetFirstRecipientAddress = ""
        Exit Function
    End If

    Dim recip     As Outlook.Recipient
    Dim addrEntry As Outlook.AddressEntry
    Set recip = mail.Recipients(1)
    Set addrEntry = recip.AddressEntry

    If Not addrEntry Is Nothing Then
        If addrEntry.AddressEntryUserType = olExchangeUserAddressEntry Or _
           addrEntry.AddressEntryUserType = olExchangeRemoteUserAddressEntry Then
            Dim exchUser As Outlook.ExchangeUser
            Set exchUser = addrEntry.GetExchangeUser()
            If Not exchUser Is Nothing Then
                GetFirstRecipientAddress = LCase(exchUser.PrimarySmtpAddress)
                Exit Function
            End If
        End If
    End If

RecipError:
    GetFirstRecipientAddress = LCase(recip.Address)
End Function

''' Speichert eine Mail als .msg-Datei auf dem Dateisystem.
'''
''' Args:
'''     mail:       Das zu exportierende MailItem.
'''     folderPath: Zielordner-Pfad.
'''     filePath:   Vollstaendiger Zieldateipfad.
'''
''' Returns:
'''     True wenn erfolgreich gespeichert (oder Datei bereits vorhanden).
Private Function SaveMailToFile(ByVal mail As Outlook.mailItem, _
                                ByVal folderPath As String, _
                                ByRef filePath As String) As Boolean
    Dim fso         As Object
    Dim folder      As Object
    Dim countBefore As Long
    Dim countAfter  As Long

    Set fso = CreateObject("Scripting.FileSystemObject")

    On Error GoTo SaveError

    If fso.FileExists(filePath) Then
        SaveMailToFile = True
        Exit Function
    End If

    Set folder = fso.GetFolder(folderPath)
    countBefore = folder.Files.Count

    mail.SaveAs filePath, olMSG

    countAfter = folder.Files.Count
    SaveMailToFile = (countAfter > countBefore)
    Exit Function

SaveError:
    SaveMailToFile = False
End Function

''' Prueft ob eine Datei vorhanden ist.
'''
''' Args:
'''     path: Vollstaendiger Dateipfad.
'''
''' Returns:
'''     True wenn die Datei existiert.
Private Function FileExists(ByVal path As String) As Boolean
    FileExists = (Len(Dir(path)) > 0)
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
