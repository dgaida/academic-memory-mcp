' =============================================================================
' ExportMailsBySubjectAndAge.bas
' Outlook VBA-Makro zum Exportieren und Loeschen von Mails basierend auf Betreff und Alter
'
' Funktionsweise:
'   1. Greift auf das Konto "daniel.gaida@th-koeln.de" zu.
'   2. Durchlaeuft den Posteingang (Inbox) und "Sent Items".
'   3. Filtert Mails, die aelter als 1 Jahr sind.
'   4. Prueft, ob ein Suchwort (z.B. "Nachteilsausgleich") im Betreff vorkommt.
'   5. Speichert diese als .msg-Dateien unter "D:\TH_Koeln\StudentMails\SubjectExport".
'   6. Dateiname: YYYYMMDD_HHMMSS - Betreff.msg
'   7. Loescht die E-Mail nach erfolgreichem Export.
' =============================================================================

Option Explicit

#If VBA7 Then
    Private Declare PtrSafe Sub Sleep Lib "kernel32" (ByVal dwMilliseconds As LongPtr)
#Else
    Private Declare Sub Sleep Lib "kernel32" (ByVal dwMilliseconds As Long)
#End If

' Konfiguration
Private Const ACCOUNT_NAME As String = "daniel.gaida@th-koeln.de"
Private Const ROOT_PATH As String = "D:\TH_Koeln\StudentMails\SubjectExport"
Private Const SEARCH_WORD As String = "Nachteilsausgleich"
Private Const MIN_AGE_YEARS As Integer = 1

' =============================================================================
' Hauptprozedur
' =============================================================================

''' Einstiegspunkt fuer das Makro.
Public Sub ExportMailsBySubjectAndAge()
    Dim ns As Outlook.NameSpace
    Dim account As Outlook.account
    Dim store As Outlook.store
    Dim rootFolder As Outlook.folder
    Dim inbox As Outlook.folder
    Dim sentItems As Outlook.folder
    Dim cutoffDate As Date

    Set ns = Application.GetNamespace("MAPI")

    ' Konto suchen
    On Error Resume Next
    Set account = ns.Accounts.Item(ACCOUNT_NAME)
    On Error GoTo 0

    If account Is Nothing Then
        MsgBox "Konto '" & ACCOUNT_NAME & "' wurde nicht gefunden.", vbCritical, "ExportBySubject"
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
        MsgBox "Inbox oder Sent Items konnte nicht gefunden werden.", vbCritical, "ExportBySubject"
        Exit Sub
    End If

    ' Stichtag berechnen (1 Jahr zurueck)
    cutoffDate = DateAdd("yyyy", -MIN_AGE_YEARS, Now())

    ' Verarbeitung starten
    ProcessFolderBySubject inbox, "Inbox", cutoffDate
    ProcessFolderBySubject sentItems, "SentItems", cutoffDate

    MsgBox "Export abgeschlossen!", vbInformation, "ExportBySubject"
End Sub

' =============================================================================
' Verarbeitungs-Logik
' =============================================================================

''' Durchlaeuft Mails in einem Ordner, filtert nach Alter und Betreff.
Private Sub ProcessFolderBySubject(ByVal olFolder As Outlook.folder, ByVal subFolderName As String, ByVal cutoffDate As Date)
    Dim items As Outlook.items
    Dim item As Object
    Dim mail As Outlook.mailItem
    Dim i As Long
    Dim targetPath As String
    Dim filePath As String
    Dim savedCount As Long
    Dim filterStr As String

    targetPath = ROOT_PATH & "\" & subFolderName
    If Not EnsureDirectory(targetPath) Then
        MsgBox "Zielverzeichnis konnte nicht erstellt werden: " & targetPath, vbCritical
        Exit Sub
    End If

    ' Items laden
    Set items = olFolder.items

    ' Zeitfilter: Nur Mails, die VOR dem cutoffDate liegen (also aelter sind)
    ' Outlook Restrict Filter braucht US-Format (MM/DD/YYYY HH:MM)
    filterStr = "[ReceivedTime] <= """ & Month(cutoffDate) & "/" & Day(cutoffDate) & "/" & Year(cutoffDate) & " " & Format(cutoffDate, "HH:mm") & """"
    Set items = items.Restrict(filterStr)

    ' Sortieren (aelteste zuerst fuer stabilere Iteration beim Loeschen)
    items.Sort "[ReceivedTime]", False

    savedCount = 0

    ' Rueckwaerts durchlaufen ist bei Outlook-Kollektionen notwendig, wenn geloescht wird
    For i = items.count To 1 Step -1
        Set item = items(i)

        If TypeOf item Is mailItem Then
            Set mail = item

            ' Betreff-Filter (Case-Insensitive)
            If InStr(1, mail.Subject, SEARCH_WORD, vbTextCompare) > 0 Then
                filePath = BuildMsgFilePath(targetPath, mail)

                ' Speichern falls nicht vorhanden
                If Len(Dir(filePath)) = 0 Then
                    On Error Resume Next
                    mail.SaveAs filePath, olMSG
                    If Err.Number = 0 Then
                        savedCount = 1 ' Platzhalter fuer Log
                        mail.Delete
                    End If
                    On Error GoTo 0
                Else
                    ' Falls bereits vorhanden, auch loeschen
                    mail.Delete
                End If
            End If
        End If

        ' System entlasten (wie in ExportStudentMails.bas)
        If i Mod 10 = 0 Then
            DoEvents
            Sleep 50
        End If
    Next i

    Debug.Print "Ordner " & subFolderName & " verarbeitet."
End Sub

' =============================================================================
' Hilfsfunktionen
' =============================================================================

Private Function BuildMsgFilePath(ByVal folderPath As String, ByVal mail As Outlook.mailItem) As String
    Dim datePart As String
    Dim subjectPart As String

    datePart = Format(mail.ReceivedTime, "YYYYMMDD_HHMMSS")
    subjectPart = SanitizeFileName(mail.Subject)

    If Len(subjectPart) > 80 Then subjectPart = Left(subjectPart, 80)

    BuildMsgFilePath = folderPath & "\" & datePart & " - " & subjectPart & ".msg"
End Function

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
