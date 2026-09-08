' =============================================================================
' AppointmentExport.bas
' Outlook VBA-Makro zum Exportieren von Terminen der kommenden 4 Wochen als Markdown
'
' Funktionsweise:
'   1. Greift auf die Kalender "Kalender (Nur dieser Computer)" UND "Kalender"
'      im Konto "daniel.gaida@th-koeln.de" zu.
'   2. Durchlaeuft die naechsten 4 Wochen (ab heute).
'   3. Extrahiert Datum, Uhrzeit, Dauer, Ort, Thema und Teilnehmer.
'   4. Schreibt alle Termine als Markdown-Tabelle in UTF-8 kodiert in:
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

' Private Status-Log-Schnittstelle zur Fehlerdiagnose
Private statusLog As String

' =============================================================================
' Hilfsprozeduren für Logging
' =============================================================================

''' Protokolliert eine Statusmeldung im privaten Log und im Debug-Fenster.
'''
''' Args:
'''     msg: Die zu protokollierende Meldung.
Private Sub LogStatus(ByVal msg As String)
    Debug.Print msg
    statusLog = statusLog & Format(Now, "HH:MM:SS") & " - " & msg & vbCrLf
End Sub

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
    Dim parentDir   As String
    Dim utf8Stream  As Object
    Dim idx         As Long

    statusLog = ""
    LogStatus "Starte Terminexport..."
    LogStatus "Zielpfad: " & OUTPUT_PATH

    Set ns = Application.GetNamespace("MAPI")

    ' Konto robust suchen via Loop über alle Accounts (prüft SMTP-Adresse und DisplayName)
    On Error Resume Next
    For idx = 1 To ns.Accounts.Count
        Set account = ns.Accounts.Item(idx)
        LogStatus "Prüfe Konto " & idx & ": SMTP='" & account.SmtpAddress & "', Name='" & account.DisplayName & "'"
        If LCase(account.SmtpAddress) = LCase(ACCOUNT_NAME) Or LCase(account.DisplayName) = LCase(ACCOUNT_NAME) Then
            LogStatus "Konto erfolgreich gefunden: " & account.SmtpAddress
            Exit For
        End If
        Set account = Nothing
    Next idx
    On Error GoTo 0

    ' Fallback auf Standard-Store, falls das Konto nicht explizit gefunden wurde
    If account Is Nothing Then
        LogStatus "HINWEIS: Konto '" & ACCOUNT_NAME & "' wurde nicht explizit in den Konten gefunden. Verwende Default-Store."
        On Error Resume Next
        Set store = ns.DefaultStore
        On Error GoTo 0
    Else
        Set store = account.DeliveryStore
    End If

    If store Is Nothing Then
        LogStatus "FEHLER: Store konnte nicht ermittelt werden."
        MsgBox "Store konnte nicht geladen werden." & vbCrLf & vbCrLf & "Status-Log:" & vbCrLf & statusLog, vbCritical, "Terminexport Fehler"
        Exit Sub
    End If

    LogStatus "Nutze Store: " & store.DisplayName
    Set rootFolder = store.GetRootFolder()

    ' Kalender-Ordner suchen
    On Error Resume Next
    Set cal1 = rootFolder.Folders(CALENDAR_NAME)
    If Not cal1 Is Nothing Then
        LogStatus "Kalender 1 '" & CALENDAR_NAME & "' in rootFolder gefunden."
    Else
        LogStatus "Kalender 1 '" & CALENDAR_NAME & "' nicht direkt in rootFolder gefunden."
    End If

    Set cal2 = rootFolder.Folders(CALENDAR_NAME_2)
    If Not cal2 Is Nothing Then
        LogStatus "Kalender 2 '" & CALENDAR_NAME_2 & "' in rootFolder gefunden."
    Else
        LogStatus "Kalender 2 '" & CALENDAR_NAME_2 & "' nicht direkt in rootFolder gefunden."
    End If
    On Error GoTo 0

    ' Fallback für Kalender 1: Standard-Kalender des Stores (olFolderCalendar = 9)
    If cal1 Is Nothing Then
        LogStatus "Suche Fallback-Kalender für Kalender 1 via store.GetDefaultFolder..."
        On Error Resume Next
        Set cal1 = store.GetDefaultFolder(olFolderCalendar)
        On Error GoTo 0
        If Not cal1 Is Nothing Then
            LogStatus "Fallback-Kalender 1 gefunden: " & cal1.Name & " (" & cal1.FolderPath & ")"
        Else
            LogStatus "FEHLER: store.GetDefaultFolder(olFolderCalendar) schlug fehl."
        End If
    End If

    If cal1 Is Nothing And cal2 Is Nothing Then
        LogStatus "FEHLER: Keiner der Kalender wurde gefunden."
        MsgBox "Keiner der Kalender wurde gefunden." & vbCrLf & vbCrLf & "Status-Log:" & vbCrLf & statusLog, vbCritical, "Terminexport Fehler"
        Exit Sub
    End If

    startDate = Date
    endDate = DateAdd("d", LOOKAHEAD_DAYS, startDate)

    ' Markdown Datei vorbereiten
    parentDir = Left(OUTPUT_PATH, InStrRev(OUTPUT_PATH, "\") - 1)
    If Not EnsureDirectory(parentDir) Then
        LogStatus "FEHLER: Zielverzeichnis konnte nicht erstellt werden: " & parentDir
        MsgBox "Zielverzeichnis konnte nicht erstellt werden: " & parentDir & vbCrLf & vbCrLf & "Status-Log:" & vbCrLf & statusLog, vbCritical, "Terminexport Fehler"
        Exit Sub
    End If

    ' ADODB.Stream fuer UTF-8 verwenden
    Set utf8Stream = CreateObject("ADODB.Stream")
    utf8Stream.Type = 2 ' adTypeText
    utf8Stream.Charset = "utf-8"
    utf8Stream.Open

    utf8Stream.WriteText "# Termine der kommenden 4 Wochen" & vbCrLf
    utf8Stream.WriteText vbCrLf
    utf8Stream.WriteText "Zeitraum: " & Format(startDate, "YYYY-MM-DD") & " bis " & Format(endDate, "YYYY-MM-DD") & vbCrLf
    utf8Stream.WriteText "Generiert am: " & Format(Now, "YYYY-MM-DD HH:MM:SS") & vbCrLf
    utf8Stream.WriteText vbCrLf
    utf8Stream.WriteText "| Datum | Uhrzeit | Dauer (Min) | Ort | Thema | Teilnehmer |" & vbCrLf
    utf8Stream.WriteText "| :--- | :--- | :--- | :--- | :--- | :--- |" & vbCrLf

    ' Termine aus beiden Kalendern verarbeiten
    ProcessCalendar cal1, startDate, endDate, utf8Stream
    ProcessCalendar cal2, startDate, endDate, utf8Stream

    utf8Stream.SaveToFile OUTPUT_PATH, 2 ' adSaveCreateOverWrite
    utf8Stream.Close

    LogStatus "Export erfolgreich abgeschlossen in " & OUTPUT_PATH
    MsgBox "Export abgeschlossen in " & OUTPUT_PATH & vbCrLf & vbCrLf & "Status-Log:" & vbCrLf & statusLog, vbInformation, "Terminexport Erfolgreich"
End Sub

''' Durchlaeuft einen Kalender-Ordner und schreibt gefilterte Termine in den Stream.
'''
''' Args:
'''     calFolder: Der zu verarbeitende Kalenderordner.
'''     startDate: Der Beginn des Zeitraums.
'''     endDate: Das Ende des Zeitraums.
'''     utf8Stream: Das ADODB.Stream Objekt zum Schreiben.
Private Sub ProcessCalendar(ByVal calFolder As Outlook.Folder, ByVal startDate As Date, ByVal endDate As Date, ByRef utf8Stream As Object)
    If calFolder Is Nothing Then
        LogStatus "ProcessCalendar übersprungen, da calFolder Nothing ist."
        Exit Sub
    End If

    LogStatus "Verarbeite Kalender: " & calFolder.Name & " (Pfad: " & calFolder.FolderPath & ")"

    Dim items           As Outlook.Items
    Dim appt            As Object
    Dim filter1         As String
    Dim filter2         As String
    Dim filter3         As String
    Dim res1            As Outlook.Items
    Dim res2            As Outlook.Items
    Dim restrictedItems As Outlook.Items
    Dim totalCount      As Long
    Dim matchedCount    As Long
    Dim processedCount  As Long
    Dim nextDay         As Date

    On Error GoTo ErrHandler

    Set items = calFolder.Items
    totalCount = items.Count
    LogStatus "Anzahl Termine im Kalender vor Filterung: " & totalCount

    items.IncludeRecurrences = True
    items.Sort "[Start]"

    nextDay = DateAdd("d", 1, endDate)

    ' Schritt 1: Einzel-Filter 1 ab startDate
    filter1 = "[End] >= """ & Month(startDate) & "/" & Day(startDate) & "/" & Year(startDate) & """"
    LogStatus "Anzuwendender Filter 1 (Start/Ab heute): " & filter1
    Set res1 = items.Restrict(filter1)
    matchedCount = res1.Count
    If matchedCount = 2147483647 Then
        LogStatus "Anzahl Termine nach Filter 1: dynamisch / unendlich (IncludeRecurrences=True)"
    Else
        LogStatus "Anzahl Termine nach Filter 1: " & matchedCount
    End If

    ' Schritt 2: Einzel-Filter 2 bis endDate
    filter2 = "[Start] < """ & Month(nextDay) & "/" & Day(nextDay) & "/" & Year(nextDay) & """"
    LogStatus "Anzuwendender Filter 2 (Ende): " & filter2
    Set res2 = items.Restrict(filter2)
    matchedCount = res2.Count
    If matchedCount = 2147483647 Then
        LogStatus "Anzahl Termine nach Filter 2: dynamisch / unendlich (IncludeRecurrences=True)"
    Else
        LogStatus "Anzahl Termine nach Filter 2: " & matchedCount
    End If

    ' Schritt 3: Kombinationsfilter (Filter 1 AND Filter 2)
    filter3 = "[End] >= """ & Month(startDate) & "/" & Day(startDate) & "/" & Year(startDate) & """" & _
              " AND [Start] < """ & Month(nextDay) & "/" & Day(nextDay) & "/" & Year(nextDay) & """"
    LogStatus "Anzuwendender Filter 3 (Kombination): " & filter3
    Set restrictedItems = items.Restrict(filter3)
    matchedCount = restrictedItems.Count
    If matchedCount = 2147483647 Then
        LogStatus "Anzahl Termine nach Filter 3 (Kombination): dynamisch / unendlich (IncludeRecurrences=True)"
    Else
        LogStatus "Anzahl Termine nach Filter 3 (Kombination): " & matchedCount
    End If

    processedCount = 0
    For Each appt In restrictedItems
        If TypeOf appt Is AppointmentItem Then
            ' Zusätzliche manuelle Sicherheitsprüfung auf Datumsbereich
            If appt.Start <= nextDay And appt.End >= startDate Then
                WriteAppointmentToStream appt, utf8Stream
                processedCount = processedCount + 1
            End If
        End If
    Next appt

    LogStatus "Erfolgreich exportierte Termine für '" & calFolder.Name & "': " & processedCount
    Exit Sub

ErrHandler:
    LogStatus "FEHLER in ProcessCalendar für '" & calFolder.Name & "': " & Err.Description
    Resume Next
End Sub

''' Formatiert ein AppointmentItem als Tabellenzeile.
'''
''' Args:
'''     appt: Das zu exportierende AppointmentItem.
'''     utf8Stream: Das Stream-Objekt zum Schreiben.
Private Sub WriteAppointmentToStream(ByVal appt As Outlook.AppointmentItem, ByRef utf8Stream As Object)
    Dim participants As String
    participants = GetRecipientEmails(appt)

    ' | Datum | Uhrzeit | Dauer (Min) | Ort | Thema | Teilnehmer |
    utf8Stream.WriteText "| " & Format(appt.Start, "YYYY-MM-DD") & _
                         " | " & Format(appt.Start, "HH:MM") & _
                         " | " & appt.Duration & _
                         " | " & SanitizeMarkdown(appt.Location) & _
                         " | " & SanitizeMarkdown(appt.Subject) & _
                         " | " & participants & " |" & vbCrLf
End Sub

''' Extrahiert alle Teilnehmer-E-Mail-Adressen.
'''
''' Args:
'''     appt: Das AppointmentItem.
'''
''' Returns:
'''     E-Mail-Adressen der Teilnehmer, durch Semikolon getrennt.
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
'''
''' Args:
'''     recip: Der Empfänger des Termins.
'''
''' Returns:
'''     Die SMTP-E-Mail-Adresse.
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
'''
''' Args:
'''     text: Der zu bereinigende Text.
'''
''' Returns:
'''     Der bereinigte Text.
Private Function SanitizeMarkdown(ByVal text As String) As String
    Dim result As String
    result = Replace(text, "|", "\|")
    result = Replace(result, vbCrLf, " ")
    result = Replace(result, vbCr, " ")
    result = Replace(result, vbLf, " ")
    SanitizeMarkdown = Trim(result)
End Function

''' Stellt sicher, dass ein Verzeichnis existiert.
'''
''' Args:
'''     path: Das Verzeichnis, das erstellt werden soll.
'''
''' Returns:
'''     True, wenn das Verzeichnis existiert oder erfolgreich erstellt wurde.
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
