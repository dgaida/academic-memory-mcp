' =============================================================================
' ArchiveOldStudentMails_Outlook2007.bas
' Outlook VBA-Makro (Outlook 2007 Version)
'
' Funktionsweise:
'   1. Greift auf das Postfach "Persönliche Ordner" zu.
'   2. Durchlaeuft "Posteingang" und "Gesendete Objekte".
'   3. Sucht nach Mails von/an Studierende mit @smail.th-koeln.de oder
'      @smail.fh-koeln.de, die aelter als ARCHIVE_AGE_YEARS Jahre sind.
'   4. Exportiert diese Mails als .msg-Datei in:
'        ARCHIVE_ROOT\<email-adresse>\Inbox\     (Posteingang)
'        ARCHIVE_ROOT\<email-adresse>\SentItems\ (Gesendete)
'   5. Verschiebt exportierte Mails in den Papierkorb ("Gelöschte Objekte").
'   6. Zeigt am Ende eine Zusammenfassung an.
'
' WICHTIG: Optimiert fuer Outlook 2007 (PST-Nutzung, vereinfachte Adressaufloesung).
' =============================================================================

Option Explicit

#If VBA7 Then
    Private Declare PtrSafe Sub Sleep Lib "kernel32" (ByVal dwMilliseconds As LongPtr)
#Else
    Private Declare Sub Sleep Lib "kernel32" (ByVal dwMilliseconds As Long)
#End If

' Konfiguration
Private Const MAILBOX_NAME As String = "Persönliche Ordner"
Private Const ARCHIVE_ROOT As String = "D:\TH_Koeln\StudentMails"

' Mails aelter als diese Anzahl Jahre werden archiviert
Private Const ARCHIVE_AGE_YEARS As Integer = 1

' Zu pruefende Absender-Domains (Pipe-getrennt, Lowercase)
Private Const STUDENT_DOMAINS As String = "@smail.th-koeln.de|@smail.fh-koeln.de"

' Zusaetzliche einzelne E-Mail-Adressen
Private Const ADDITIONAL_ADDRESSES As String = "noreply@th-koeln.de"


' =============================================================================
' Hauptprozedur
' =============================================================================

''' Archiviert alte Studierenden-Mails aus Posteingang und Gesendeten Elementen.
Public Sub ArchiveOldStudentMails()

    On Error GoTo MainError

    Dim ns As Outlook.NameSpace
    Dim rootFolder As Outlook.folder
    Dim inbox As Outlook.folder
    Dim sentItems As Outlook.folder

    Set ns = Application.GetNamespace("MAPI")

    ' Postfach suchen
    On Error Resume Next
    Set rootFolder = ns.Folders(MAILBOX_NAME)
    On Error GoTo 0

    If rootFolder Is Nothing Then
        MsgBox "Postfach '" & MAILBOX_NAME & "' wurde nicht gefunden.", vbCritical, "ArchiveOldStudentMails"
        Exit Sub
    End If

    ' Standardordner abrufen
    On Error Resume Next
    Set inbox = rootFolder.Folders("Posteingang")
    Set sentItems = rootFolder.Folders("Gesendete Objekte")
    On Error GoTo 0

    If inbox Is Nothing Or sentItems Is Nothing Then
        MsgBox "Posteingang oder Gesendete Objekte konnten nicht geoeffnet werden.", _
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
    Set rootFolder = Nothing
    Exit Sub

MainError:
    MsgBox "Fehler: " & Err.Description, vbCritical, "ArchiveOldStudentMails"
    Resume Cleanup

End Sub


' =============================================================================
' Ordner verarbeiten
' =============================================================================

''' Durchlaeuft einen Outlook-Ordner und archiviert passende alte Mails.
Private Sub ProcessArchiveFolder(ByVal folder As Outlook.folder, _
                                 ByVal cutoffDate As Date, _
                                 ByVal subFolder As String, _
                                 ByVal isSent As Boolean, _
                                 ByRef exportedCount As Long)

    On Error GoTo FolderError

    Dim items As Outlook.items
    Set items = folder.items

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
                    studentAddr = GetSenderEmailAddress(mail)
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

    Dim deletedFolder As Outlook.folder
    Dim root As Outlook.folder
    Set root = folder.Parent

    On Error Resume Next
    Set deletedFolder = root.Folders("Gelöschte Objekte")
    If deletedFolder Is Nothing Then Set deletedFolder = Application.Session.GetDefaultFolder(olFolderDeletedItems)
    On Error GoTo FolderError

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
            studentAddr2 = GetSenderEmailAddress(mailItem)
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
                               ByVal deletedFolder As Outlook.folder, _
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

Private Function ShouldArchiveAddress(ByVal addr As String) As Boolean

    If Len(addr) = 0 Then
        ShouldArchiveAddress = False
        Exit Function
    End If

    Dim domains() As String
    domains = Split(STUDENT_DOMAINS, "|")

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

Private Function GetSenderEmailAddress(ByVal mail As Outlook.mailItem) As String
    GetSenderEmailAddress = LCase(mail.SenderEmailAddress)
End Function


' =============================================================================
' SMTP-Adresse erster Empfaenger
' =============================================================================

Private Function GetFirstRecipientAddress(ByVal mail As Outlook.mailItem) As String

    On Error GoTo RecipError

    If mail.Recipients.count = 0 Then
        GetFirstRecipientAddress = ""
        Exit Function
    End If

    GetFirstRecipientAddress = LCase(mail.Recipients(1).Address)
    Exit Function

RecipError:

    GetFirstRecipientAddress = ""

End Function
