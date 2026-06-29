' =============================================================================
' ArchiveOldStudentMails.bas
' Outlook 2019 VBA-Makro (stabilisierte Version)
'
' Funktionsweise:
'   1. Durchlaeuft Posteingang und Gesendete Elemente.
'   2. Sucht nach Mails von/an Studierende mit @smail.th-koeln.de oder
'      @smail.fh-koeln.de, die aelter als ARCHIVE_AGE_YEARS Jahre sind.
'   3. Exportiert diese Mails als .msg-Datei in:
'        ARCHIVE_ROOT\<email-adresse>\Inbox\     (Posteingang)
'        ARCHIVE_ROOT\<email-adresse>\SentItems\ (Gesendete)
'   4. Verschiebt exportierte Mails in den Papierkorb.
'   5. Zeigt am Ende eine Zusammenfassung an.
'
' Wichtige Stabilitaetsverbesserungen:
'   - Rueckwaertsiteration
'   - Regelmaessige DoEvents + Sleep
'   - COM-Objekte werden sauber freigegeben
'   - MailItems werden explizit gecastet
'   - Keine direkte Delete-Operation mehr
' =============================================================================

Option Explicit

#If VBA7 Then
    Private Declare PtrSafe Sub Sleep Lib "kernel32" (ByVal dwMilliseconds As LongPtr)
#Else
    Private Declare Sub Sleep Lib "kernel32" (ByVal dwMilliseconds As Long)
#End If

' Wurzelordner fuer das Archiv
Private Const ARCHIVE_ROOT As String = "D:\TH_Koeln\StudentMails"

' Mails aelter als diese Anzahl Jahre werden archiviert
Private Const ARCHIVE_AGE_YEARS As Integer = 1

' Name der Datei mit studentischen Domains
Private Const DOMAINS_FILE_NAME As String = "student_domains.md"

' Modul-Variable fuer geladene Domains
Private m_StudentDomains As String

' Zusaetzliche einzelne E-Mail-Adressen
Private Const ADDITIONAL_ADDRESSES As String = "noreply@th-koeln.de"


' =============================================================================
' Hauptprozedur
' =============================================================================

''' Archiviert alte Studierenden-Mails aus Posteingang und Gesendeten Elementen.
'''
''' Mails aelter als ARCHIVE_AGE_YEARS Jahre von/an Adressen mit einer der
''' in STUDENT_DOMAINS konfigurierten Endungen werden als .msg exportiert und
''' anschliessend aus Outlook geloescht.
Public Sub ArchiveOldStudentMails()

    On Error GoTo MainError

    ' Domains aus Datei laden
    m_StudentDomains = LoadStudentDomains()

    Dim inbox As Outlook.MAPIFolder
    Dim sentItems As Outlook.MAPIFolder

    Set inbox = Application.Session.GetDefaultFolder(olFolderInbox)
    Set sentItems = Application.Session.GetDefaultFolder(olFolderSentMail)

    If inbox Is Nothing Or sentItems Is Nothing Then
        MsgBox "Posteingang oder Gesendete Elemente konnten nicht geoeffnet werden.", _
               vbCritical, "ArchiveOldStudentMails"
        Exit Sub
    End If

    If Not EnsureDirectory(ARCHIVE_ROOT) Then
        MsgBox "Archivordner konnte nicht erstellt werden:" & vbCrLf & ARCHIVE_ROOT, _
               vbCritical, "ArchiveOldStudentMails"
        Exit Sub
    End If

    Dim cutoffDate As Date
    cutoffDate = DateAdd("yyyy", -ARCHIVE_AGE_YEARS, Now())

    Dim exportedCount As Long
    exportedCount = 0

    ProcessArchiveFolder inbox, cutoffDate, "Inbox", False, exportedCount

    DoEvents
    Sleep 1000

    ProcessArchiveFolder sentItems, cutoffDate, "SentItems", True, exportedCount

    MsgBox "Fertig!" & vbCrLf & _
           "Archiviert: " & exportedCount & " Mail(s)" & vbCrLf & _
           "Archivpfad: " & ARCHIVE_ROOT, _
           vbInformation, "ArchiveOldStudentMails"

Cleanup:
    Set inbox = Nothing
    Set sentItems = Nothing
    Exit Sub

MainError:
    MsgBox "Fehler: " & Err.Description, vbCritical, "ArchiveOldStudentMails"
    Resume Cleanup

End Sub


' =============================================================================
' Ordner verarbeiten
' =============================================================================

''' Durchlaeuft einen Outlook-Ordner und archiviert passende alte Mails.
'''
''' Args:
'''     folder:        Der zu durchsuchende Outlook-Ordner.
'''     cutoffDate:    Mails aelter als dieses Datum werden archiviert.
'''     subFolder:     Unterordner-Name im Studierenden-Archivordner ("Inbox"
'''                    oder "SentItems").
'''     isSent:        True = Empfaengeradresse pruefen, False = Absender.
'''     exportedCount: Zaehler exportierter Mails (wird hochgezaehlt).
Private Sub ProcessArchiveFolder(ByVal folder As Outlook.MAPIFolder, _
                                 ByVal cutoffDate As Date, _
                                 ByVal subFolder As String, _
                                 ByVal isSent As Boolean, _
                                 ByRef exportedCount As Long)

    On Error GoTo FolderError

    Dim items As Outlook.items
    Set items = folder.items

    ' Zu archivierende Mails zuerst in eine separate Liste sammeln,
    ' um Probleme beim Loeschen waehrend der Iteration zu vermeiden.
    Dim toArchive As Collection
    Set toArchive = New Collection

    Dim itemCount As Long
    itemCount = items.count

    Dim i As Long

    ' Rueckwaerts iterieren -> stabiler
    For i = itemCount To 1 Step -1

        If i Mod 50 = 0 Then
            DoEvents
            Sleep 200
        End If

        Dim obj As Object
        Set obj = items(i)

        If TypeOf obj Is Outlook.mailItem Then

            Dim mail As Outlook.mailItem
            Set mail = obj

            On Error Resume Next

            If mail.ReceivedTime < cutoffDate Then

                Dim studentAddr As String

                If isSent Then
                    studentAddr = GetFirstRecipientAddress(mail)
                Else
                    studentAddr = LCase(GetSenderEmailAddress(mail))
                End If

                If ShouldArchiveAddress(studentAddr) Then
                    toArchive.Add mail
                End If

            End If

            On Error GoTo FolderError

            Set mail = Nothing

        End If

        Set obj = Nothing

    Next i


    ' =====================================================================
    ' Exportieren
    ' =====================================================================

    Dim deletedFolder As Outlook.MAPIFolder
    Set deletedFolder = Application.Session.GetDefaultFolder(olFolderDeletedItems)

    Dim processed As Long
    processed = 0

    Dim mailItem As Outlook.mailItem

    For Each mailItem In toArchive

        processed = processed + 1

        If processed Mod 10 = 0 Then
            DoEvents
            Sleep 500
        End If

        Dim studentAddr2 As String

        If isSent Then
            studentAddr2 = GetFirstRecipientAddress(mailItem)
        Else
            studentAddr2 = LCase(GetSenderEmailAddress(mailItem))
        End If

        ' Zielordner: ARCHIVE_ROOT\<email>\<subFolder>
        Dim targetPath As String
        targetPath = ARCHIVE_ROOT & "\" & _
                     SanitizeFolderName(studentAddr2) & "\" & subFolder

        If EnsureDirectory(targetPath) Then

            Dim filePath As String
            filePath = BuildMsgFilePath(targetPath, mailItem)

            If ExportAndMove(mailItem, deletedFolder, targetPath, filePath) Then
                exportedCount = exportedCount + 1
            End If

        End If

        Set mailItem = Nothing

    Next mailItem

Cleanup:
    Set deletedFolder = Nothing
    Set items = Nothing
    Set toArchive = Nothing
    Exit Sub

FolderError:
    MsgBox "Fehler in Ordnerverarbeitung: " & Err.Description, _
           vbExclamation, "ArchiveOldStudentMails"
    Resume Cleanup

End Sub


' =============================================================================
' Exportieren + verschieben
' =============================================================================

Private Function ExportAndMove(ByVal mail As Outlook.mailItem, _
                               ByVal deletedFolder As Outlook.MAPIFolder, _
                               ByVal folderPath As String, _
                               ByVal filePath As String) As Boolean

    On Error GoTo ExportError

    Dim fso As Object
    Set fso = CreateObject("Scripting.FileSystemObject")

    If fso.FileExists(filePath) Then

        DoEvents
        Sleep 150

        mail.Move deletedFolder

        ExportAndMove = True
        GoTo Cleanup

    End If

    Dim folderObj As Object
    Set folderObj = fso.GetFolder(folderPath)

    Dim countBefore As Long
    countBefore = folderObj.Files.count


    ' =====================================================================
    ' SAVE AS
    ' =====================================================================

    mail.SaveAs filePath, olMSG

    ' Outlook/MAPI entlasten
    DoEvents
    Sleep 300


    ' =====================================================================
    ' Erfolg pruefen
    ' =====================================================================

    If folderObj.Files.count > countBefore Then

        DoEvents
        Sleep 150

        ' NICHT direkt loeschen -> stabiler
        mail.Move deletedFolder

        DoEvents

        ExportAndMove = True

    Else

        ExportAndMove = False

    End If

Cleanup:
    Set folderObj = Nothing
    Set fso = Nothing
    Exit Function

ExportError:

    ExportAndMove = False

    Set folderObj = Nothing
    Set fso = Nothing

End Function


' =============================================================================
' Adresspruefung
' =============================================================================

''' Prueft ob eine E-Mail-Adresse archiviert werden soll.
'''
''' Es wird geprueft ob die Adresse:
'''   (a) eine der konfigurierten Studierenden-Domains enthaelt, oder
'''   (b) exakt einer der konfigurierten Zusatz-Adressen entspricht.
'''
''' Args:
'''     addr: Die zu pruefende E-Mail-Adresse (Lowercase).
'''
''' Returns:
'''     True wenn die Adresse archiviert werden soll.
Private Function ShouldArchiveAddress(ByVal addr As String) As Boolean

    If Len(addr) = 0 Then
        ShouldArchiveAddress = False
        Exit Function
    End If

    Dim domains() As String
    domains = Split(m_StudentDomains, "|")

    Dim d As Variant

    For Each d In domains

        If InStr(addr, CStr(d)) > 0 Then
            ShouldArchiveAddress = True
            Exit Function
        End If

    Next d


    If Len(Trim(ADDITIONAL_ADDRESSES)) > 0 Then

        Dim addrs() As String
        addrs = Split(ADDITIONAL_ADDRESSES, "|")

        Dim a As Variant

        For Each a In addrs

            If LCase(Trim(CStr(a))) = addr Then
                ShouldArchiveAddress = True
                Exit Function
            End If

        Next a

    End If

    ShouldArchiveAddress = False

End Function


' =============================================================================
' Dateiname erzeugen
' =============================================================================

''' Baut den vollstaendigen Dateipfad fuer eine .msg-Datei zusammen.
'''
''' Dateiname: YYYYMMDD_HHMMSS - Betreff.msg
''' Ungueltige Dateinamen-Zeichen werden entfernt, Betreff auf 80 Zeichen gekuerzt.
'''
''' Args:
'''     folderPath: Zielordner auf dem Dateisystem.
'''     mail:       Das zu speichernde MailItem.
'''
''' Returns:
'''     Vollstaendiger Dateipfad als String.
Private Function BuildMsgFilePath(ByVal folderPath As String, _
                                  ByVal mail As Outlook.mailItem) As String

    Dim datePart As String
    Dim subjectPart As String

    datePart = Format(mail.ReceivedTime, "YYYYMMDD_HHMMSS")

    subjectPart = SanitizeFileName(mail.Subject)

    If Len(subjectPart) > 80 Then
        subjectPart = Left(subjectPart, 80)
    End If

    Do While Right(folderPath, 1) = "\"
        folderPath = Left(folderPath, Len(folderPath) - 1)
    Loop

    BuildMsgFilePath = folderPath & "\" & _
                       datePart & " - " & subjectPart & ".msg"

End Function


' =============================================================================
' Dateiname bereinigen
' =============================================================================

''' Entfernt Zeichen, die in Windows-Dateinamen nicht erlaubt sind.
'''
''' Args:
'''     name: Der zu bereinigende String.
'''
''' Returns:
'''     Bereinigter String ohne \ / : * ? " < > |
Private Function SanitizeFileName(ByVal name As String) As String

    Dim invalidChars As String
    invalidChars = "\/:*?""<>|"

    Dim result As String
    result = name

    Dim i As Long

    For i = 1 To Len(invalidChars)
        result = Join(Split(result, Mid(invalidChars, i, 1)), "_")
    Next i

    result = Trim(result)

    Do While Len(result) > 0 And Right(result, 1) = "."
        result = Left(result, Len(result) - 1)
    Loop

    If Len(result) = 0 Then
        result = "kein_Betreff"
    End If

    SanitizeFileName = result

End Function


' =============================================================================
' Ordnername bereinigen
' =============================================================================

''' Bereitet eine E-Mail-Adresse als gueltigen Ordnernamen auf.
'''
''' Ersetzt nur Zeichen, die als Windows-Ordnername nicht erlaubt sind.
''' "@" und "." bleiben erhalten, da sie Ordnernamen gut lesbar machen.
'''
''' Args:
'''     addr: Die E-Mail-Adresse.
'''
''' Returns:
'''     Bereinigter Ordnername.
Private Function SanitizeFolderName(ByVal addr As String) As String

    Dim result As String

    result = addr

    result = Replace(result, "\", "_")
    result = Replace(result, "/", "_")
    result = Replace(result, ":", "_")
    result = Replace(result, "*", "_")
    result = Replace(result, "?", "_")
    result = Replace(result, """", "_")
    result = Replace(result, "<", "_")
    result = Replace(result, ">", "_")
    result = Replace(result, "|", "_")

    result = Trim(result)

    If Len(result) = 0 Then
        result = "unbekannt"
    End If

    SanitizeFolderName = result

End Function


' =============================================================================
' Ordner sicherstellen
' =============================================================================

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
        Set fso = Nothing
        Exit Function
    End If

    Dim parentPath As String
    parentPath = fso.GetParentFolderName(path)

    If Len(parentPath) = 0 Or parentPath = path Then
        EnsureDirectory = False
        Set fso = Nothing
        Exit Function
    End If

    If Not EnsureDirectory(parentPath) Then
        EnsureDirectory = False
        Set fso = Nothing
        Exit Function
    End If

    On Error GoTo DirError

    fso.CreateFolder path

    EnsureDirectory = True

    Set fso = Nothing

    Exit Function

DirError:

    EnsureDirectory = False

    Set fso = Nothing

End Function


' =============================================================================
' SMTP-Absenderadresse
' =============================================================================

''' Gibt die tatsaechliche SMTP-Adresse eines Absenders zurueck.
'''
''' Args:
'''     mail: Das MailItem.
'''
''' Returns:
'''     SMTP-Adresse (Lowercase).
Private Function GetSenderEmailAddress(ByVal mail As Outlook.mailItem) As String

    On Error GoTo Fallback

    Dim addrEntry As Outlook.AddressEntry
    Set addrEntry = mail.sender

    If Not addrEntry Is Nothing Then

        If addrEntry.AddressEntryUserType = olExchangeUserAddressEntry Or _
           addrEntry.AddressEntryUserType = olExchangeRemoteUserAddressEntry Then

            Dim exchUser As Outlook.ExchangeUser
            Set exchUser = addrEntry.GetExchangeUser()

            If Not exchUser Is Nothing Then

                GetSenderEmailAddress = LCase(exchUser.PrimarySmtpAddress)

                Set exchUser = Nothing
                Set addrEntry = Nothing

                Exit Function

            End If

            Set exchUser = Nothing

        End If

    End If

Fallback:

    GetSenderEmailAddress = LCase(mail.SenderEmailAddress)

    Set addrEntry = Nothing

End Function


' =============================================================================
' SMTP-Adresse erster Empfaenger
' =============================================================================

''' Gibt die SMTP-Adresse des ersten Empfaengers zurueck.
'''
''' Args:
'''     mail: Das MailItem.
'''
''' Returns:
'''     SMTP-Adresse des ersten Empfaengers (Lowercase).
Private Function GetFirstRecipientAddress(ByVal mail As Outlook.mailItem) As String

    On Error GoTo RecipError

    If mail.Recipients.count = 0 Then
        GetFirstRecipientAddress = ""
        Exit Function
    End If

    Dim recip As Outlook.Recipient
    Set recip = mail.Recipients(1)

    Dim addrEntry As Outlook.AddressEntry
    Set addrEntry = recip.AddressEntry

    If Not addrEntry Is Nothing Then

        If addrEntry.AddressEntryUserType = olExchangeUserAddressEntry Or _
           addrEntry.AddressEntryUserType = olExchangeRemoteUserAddressEntry Then

            Dim exchUser As Outlook.ExchangeUser
            Set exchUser = addrEntry.GetExchangeUser()

            If Not exchUser Is Nothing Then

                GetFirstRecipientAddress = LCase(exchUser.PrimarySmtpAddress)

                Set exchUser = Nothing
                Set addrEntry = Nothing
                Set recip = Nothing

                Exit Function

            End If

            Set exchUser = Nothing

        End If

    End If

RecipError:

    GetFirstRecipientAddress = LCase(recip.Address)

    Set addrEntry = Nothing
    Set recip = Nothing

End Function


' =============================================================================
' Hilfsfunktionen
' =============================================================================

''' Lädt studentische Domains aus einer externen Datei (analog zu ExportStudentMails.bas).
'''
''' Returns:
'''     Eine durch "|" getrennte Liste von Domains.
Private Function LoadStudentDomains() As String
    Dim fso As Object
    Dim ts As Object
    Dim filePath As String
    Dim line As String
    Dim result As String
    Dim defaultDomains As String

    defaultDomains = "@smail.th-koeln.de|@smail.fh-koeln.de"
    ' Nutzt ARCHIVE_ROOT als Basispfad für die Konfigurationsdatei
    filePath = ARCHIVE_ROOT & "\" & DOMAINS_FILE_NAME
    result = ""

    Set fso = CreateObject("Scripting.FileSystemObject")

    If Not fso.FileExists(filePath) Then
        LoadStudentDomains = defaultDomains
        Exit Function
    End If

    On Error GoTo ReadError
    Set ts = fso.OpenTextFile(filePath, 1) ' 1 = ForReading

    Do Until ts.AtEndOfStream
        line = Trim(ts.ReadLine)
        ' Überschriften und Kommentare ignorieren
        If Len(line) > 0 And Left(line, 1) <> "#" Then
            If Len(result) > 0 Then
                result = result & "|" & line
            Else
                result = line
            End If
        End If
    Loop

    ts.Close

    If Len(result) = 0 Then
        LoadStudentDomains = defaultDomains
    Else
        LoadStudentDomains = result
    End If
    Exit Function

ReadError:
    If Not ts Is Nothing Then ts.Close
    Debug.Print "Fehler beim Lesen der Domains-Datei: " & Err.Description
    LoadStudentDomains = defaultDomains
End Function
