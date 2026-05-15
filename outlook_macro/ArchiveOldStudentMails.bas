' =============================================================================
' ArchiveOldStudentMails.bas
' Outlook 2019 VBA-Makro
'
' Funktionsweise:
'   1. Durchlaeuft Posteingang und Gesendete Elemente.
'   2. Sucht nach Mails von/an Studierende mit @smail.th-koeln.de oder
'      @smail.fh-koeln.de, die aelter als ARCHIVE_AGE_YEARS Jahre sind.
'   3. Exportiert diese Mails als .msg-Datei in:
'        ARCHIVE_ROOT\<email-adresse>\Inbox\     (Posteingang)
'        ARCHIVE_ROOT\<email-adresse>\SentItems\ (Gesendete)
'   4. Loescht die exportierten Mails aus Outlook.
'   5. Zeigt am Ende eine Zusammenfassung an.
'
' WICHTIG: Den Pfad in ARCHIVE_ROOT ggf. anpassen.
' =============================================================================

Option Explicit

' Wurzelordner fuer das Archiv
Private Const ARCHIVE_ROOT As String = "D:\TH_Koeln\StudentMails"

' Mails aelter als diese Anzahl Jahre werden archiviert
Private Const ARCHIVE_AGE_YEARS As Integer = 3

' Zu pruefende Absender-Domains (Pipe-getrennt, Lowercase)
Private Const STUDENT_DOMAINS As String = "@smail.th-koeln.de|@smail.fh-koeln.de"

' =============================================================================
' Hauptprozedur
' =============================================================================

''' Archiviert alte Studierenden-Mails aus Posteingang und Gesendeten Elementen.
'''
''' Mails aelter als ARCHIVE_AGE_YEARS Jahre von/an Adressen mit einer der
''' in STUDENT_DOMAINS konfigurierten Endungen werden als .msg exportiert und
''' anschliessend aus Outlook geloescht.
Public Sub ArchiveOldStudentMails()
    Dim inbox     As Outlook.MAPIFolder
    Dim sentItems As Outlook.MAPIFolder

    Set inbox = Application.Session.GetDefaultFolder(olFolderInbox)
    Set sentItems = Application.Session.GetDefaultFolder(olFolderSentMail)

    If inbox Is Nothing Or sentItems Is Nothing Then
        MsgBox "Posteingang oder Gesendete Elemente konnten nicht geoeffnet werden.", _
               vbCritical, "ArchiveOldStudentMails"
        Exit Sub
    End If

    ' Archiv-Wurzelordner sicherstellen
    If Not EnsureDirectory(ARCHIVE_ROOT) Then
        MsgBox "Archivordner konnte nicht erstellt werden:" & vbCrLf & ARCHIVE_ROOT, _
               vbCritical, "ArchiveOldStudentMails"
        Exit Sub
    End If

    Dim cutoffDate  As Date
    cutoffDate = DateAdd("yyyy", -ARCHIVE_AGE_YEARS, Now())

    Dim exportedCount As Long
    exportedCount = 0

    ProcessArchiveFolder inbox, cutoffDate, "Inbox", False, exportedCount
    ProcessArchiveFolder sentItems, cutoffDate, "SentItems", True, exportedCount

    MsgBox "Fertig!" & vbCrLf & _
           "Archiviert und geloescht: " & exportedCount & " Mail(s)" & vbCrLf & _
           "Archivpfad: " & ARCHIVE_ROOT, _
           vbInformation, "ArchiveOldStudentMails"
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
    ' Mails rueckwaerts iterieren, da beim Loeschen der Index verschoben wird
    Dim items As Outlook.items
    Set items = folder.items

    ' Zu archivierende Mails zuerst in eine separate Liste sammeln,
    ' um Probleme beim Loeschen waehrend der Iteration zu vermeiden.
    Dim toArchive As Collection
    Set toArchive = New Collection

    Dim i As Long
    For i = 1 To items.Count
        Dim item As Object
        Set item = items(i)

        If item.Class = olMail Then
            ' Datumscheck
            If item.ReceivedTime < cutoffDate Then
                ' Studierenden-Adresse ermitteln
                Dim studentAddr As String
                If isSent Then
                    studentAddr = GetFirstRecipientAddress(item)
                Else
                    studentAddr = LCase(GetSenderEmailAddress(item))
                End If

                If IsStudentAddress(studentAddr) Then
                    toArchive.Add item
                End If
            End If
        End If
    Next i

    ' Gesammelte Mails exportieren und loeschen
    Dim mailItem As Object
    For Each mailItem In toArchive
        Dim studentAddr2 As String
        If isSent Then
            studentAddr2 = GetFirstRecipientAddress(mailItem)
        Else
            studentAddr2 = LCase(GetSenderEmailAddress(mailItem))
        End If

        ' Zielordner: ARCHIVE_ROOT\<email>\<subFolder>
        Dim targetPath As String
        targetPath = ARCHIVE_ROOT & "\" & SanitizeFolderName(studentAddr2) & "\" & subFolder

        If Not EnsureDirectory(targetPath) Then
            MsgBox "Ordner konnte nicht erstellt werden:" & vbCrLf & targetPath, _
                   vbExclamation, "ArchiveOldStudentMails"
        Else
            Dim filePath As String
            filePath = BuildMsgFilePath(targetPath, mailItem)

            If ExportAndDelete(mailItem, targetPath, filePath) Then
                exportedCount = exportedCount + 1
            Else
                MsgBox "Export fehlgeschlagen!" & vbCrLf & _
                       "Betreff: " & mailItem.Subject & vbCrLf & _
                       "Zielpfad: " & filePath, vbExclamation, "ArchiveOldStudentMails"
            End If
        End If
    Next mailItem

    Set toArchive = Nothing
End Sub

' =============================================================================
' Hilfsfunktionen
' =============================================================================

''' Prueft ob eine E-Mail-Adresse zu einer der konfigurierten Studierenden-Domains
''' gehoert.
'''
''' Args:
'''     addr: Die zu pruefende E-Mail-Adresse (Lowercase).
'''
''' Returns:
'''     True wenn die Adresse eine der Studierenden-Domains enthaelt.
Private Function IsStudentAddress(ByVal addr As String) As Boolean
    If Len(addr) = 0 Then
        IsStudentAddress = False
        Exit Function
    End If

    Dim domains() As String
    domains = Split(STUDENT_DOMAINS, "|")
    Dim d As Variant
    For Each d In domains
        If InStr(addr, CStr(d)) > 0 Then
            IsStudentAddress = True
            Exit Function
        End If
    Next d

    IsStudentAddress = False
End Function

''' Exportiert eine Mail als .msg-Datei und loescht sie danach aus Outlook.
'''
''' Args:
'''     mail:       Das zu exportierende MailItem.
'''     folderPath: Zielordner-Pfad.
'''     filePath:   Vollstaendiger Zieldateipfad.
'''
''' Returns:
'''     True wenn Export und Loeschung erfolgreich waren.
Private Function ExportAndDelete(ByVal mail As Outlook.mailItem, _
                                 ByVal folderPath As String, _
                                 ByVal filePath As String) As Boolean
    On Error GoTo ExportError

    Dim fso As Object
    Set fso = CreateObject("Scripting.FileSystemObject")

    ' Datei existiert bereits -> als Erfolg werten, Mail trotzdem loeschen
    If fso.FileExists(filePath) Then
        mail.Delete
        ExportAndDelete = True
        Exit Function
    End If

    Dim folder As Object
    Set folder = fso.GetFolder(folderPath)
    Dim countBefore As Long
    countBefore = folder.Files.Count

    mail.SaveAs filePath, olMSG

    ' Nur loeschen wenn Export nachweislich erfolgreich war
    If folder.Files.Count > countBefore Then
        mail.Delete
        ExportAndDelete = True
    Else
        ExportAndDelete = False
    End If
    Exit Function

ExportError:
    ExportAndDelete = False
End Function

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
    Dim datePart    As String
    Dim subjectPart As String

    datePart = Format(mail.ReceivedTime, "YYYYMMDD_HHMMSS")
    subjectPart = SanitizeFileName(mail.Subject)
    If Len(subjectPart) > 80 Then subjectPart = Left(subjectPart, 80)

    Do While Right(folderPath, 1) = "\"
        folderPath = Left(folderPath, Len(folderPath) - 1)
    Loop

    BuildMsgFilePath = folderPath & "\" & datePart & " - " & subjectPart & ".msg"
End Function

''' Entfernt Zeichen, die in Windows-Dateinamen nicht erlaubt sind.
'''
''' Args:
'''     name: Der zu bereinigende String.
'''
''' Returns:
'''     Bereinigter String ohne \ / : * ? " < > |
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
    Do While Len(result) > 0 And Right(result, 1) = "."
        result = Left(result, Len(result) - 1)
    Loop

    If Len(result) = 0 Then result = "kein_Betreff"
    SanitizeFileName = result
End Function

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
    If Len(result) = 0 Then result = "unbekannt"
    SanitizeFolderName = result
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
    On Error GoTo Fallback
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
Fallback:
    GetSenderEmailAddress = LCase(mail.SenderEmailAddress)
End Function

''' Gibt die SMTP-Adresse des ersten Empfaengers zurueck.
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
