' =============================================================================
' FreeSlotExport.bas
' Outlook VBA-Makro zum Exportieren freier Kalender-Slots als Markdown-Datei
'
' Funktionsweise:
'   1. Greift auf die Kalender "Kalender (Nur dieser Computer)" UND "Kalender"
'      im Konto "daniel.gaida@th-koeln.de" zu.
'   2. Durchlaeuft die naechsten 14 Tage (ab heute).
'   3. Prueft fuer jeden Werktag (ohne Feiertage, ohne konfigurierte Ausnahme-
'      Wochentage) das Zeitfenster 13:30 - 16:00 Uhr im 30-Minuten-Takt.
'   4. Ein 30-Minuten-Slot gilt als frei, wenn kein Termin (ausser ganztaegigen)
'      in BEIDEN Kalendern in diesen Zeitraum faellt.
'   5. Schreibt alle freien Slots als Markdown-Liste in:
'      D:\TH_Koeln\academic-memory-mcp\data\free_slots.md
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

' -----------------------------------------------------------------------------
' Konfiguration
' -----------------------------------------------------------------------------
Private Const ACCOUNT_NAME       As String = "daniel.gaida@th-koeln.de"
Private Const CALENDAR_NAME      As String = "Kalender (Nur dieser Computer)"
Private Const CALENDAR_NAME_2    As String = "Kalender"   ' zweiter Kalender im selben Postfach
Private Const OUTPUT_PATH       As String = "D:\TH_Koeln\academic-memory-mcp\data\free_slots.md"
Private Const SLOT_WINDOW_START As String = "13:30"   ' Fenster-Beginn (HH:MM)
Private Const SLOT_WINDOW_END   As String = "16:00"   ' Fenster-Ende   (HH:MM)
Private Const SLOT_DURATION_MIN As Long   = 30        ' Slot-Laenge in Minuten
Private Const LOOKAHEAD_DAYS    As Long   = 14        ' Betrachtungszeitraum

' Wochentage, die AUSGESCHLOSSEN werden sollen (VBA: 1=So, 2=Mo, ..., 7=Sa)
' Aktuell: Mittwoch (4) und Freitag (6)
Private Const EXCLUDED_WEEKDAYS As String = "4|6"

' =============================================================================
' Hauptprozedur
' =============================================================================

''' Einstiegspunkt fuer das Makro. Sucht beide Kalender und exportiert freie Slots.
Public Sub ExportFreeSlots()
    Dim ns           As Outlook.NameSpace
    Dim calFolder    As Outlook.Folder
    Dim calFolder2   As Outlook.Folder
    Dim freeSlots()  As String
    Dim slotCount    As Long

    Set ns = Application.GetNamespace("MAPI")

    ' Beide Kalender-Ordner ermitteln
    Set calFolder  = FindCalendarFolder(ns, CALENDAR_NAME)
    Set calFolder2 = FindCalendarFolder(ns, CALENDAR_NAME_2)

    If calFolder Is Nothing Then
        MsgBox "Kalender '" & CALENDAR_NAME & "' im Konto '" & ACCOUNT_NAME & _
               "' wurde nicht gefunden.", vbCritical, "FreeSlotExport"
        Exit Sub
    End If
    If calFolder2 Is Nothing Then
        MsgBox "Kalender '" & CALENDAR_NAME_2 & "' im Konto '" & ACCOUNT_NAME & _
               "' wurde nicht gefunden.", vbCritical, "FreeSlotExport"
        Exit Sub
    End If

    ' Freie Slots berechnen (Slot muss in BEIDEN Kalendern frei sein)
    ReDim freeSlots(0 To 0)
    slotCount = 0
    CollectFreeSlots calFolder, calFolder2, freeSlots, slotCount

    ' Ausgabe-Verzeichnis sicherstellen
    Dim outDir As String
    outDir = Left(OUTPUT_PATH, InStrRev(OUTPUT_PATH, "\") - 1)
    If Not EnsureDirectory(outDir) Then
        MsgBox "Ausgabeverzeichnis konnte nicht erstellt werden: " & outDir, _
               vbCritical, "FreeSlotExport"
        Exit Sub
    End If

    ' Markdown-Datei schreiben
    WriteSlotsToMarkdown freeSlots, slotCount

    MsgBox "Export abgeschlossen! " & slotCount & " freie Slots gefunden." & vbCrLf & _
           "Datei: " & OUTPUT_PATH, vbInformation, "FreeSlotExport"
End Sub

' =============================================================================
' Kalender-Suche
' =============================================================================

''' Sucht einen Kalender-Ordner per Name im gewuenschten Konto.
'''
''' Args:
'''     ns:          Der MAPI-Namespace von Outlook.
'''     calName:     Name des gesuchten Kalender-Ordners.
'''
''' Returns:
'''     Outlook.Folder des Kalenders oder Nothing, falls nicht gefunden.
Private Function FindCalendarFolder(ByVal ns As Outlook.NameSpace, _
                                     ByVal calName As String) As Outlook.Folder
    Dim acct        As Outlook.Account
    Dim store       As Outlook.Store
    Dim rootFolder  As Outlook.Folder
    Dim subFolder   As Outlook.Folder

    ' Ziel-Konto suchen
    Dim i As Long
    For i = 1 To ns.Accounts.Count
        Set acct = ns.Accounts.Item(i)
        If LCase(acct.SmtpAddress) = LCase(ACCOUNT_NAME) Then

            Set store      = acct.DeliveryStore
            Set rootFolder = store.GetRootFolder()

            ' Kalender-Ordner per Name suchen (ein Level tief)
            Dim j As Long
            For j = 1 To rootFolder.Folders.Count
                Set subFolder = rootFolder.Folders(j)
                If subFolder.Name = calName Then
                    Set FindCalendarFolder = subFolder
                    Exit Function
                End If
            Next j

            ' Fallback nur fuer den primaeren Kalender: Standard-Kalender (olFolderCalendar = 9)
            If calName = CALENDAR_NAME Then
                On Error Resume Next
                Set FindCalendarFolder = store.GetDefaultFolder(olFolderCalendar)
                On Error GoTo 0
            End If
            Exit Function
        End If
    Next i

    Set FindCalendarFolder = Nothing
End Function

' =============================================================================
' Slot-Berechnung
' =============================================================================

''' Durchlaeuft die naechsten LOOKAHEAD_DAYS Tage und sammelt freie Slots.
''' Ein Slot wird nur aufgenommen, wenn er in BEIDEN Kalendern frei ist.
'''
''' Args:
'''     calFolder:   Erster Outlook-Kalender-Ordner.
'''     calFolder2:  Zweiter Outlook-Kalender-Ordner.
'''     freeSlots:   Dynamisches String-Array, das befuellt wird.
'''     slotCount:   Zaehler der gefundenen Slots (wird in-place erhoeht).
Private Sub CollectFreeSlots(ByVal calFolder As Outlook.Folder, _
                              ByVal calFolder2 As Outlook.Folder, _
                              ByRef freeSlots() As String, _
                              ByRef slotCount As Long)
    Dim today       As Date
    Dim checkDate   As Date
    Dim dayOffset   As Long

    today = Date ' aktuelles Datum (ohne Uhrzeit)

    For dayOffset = 0 To LOOKAHEAD_DAYS - 1
        checkDate = today + dayOffset

        ' Wochenenden ueberspringen (Weekday: 1=So, 7=Sa)
        If Weekday(checkDate) = 1 Or Weekday(checkDate) = 7 Then GoTo NextDay

        ' Ausgeschlossene Wochentage ueberspringen
        If IsExcludedWeekday(Weekday(checkDate)) Then GoTo NextDay

        ' Feiertage ueberspringen (NRW-Feiertage)
        If IsPublicHoliday(checkDate) Then GoTo NextDay

        ' Freie Slots fuer diesen Tag ermitteln (beide Kalender)
        CollectFreeSlotsForDay calFolder, calFolder2, checkDate, freeSlots, slotCount

        ' Outlook reaktionsfaehig halten
        DoEvents
        Sleep 50

NextDay:
    Next dayOffset
End Sub

''' Prueft alle 30-Minuten-Slots im konfigurierten Fenster fuer einen Tag.
''' Nur Slots, die in BEIDEN Kalendern frei sind, werden aufgenommen.
'''
''' Args:
'''     calFolder:   Erster Outlook-Kalender-Ordner.
'''     calFolder2:  Zweiter Outlook-Kalender-Ordner.
'''     checkDate:   Das zu pruefende Datum.
'''     freeSlots:   Dynamisches String-Array fuer Ergebnisse.
'''     slotCount:   Laufender Zaehler der freien Slots.
Private Sub CollectFreeSlotsForDay(ByVal calFolder As Outlook.Folder, _
                                    ByVal calFolder2 As Outlook.Folder, _
                                    ByVal checkDate As Date, _
                                    ByRef freeSlots() As String, _
                                    ByRef slotCount As Long)
    Dim windowStart  As Date
    Dim windowEnd    As Date
    Dim slotStart    As Date
    Dim slotEnd      As Date

    ' Absoluter Start/Ende-Zeitpunkt fuer diesen Tag
    windowStart = CDate(Format(checkDate, "YYYY-MM-DD") & " " & SLOT_WINDOW_START)
    windowEnd   = CDate(Format(checkDate, "YYYY-MM-DD") & " " & SLOT_WINDOW_END)

    ' Termine beider Kalender einmal laden (gefiltert auf das Fenster)
    Dim dayItems1 As Outlook.Items
    Dim dayItems2 As Outlook.Items
    Set dayItems1 = GetAppointmentsForWindow(calFolder,  windowStart, windowEnd)
    Set dayItems2 = GetAppointmentsForWindow(calFolder2, windowStart, windowEnd)

    ' Alle Slots im Fenster pruefen
    slotStart = windowStart
    Do While slotStart < windowEnd
        slotEnd = slotStart + TimeSerial(0, SLOT_DURATION_MIN, 0)

        ' Slot passt nicht mehr ins Fenster (> statt >= um 15:30-16:00 einzuschliessen)
        If slotEnd > windowEnd Then Exit Do

        ' Slot nur aufnehmen wenn er in BEIDEN Kalendern frei ist
        If IsSlotFree(dayItems1, slotStart, slotEnd) And _
           IsSlotFree(dayItems2, slotStart, slotEnd) Then
            If slotCount >= UBound(freeSlots) + 1 Then
                ReDim Preserve freeSlots(0 To slotCount)
            End If
            freeSlots(slotCount) = FormatSlot(slotStart, slotEnd)
            slotCount = slotCount + 1
        End If

        slotStart = slotEnd ' naechster Slot
    Loop
End Sub

''' Laedt alle nicht-ganztaegigen Termine eines Kalender-Ordners fuer ein Zeitfenster.
'''
''' Args:
'''     calFolder:   Der Outlook-Kalender-Ordner.
'''     windowStart: Beginn des Zeitfensters.
'''     windowEnd:   Ende des Zeitfensters.
'''
''' Returns:
'''     Gefiltertes Outlook.Items-Objekt.
Private Function GetAppointmentsForWindow(ByVal calFolder As Outlook.Folder, _
                                           ByVal windowStart As Date, _
                                           ByVal windowEnd As Date) As Outlook.Items
    Dim allItems    As Outlook.Items
    Dim restricted  As Outlook.Items
    Dim filterStr   As String

    Set allItems = calFolder.Items
    allItems.IncludeRecurrences = True ' Serienelemente einbeziehen
    allItems.Sort "[Start]"

    ' Filter auf den gesamten Tag, nicht auf das engere Zeitfenster.
    ' Grund: Format(..., "HH:MM AM/PM") liefert unter deutschen Systemeinstellungen
    ' kein gueltiges AM/PM-Suffix, was den Restrict-Filter unzuverlaessig macht.
    ' Die genaue Zeitpruefung uebernimmt IsSlotFree zuverlaessig per VBA-Vergleich.
    Dim dayStart As Date
    Dim dayEnd   As Date
    dayStart = Int(windowStart)     ' Mitternacht des Tages
    dayEnd   = Int(windowStart) + 1 ' Mitternacht des Folgetags

    ' Format() respektiert die Windows-Locale und liefert auf deutschen Systemen
    ' "TT.MM.JJJJ" statt "MM/DD/YYYY". Outlook-Filter braucht zwingend MM/DD/YYYY,
    ' daher manuell aus den Datumsteilen zusammenbauen (locale-unabhaengig).
    filterStr = "[Start] < """ & Month(dayEnd)   & "/" & Day(dayEnd)   & "/" & Year(dayEnd)   & """ " & _
                "AND [End] > """ & Month(dayStart) & "/" & Day(dayStart) & "/" & Year(dayStart) & """"

    Set restricted = allItems.Restrict(filterStr)
    Set GetAppointmentsForWindow = restricted
End Function

''' Prueft, ob ein Slot (slotStart bis slotEnd) frei ist.
''' Ganztaegige Termine werden ignoriert.
'''
''' Args:
'''     dayItems:   Bereits gefiltertes Items-Objekt fuer das Zeitfenster.
'''     slotStart:  Beginn des Slots.
'''     slotEnd:    Ende des Slots.
'''
''' Returns:
'''     True, wenn keine Ueberschneidung mit einem nicht-ganztaegigen Termin vorliegt.
Private Function IsSlotFree(ByVal dayItems As Outlook.Items, _
                              ByVal slotStart As Date, _
                              ByVal slotEnd As Date) As Boolean
    Dim appt As Object

    For Each appt In dayItems
        If TypeOf appt Is Outlook.AppointmentItem Then
            Dim apptItem As Outlook.AppointmentItem
            Set apptItem = appt

            ' Ganztaegige Termine nicht als Blocker werten
            If apptItem.AllDayEvent Then GoTo NextAppt

            ' Ueberschneidung: Termin beginnt vor Slot-Ende UND endet nach Slot-Start
            If apptItem.Start < slotEnd And apptItem.End > slotStart Then
                IsSlotFree = False
                Exit Function
            End If
        End If
NextAppt:
    Next appt

    IsSlotFree = True
End Function

' =============================================================================
' Feiertags-Pruefung (NRW)
' =============================================================================

''' Prueft, ob ein Datum ein gesetzlicher Feiertag in NRW ist.
''' Beruecksichtigt feste und bewegliche Feiertage.
'''
''' Args:
'''     checkDate: Das zu pruefende Datum.
'''
''' Returns:
'''     True, wenn der Tag ein NRW-Feiertag ist.
Private Function IsPublicHoliday(ByVal checkDate As Date) As Boolean
    Dim y       As Long
    Dim easter  As Date

    y      = Year(checkDate)
    easter = CalcEasterSunday(y)

    ' --- Feste Feiertage ---
    Dim fixedHolidays(8) As String
    fixedHolidays(0) = "01/01"  ' Neujahr
    fixedHolidays(1) = "05/01"  ' Tag der Arbeit
    fixedHolidays(2) = "10/03"  ' Tag der Deutschen Einheit
    fixedHolidays(3) = "11/01"  ' Allerheiligen (NRW)
    fixedHolidays(4) = "12/25"  ' 1. Weihnachtstag
    fixedHolidays(5) = "12/26"  ' 2. Weihnachtstag
    fixedHolidays(6) = "12/24"  ' Heiligabend (kein gesetzlicher FT, aber oft blockiert)
    fixedHolidays(7) = "12/31"  ' Silvester (kein gesetzlicher FT, optional)
    fixedHolidays(8) = ""       ' Platzhalter

    Dim mmdd As String
    mmdd = Format(checkDate, "MM/DD")
    Dim i As Long
    For i = 0 To 6 ' Nur gesetzliche pruefen (0-5), Heiligabend/Silvester weglassen
        If fixedHolidays(i) = mmdd Then
            IsPublicHoliday = True
            Exit Function
        End If
    Next i

    ' --- Bewegliche Feiertage (relativ zu Ostersonntag) ---
    If checkDate = easter - 2     Then IsPublicHoliday = True  : Exit Function ' Karfreitag
    If checkDate = easter         Then IsPublicHoliday = True  : Exit Function ' Ostersonntag
    If checkDate = easter + 1     Then IsPublicHoliday = True  : Exit Function ' Ostermontag
    If checkDate = easter + 39    Then IsPublicHoliday = True  : Exit Function ' Christi Himmelfahrt
    If checkDate = easter + 49    Then IsPublicHoliday = True  : Exit Function ' Pfingstsonntag
    If checkDate = easter + 50    Then IsPublicHoliday = True  : Exit Function ' Pfingstmontag
    If checkDate = easter + 60    Then IsPublicHoliday = True  : Exit Function ' Fronleichnam (NRW)

    IsPublicHoliday = False
End Function

''' Berechnet den Ostersonntag fuer ein gegebenes Jahr (Algorithmus nach Gauss/Spencer).
'''
''' Args:
'''     y: Das Jahr.
'''
''' Returns:
'''     Datum des Ostersonntags.
Private Function CalcEasterSunday(ByVal y As Long) As Date
    Dim a As Long, b As Long, c As Long, d As Long, e As Long
    Dim f As Long, g As Long, h As Long, i As Long, k As Long
    Dim l As Long, m As Long, eMonth As Long, eDay As Long

    a = y Mod 19
    b = y \ 100
    c = y Mod 100
    d = b \ 4
    e = b Mod 4
    f = (b + 8) \ 25
    g = (b - f + 1) \ 3
    h = (19 * a + b - d - g + 15) Mod 30
    i = c \ 4
    k = c Mod 4
    l = (32 + 2 * e + 2 * i - h - k) Mod 7
    m = (a + 11 * h + 22 * l) \ 451
    eMonth = (h + l - 7 * m + 114) \ 31
    eDay   = ((h + l - 7 * m + 114) Mod 31) + 1

    CalcEasterSunday = DateSerial(y, eMonth, eDay)
End Function

' =============================================================================
' Hilfsfunktionen
' =============================================================================

''' Prueft, ob ein Wochentag in der Ausschlussliste steht.
'''
''' Args:
'''     wd: VBA-Weekday-Wert (1=So, 2=Mo, ..., 7=Sa).
'''
''' Returns:
'''     True, wenn der Wochentag ausgeschlossen ist.
Private Function IsExcludedWeekday(ByVal wd As Long) As Boolean
    Dim excluded() As String
    Dim d As Variant

    excluded = Split(EXCLUDED_WEEKDAYS, "|")
    For Each d In excluded
        If CLng(d) = wd Then
            IsExcludedWeekday = True
            Exit Function
        End If
    Next d

    IsExcludedWeekday = False
End Function

''' Formatiert einen Slot als lesbaren String.
'''
''' Args:
'''     slotStart: Beginn des Slots.
'''     slotEnd:   Ende des Slots.
'''
''' Returns:
'''     Formatierter String, z.B. "Mo, 2025-06-02 13:30-14:00".
Private Function FormatSlot(ByVal slotStart As Date, ByVal slotEnd As Date) As String
    Dim weekdayNames(1 To 7) As String
    weekdayNames(1) = "So"
    weekdayNames(2) = "Mo"
    weekdayNames(3) = "Di"
    weekdayNames(4) = "Mi"
    weekdayNames(5) = "Do"
    weekdayNames(6) = "Fr"
    weekdayNames(7) = "Sa"

    FormatSlot = weekdayNames(Weekday(slotStart)) & ", " & _
                 Format(slotStart, "YYYY-MM-DD") & " " & _
                 Format(slotStart, "HH:MM") & "-" & _
                 Format(slotEnd, "HH:MM")
End Function

''' Schreibt die gesammelten freien Slots als Markdown-Datei.
'''
''' Args:
'''     freeSlots: Array mit formatierten Slot-Strings.
'''     slotCount: Anzahl der gueltigen Eintraege im Array.
Private Sub WriteSlotsToMarkdown(ByRef freeSlots() As String, ByVal slotCount As Long)
    Dim fileNum As Integer
    Dim i       As Long

    fileNum = FreeFile()

    Open OUTPUT_PATH For Output As #fileNum

    ' Header
    Print #fileNum, "# Freie Terminslots"
    Print #fileNum, ""
    Print #fileNum, "Zeitraum: " & Format(Date, "YYYY-MM-DD") & " bis " & _
                    Format(Date + LOOKAHEAD_DAYS - 1, "YYYY-MM-DD")
    Print #fileNum, "Fenster: " & SLOT_WINDOW_START & " - " & SLOT_WINDOW_END & _
                    " Uhr (je " & SLOT_DURATION_MIN & " Min)"
    Print #fileNum, "Generiert: " & Format(Now, "YYYY-MM-DD HH:MM:SS")
    Print #fileNum, ""

    If slotCount = 0 Then
        Print #fileNum, "_Keine freien Slots gefunden._"
    Else
        Print #fileNum, "## Verfuegbare Slots (" & slotCount & ")"
        Print #fileNum, ""
        For i = 0 To slotCount - 1
            Print #fileNum, "- " & freeSlots(i)
        Next i
    End If

    Close #fileNum
End Sub

''' Stellt sicher, dass ein Verzeichnis existiert (rekursiv).
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
