' =============================================================================
' AppointmentExport.bas
' Outlook VBA-Makro zum Exportieren von Terminen der kommenden 4 Wochen als Markdown
'
' Funktionsweise:
'   1. Greift auf die Kalender "Kalender (Nur dieser Computer)" UND "Kalender"
'      im Konto "daniel.gaida@th-koeln.de" zu.
'   2. Durchlaeuft die naechsten 4 Wochen (ab heute).
'   3. Extrahiert Datum, Uhrzeit, Dauer, Ort, Thema und Teilnehmer.
'   4. Schreibt alle Termine als Markdown-Tabelle in:
'      D:\TH_Koeln\academic-memory-mcp\data\appointments.md
' =============================================================================

Option Explicit

' -----------------------------------------------------------------------------
' Konfiguration
' -----------------------------------------------------------------------------
Private Const ACCOUNT_NAME    As String = "daniel.gaida@th-koeln.de"
Private Const CALENDAR_NAME   As String = "Kalender (Nur dieser Computer)"
Private Const CALENDAR_NAME_2 As String = "Kalender"
Private Const OUTPUT_PATH    As String = "D:\TH_Koeln\academic-memory-mcp\data\appointments.md"
Private Const LOOKAHEAD_DAYS As Long   = 28 ' 4 Wochen

' =============================================================================
' Hauptprozedur
' =============================================================================

''' Einstiegspunkt fuer das Makro. Sucht beide Kalender und exportiert Termine.
Public Sub ExportAppointments()
    Dim ns          As Outlook.NameSpace
    Dim account     As Outlook.Account
    Dim store       As Outlook.Store
    Dim rootFolder  As Outlook.Folder
    Dim cal1        As Outlook.Folder
    Dim cal2        As Outlook.Folder
    Dim startDate   As Date
    Dim endDate     As Date
    Dim fileNum     As Integer
    Dim parentDir   As String

    Set ns = Application.GetNamespace("MAPI")

    ' Konto suchen
    On Error Resume Next
    Set account = ns.Accounts.Item(ACCOUNT_NAME)
    On Error GoTo 0

    If account Is Nothing Then
        MsgBox "Konto '" & ACCOUNT_NAME & "' wurde nicht gefunden.", vbCritical
        Exit Sub
    End If

    Set store = account.DeliveryStore
    Set rootFolder = store.GetRootFolder()

    ' Kalender-Ordner suchen
    On Error Resume Next
    Set cal1 = rootFolder.Folders(CALENDAR_NAME)
    Set cal2 = rootFolder.Folders(CALENDAR_NAME_2)
    On Error GoTo 0

    If cal1 Is Nothing And cal2 Is Nothing Then
        MsgBox "Keiner der Kalender wurde gefunden.", vbCritical
        Exit Sub
    End If

    startDate = Date
    endDate = DateAdd("d", LOOKAHEAD_DAYS, startDate)

    ' Markdown Datei vorbereiten
    parentDir = Left(OUTPUT_PATH, InStrRev(OUTPUT_PATH, "\") - 1)
    If Not EnsureDirectory(parentDir) Then
        MsgBox "Zielverzeichnis konnte nicht erstellt werden: " & parentDir, vbCritical
        Exit Sub
    End If

    fileNum = FreeFile()
    Open OUTPUT_PATH For Output As #fileNum

    Print #fileNum, "# Termine der kommenden 4 Wochen"
    Print #fileNum, ""
    Print #fileNum, "Zeitraum: " & Format(startDate, "YYYY-MM-DD") & " bis " & Format(endDate, "YYYY-MM-DD")
    Print #fileNum, "Generiert am: " & Format(Now, "YYYY-MM-DD HH:MM:SS")
    Print #fileNum, ""
    Print #fileNum, "| Datum | Uhrzeit | Dauer (Min) | Ort | Thema | Teilnehmer |"
    Print #fileNum, "| :--- | :--- | :--- | :--- | :--- | :--- |"

    ' Termine aus beiden Kalendern verarbeiten
    ProcessCalendar cal1, startDate, endDate, fileNum
    ProcessCalendar cal2, startDate, endDate, fileNum

    Close #fileNum

    MsgBox "Export abgeschlossen in " & OUTPUT_PATH, vbInformation
End Sub

''' Durchlaeuft einen Kalender-Ordner und schreibt gefilterte Termine in die Datei.
Private Sub ProcessCalendar(ByVal calFolder As Outlook.Folder, ByVal startDate As Date, ByVal endDate As Date, ByVal fileNum As Integer)
    If calFolder Is Nothing Then Exit Sub

    Dim items As Outlook.Items
    Dim appt As Object
    Dim filter As String

    Set items = calFolder.Items
    items.IncludeRecurrences = True
    items.Sort "[Start]"

    ' Outlook Filter Format: MM/DD/YYYY HH:MM AM/PM
    ' Wir filtern grob auf den Zeitraum.
    filter = "[Start] >= """ & Month(startDate) & "/" & Day(startDate) & "/" & Year(startDate) & " 00:00 AM""" & _
             " AND [Start] <= """ & Month(endDate) & "/" & Day(endDate) & "/" & Year(endDate) & " 11:59 PM"""

    Set items = items.Restrict(filter)

    For Each appt In items
        If TypeOf appt Is AppointmentItem Then
            WriteAppointmentToMarkdown appt, fileNum
        End If
    Next appt
End Sub

''' Formatiert ein AppointmentItem als Tabellenzeile.
Private Sub WriteAppointmentToMarkdown(ByVal appt As Outlook.AppointmentItem, ByVal fileNum As Integer)
    Dim participants As String
    participants = GetRecipientEmails(appt)

    ' | Datum | Uhrzeit | Dauer (Min) | Ort | Thema | Teilnehmer |
    Print #fileNum, "| " & Format(appt.Start, "YYYY-MM-DD") & _
                    " | " & Format(appt.Start, "HH:MM") & _
                    " | " & appt.Duration & _
                    " | " & SanitizeMarkdown(appt.Location) & _
                    " | " & SanitizeMarkdown(appt.Subject) & _
                    " | " & participants & " |"
End Sub

''' Extrahiert alle Teilnehmer-E-Mail-Adressen.
Private Function GetRecipientEmails(ByVal appt As Outlook.AppointmentItem) As String
    Dim recip As Outlook.Recipient
    Dim result As String
    Dim addr As String

    For Each recip In appt.Recipients
        addr = GetSmtpAddress(recip)
        If Len(addr) > 0 Then
            If Len(result) > 0 Then result = result & "; "
            result = result & addr
        End If
    Next recip

    GetRecipientEmails = result
End Function

''' Versucht die SMTP-Adresse eines Empfaengers zu ermitteln.
Private Function GetSmtpAddress(ByVal recip As Outlook.Recipient) As String
    On Error Resume Next
    Dim addrEntry As Outlook.AddressEntry
    Set addrEntry = recip.AddressEntry

    If addrEntry Is Nothing Then
        GetSmtpAddress = recip.Address
        Exit Function
    End If

    If addrEntry.AddressEntryUserType = olExchangeUserAddressEntry Or _
       addrEntry.AddressEntryUserType = olExchangeRemoteUserAddressEntry Then
        Dim exchUser As Outlook.ExchangeUser
        Set exchUser = addrEntry.GetExchangeUser()
        If Not exchUser Is Nothing Then
            GetSmtpAddress = exchUser.PrimarySmtpAddress
            Exit Function
        End If
    End If

    GetSmtpAddress = recip.Address
    On Error GoTo 0
End Function

''' Bereinigt Text fuer Markdown-Tabellen (entfernt Pipes und Zeilenumbrueche).
Private Function SanitizeMarkdown(ByVal text As String) As String
    Dim result As String
    result = Replace(text, "|", "\|")
    result = Replace(result, vbCrLf, " ")
    result = Replace(result, vbCr, " ")
    result = Replace(result, vbLf, " ")
    SanitizeMarkdown = Trim(result)
End Function

''' Stellt sicher, dass ein Verzeichnis existiert.
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
