' =============================================================================
' ExportStudentMails.bas
' Outlook VBA-Makro zum Exportieren studentischer E-Mails
'
' Funktionsweise:
'   1. Greift auf das Konto "daniel.gaida@th-koeln.de" zu.
'   2. Durchlaeuft den Posteingang (Inbox) und "Sent Items".
'   3. Filtert Mails von/an "@smail.th-koeln.de" oder "@smail.fh-koeln.de".
'   4. Speichert diese als .msg-Dateien unter "D:\TH_Koeln\StudentMails".
'   5. Dateiname: YYYYMMDD_HHMMSS - Betreff.msg
'   6. Loescht die E-Mail nach erfolgreichem Export oder falls bereits vorhanden.
'
' WICHTIG: Nutzt DoEvents und Sleep, um Outlook waehrend des Exports
' reaktionsfaehig zu halten.
' =============================================================================

Option Explicit

#If VBA7 Then
    Private Declare PtrSafe Sub Sleep Lib "kernel32" (ByVal dwMilliseconds As LongPtr)
#Else
    Private Declare Sub Sleep Lib "kernel32" (ByVal dwMilliseconds As Long)
#End If

' Konfiguration
Private Const ACCOUNT_NAME As String = "daniel.gaida@th-koeln.de"
Private Const ROOT_PATH As String = "D:\TH_Koeln\StudentMails"
Private Const STUDENT_DOMAINS As String = "@smail.th-koeln.de|@smail.fh-koeln.de"

' =============================================================================
' Hauptprozedur
' =============================================================================

''' Einstiegspunkt fuer das Makro. Initialisiert den Export fuer Inbox und Sent Items.
Public Sub ExportStudentEmails()
    Dim ns As Outlook.NameSpace
    Dim account As Outlook.account
    Dim store As Outlook.store
    Dim rootFolder As Outlook.folder
    Dim inbox As Outlook.folder
    Dim sentItems As Outlook.folder

    Set ns = Application.GetNamespace("MAPI")

    ' Konto suchen
    On Error Resume Next
    Set account = ns.Accounts.Item(ACCOUNT_NAME)
    On Error GoTo 0

    If account Is Nothing Then
        MsgBox "Konto '" & ACCOUNT_NAME & "' wurde nicht gefunden.", vbCritical, "ExportStudentMails"
        Exit Sub
    End If

    Set store = account.DeliveryStore
    Set rootFolder = store.GetRootFolder()

    ' Standardordner abrufen
    On Error Resume Next
    Set inbox = rootFolder.Folders("Posteingang") ' Deutsch
    If inbox Is Nothing Then Set inbox = rootFolder.Folders("Inbox")

    Set sentItems = rootFolder.Folders("Gesendete Elemente") ' Deutsch
    If sentItems Is Nothing Then Set sentItems = rootFolder.Folders("Sent Items")
    On Error GoTo 0

    If inbox Is Nothing Or sentItems Is Nothing Then
        MsgBox "Inbox oder Sent Items konnte nicht gefunden werden.", vbCritical, "ExportStudentMails"
        Exit Sub
    End If

    ' Verarbeitung starten
    ProcessFolder inbox, "Inbox"
    ProcessFolder sentItems, "SentItems"

    MsgBox "Export abgeschlossen!", vbInformation, "ExportStudentMails"
End Sub

' =============================================================================
' Verarbeitungs-Logik
' =============================================================================

''' Durchlaeuft alle Mails in einem Outlook-Ordner und speichert studentische Mails.
'''
''' Args:
'''     olFolder: Der zu durchsuchende Outlook-Ordner.
'''     subFolderName: Der Name des Unterordners im Zielpfad ("Inbox" oder "SentItems").
Private Sub ProcessFolder(ByVal olFolder As Outlook.folder, ByVal subFolderName As String)
    Dim items As Outlook.items
    Dim item As Object
    Dim mail As Outlook.mailItem
    Dim i As Long
    Dim targetPath As String
    Dim filePath As String
    Dim addr As String
    Dim savedCount As Long

    targetPath = ROOT_PATH & "\" & subFolderName
    If Not EnsureDirectory(targetPath) Then
        MsgBox "Zielverzeichnis konnte nicht erstellt werden: " & targetPath, vbCritical
        Exit Sub
    End If

    Set items = olFolder.items
    savedCount = 0

    ' Rueckwaerts durchlaufen ist bei Outlook-Kollektionen oft stabiler
    For i = items.count To 1 Step -1
        Set item = items(i)

        If TypeOf item Is mailItem Then
            Set mail = item

            ' Adresse ermitteln (je nach Ordner Absender oder Empfaenger)
            If subFolderName = "Inbox" Then
                addr = GetSenderEmailAddress(mail)
            Else
                addr = GetFirstRecipientAddress(mail)
            End If

            ' Studentische Mail?
            If IsStudentMail(addr) Then
                filePath = BuildMsgFilePath(targetPath, mail)

                ' Speichern falls nicht vorhanden
                If Len(Dir(filePath)) = 0 Then
                    On Error Resume Next
                    mail.SaveAs filePath, olMSG
                    If Err.Number = 0 Then
                        savedCount = savedCount + 1
                        mail.Delete
                    End If
                    On Error GoTo 0
                Else
                    ' Falls bereits vorhanden, auch loeschen
                    mail.Delete
                End If
            End If
        End If

        ' System entlasten
        If i Mod 10 = 0 Then
            DoEvents
            Sleep 50
        End If
    Next i

    Debug.Print "Ordner " & subFolderName & ": " & savedCount & " Mails exportiert."
End Sub

' =============================================================================
' Hilfsfunktionen
' =============================================================================

''' Prueft, ob eine E-Mail-Adresse zu einer studentischen Domain gehoert.
'''
''' Args:
'''     addr: Die zu pruefende E-Mail-Adresse.
'''
''' Returns:
'''     True, wenn die Adresse studentisch ist.
Private Function IsStudentMail(ByVal addr As String) As Boolean
    Dim domains() As String
    Dim d As Variant

    domains = Split(STUDENT_DOMAINS, "|")
    addr = LCase(addr)

    For Each d In domains
        If InStr(addr, CStr(d)) > 0 Then
            IsStudentMail = True
            Exit Function
        End If
    Next d

    IsStudentMail = False
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
    Set addrEntry = mail.sender
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
                Exit Function
            End If
        End If
    End If
RecipError:
    GetFirstRecipientAddress = LCase(recip.Address)
End Function

''' Baut den vollstaendigen Dateipfad fuer eine .msg-Datei zusammen.
'''
''' Args:
'''     folderPath: Zielordner auf dem Dateisystem.
'''     mail:       Das zu speichernde MailItem.
'''
''' Returns:
'''     Vollstaendiger Dateipfad.
Private Function BuildMsgFilePath(ByVal folderPath As String, ByVal mail As Outlook.mailItem) As String
    Dim datePart As String
    Dim subjectPart As String

    datePart = Format(mail.ReceivedTime, "YYYYMMDD_HHMMSS")
    subjectPart = SanitizeFileName(mail.Subject)

    If Len(subjectPart) > 80 Then subjectPart = Left(subjectPart, 80)

    BuildMsgFilePath = folderPath & "\" & datePart & " - " & subjectPart & ".msg"
End Function

''' Entfernt Zeichen, die in Windows-Dateinamen nicht erlaubt sind.
'''
''' Args:
'''     name: Der zu bereinigende String.
'''
''' Returns:
'''     Bereinigter String.
Private Function SanitizeFileName(ByVal name As String) As String
    Dim invalidChars As String
    Dim result As String
    Dim i As Long

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

''' Stellt sicher, dass ein Verzeichnis existiert.
'''
''' Args:
'''     path: Der zu pruefende/erstellende Pfad.
'''
''' Returns:
'''     True, wenn das Verzeichnis existiert oder erstellt wurde.
Private Function EnsureDirectory(ByVal path As String) As Boolean
    Dim fso As Object
    Set fso = CreateObject("Scripting.FileSystemObject")

    If fso.FolderExists(path) Then
        EnsureDirectory = True
        Exit Function
    End If

    Dim parentPath As String
    parentPath = fso.GetParentFolderName(path)

    If Len(parentPath) > 0 Then
        If Not EnsureDirectory(parentPath) Then
            EnsureDirectory = False
            Exit Function
        End If
    End If

    On Error Resume Next
    fso.CreateFolder path
    EnsureDirectory = (Err.Number = 0 Or fso.FolderExists(path))
    On Error GoTo 0
End Function
