' =============================================================================
' EmailSorter.bas
' Outlook 2019 VBA-Makro
'
' Funktionsweise:
'   1. Liest eine Markdown-Datei ein, die E-Mail-Adressen und Zielordner-Pfade
'      auf dem Dateisystem enthaelt (Tab- oder mehrfach-Leerzeichen-getrennt).
'   2. Durchlaeuft alle E-Mails im Posteingang.
'   3. Speichert E-Mails bekannter Absender als .msg-Datei im zugeordneten
'      Ordner auf dem Laufwerk.
'   4. Behaelt pro Absender nur die neueste Mail in Outlook; aeltere werden
'      nach dem Export geloescht.
'
' Markdown-Format der Konfigurationsdatei (z.B. email_config.md):
'   absender@example.com     C:\Ablage\KundeA
'   info@firma.de            D:\Archiv\Newsletter
'   ...
'   Leerzeilen und Zeilen, die mit '#' beginnen, werden ignoriert.
'
' WICHTIG: Den Pfad zur Markdown-Datei in CONFIG_FILE_PATH anpassen!
' =============================================================================

Option Explicit

' Pfad zur Markdown-Konfigurationsdatei - bitte anpassen
Private Const CONFIG_FILE_PATH As String = "D:\TH_Koeln\academic-memory-mcp\email_config.md"

' Trennzeichen zwischen E-Mail-Adresse und Ordnerpfad in der MD-Datei
' Das Makro unterstuetzt sowohl Tabs als auch mehrere Leerzeichen als Trenner
Private Const MIN_SPACES_AS_SEPARATOR As Integer = 2

' =============================================================================
' Hauptprozedur - Einstiegspunkt des Makros
' =============================================================================

''' Hauptprozedur: Liest die Konfiguration und exportiert E-Mails aus dem
''' Posteingang als .msg-Dateien auf das Dateisystem.
Public Sub SortInboxByConfig()
    Dim emailMap   As Object
    Dim inbox      As Outlook.MAPIFolder
    Dim sentItems  As Outlook.MAPIFolder
    Dim configPath As String

    configPath = CONFIG_FILE_PATH

    If Not FileExists(configPath) Then
        MsgBox "Konfigurationsdatei nicht gefunden:" & vbCrLf & configPath, _
               vbCritical, "EmailSorter"
        Exit Sub
    End If

    Set emailMap = ReadEmailConfig(configPath)
    If emailMap Is Nothing Then
        MsgBox "Fehler beim Einlesen der Konfigurationsdatei.", vbCritical, "EmailSorter"
        Exit Sub
    End If

    If emailMap.Count = 0 Then
        MsgBox "Keine gueltigen Eintraege in der Konfigurationsdatei gefunden.", _
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

    ProcessFolder inbox, emailMap, "Inbox", False, savedCount, deletedCount
    ProcessFolder sentItems, emailMap, "SentItems", True, savedCount, deletedCount

    MsgBox "Fertig!" & vbCrLf & _
           "Exportiert: " & savedCount & " E-Mail(s)" & vbCrLf & _
           "Geloescht (Duplikate): " & deletedCount & " E-Mail(s)", _
           vbInformation, "EmailSorter"

    Set emailMap = Nothing
End Sub

' =============================================================================
' Konfiguration einlesen
' =============================================================================

''' Liest die Markdown-Konfigurationsdatei ein und gibt ein Dictionary zurueck.
'''
''' Args:
'''     filePath: Vollstaendiger Pfad zur Markdown-Datei.
'''
''' Returns:
'''     Scripting.Dictionary mit E-Mail-Adresse (Lowercase) als Key
'''     und Dateisystem-Ordnerpfad als Value. Nothing bei einem Fehler.
Private Function ReadEmailConfig(ByVal filePath As String) As Object
    Dim fso        As Object
    Dim fileStream As Object
    Dim dict       As Object
    Dim line       As String
    Dim parts(1)   As String

    Set dict = CreateObject("Scripting.Dictionary")
    dict.CompareMode = 1 ' vbTextCompare - Gross-/Kleinschreibung ignorieren

    Set fso = CreateObject("Scripting.FileSystemObject")

    On Error GoTo ReadError
    Set fileStream = fso.OpenTextFile(filePath, 1, False) ' 1 = ForReading

    Do While Not fileStream.AtEndOfStream
        line = Trim(fileStream.ReadLine())

        ' Leerzeilen und Kommentarzeilen (beginnen mit #) ueberspringen
        If Len(line) = 0 Then GoTo NextLine
        If Left(line, 1) = "#" Then GoTo NextLine

        ' Zeile in E-Mail und Pfad aufteilen
        If ParseConfigLine(line, parts) Then
            Dim emailAddr  As String
            Dim folderPath As String
            emailAddr = LCase(Trim(parts(0)))
            folderPath = Trim(parts(1))
            ' Markdown-Escapes aufloesen: \_ -> _, \\ -> \, usw.
            folderPath = Replace(folderPath, "\_", "_")
            folderPath = Replace(folderPath, "\\", "\")

            If Len(emailAddr) > 0 And Len(folderPath) > 0 Then
                If Not dict.Exists(emailAddr) Then
                    dict.Add emailAddr, folderPath
                End If
            End If
        End If

NextLine:
    Loop

    fileStream.Close
    Set ReadEmailConfig = dict
    Exit Function

ReadError:
    MsgBox "Fehler beim Lesen der Datei: " & Err.Description, vbCritical, "EmailSorter"
    If Not fileStream Is Nothing Then fileStream.Close
    Set ReadEmailConfig = Nothing
End Function

''' Zerlegt eine Konfigurationszeile in E-Mail-Adresse und Ordnerpfad.
'''
''' Unterstuetzt als Trennzeichen: Tab-Zeichen oder mind. 2 aufeinanderfolgende
''' Leerzeichen, damit einzelne Leerzeichen in Pfaden nicht als Trenner gelten.
'''
''' Args:
'''     line:  Eine Zeile aus der Konfigurationsdatei.
'''     parts: Ausgabe-Array(0..1); parts(0) = E-Mail, parts(1) = Ordnerpfad.
'''
''' Returns:
'''     True wenn die Zeile erfolgreich zerlegt werden konnte, sonst False.
Private Function ParseConfigLine(ByVal line As String, ByRef parts() As String) As Boolean
    Dim tabPos   As Long
    Dim spacePos As Long

    ParseConfigLine = False
    parts(0) = ""
    parts(1) = ""

    ' Versuch 1: Tab als Trenner
    tabPos = InStr(line, vbTab)
    If tabPos > 1 Then
        parts(0) = Left(line, tabPos - 1)
        parts(1) = Mid(line, tabPos + 1)
        ParseConfigLine = True
        Exit Function
    End If

    ' Versuch 2: Mindestens MIN_SPACES_AS_SEPARATOR Leerzeichen als Trenner
    Dim separator As String
    separator = String(MIN_SPACES_AS_SEPARATOR, " ")
    spacePos = InStr(line, separator)
    If spacePos > 1 Then
        parts(0) = Left(line, spacePos - 1)
        parts(1) = Trim(Mid(line, spacePos))
        ParseConfigLine = True
        Exit Function
    End If
End Function

' =============================================================================
' Posteingang verarbeiten
' =============================================================================

''' Durchlaeuft einen Outlook-Ordner, exportiert und loescht E-Mails gemaess Config.
'''
''' Args:
'''     folder:       Der zu durchsuchende Outlook-Ordner.
'''     emailMap:     Dictionary mit E-Mail-Adressen und Zielordner-Pfaden.
'''     subFolder:    Unterordner-Name der an den konfigurierten Pfad angehaengt wird.
'''     isSent:       True = Empfaengeradresse pruefen (Gesendete), False = Absender (Eingang).
'''     savedCount:   Zaehler der exportierten Mails (wird hochgezaehlt).
'''     deletedCount: Zaehler der geloeschten Mails (wird hochgezaehlt).
Private Sub ProcessFolder(ByVal folder As Outlook.MAPIFolder, _
                          ByVal emailMap As Object, _
                          ByVal subFolder As String, _
                          ByVal isSent As Boolean, _
                          ByRef savedCount As Long, _
                          ByRef deletedCount As Long)

    Dim senderMails As Object
    Set senderMails = CreateObject("Scripting.Dictionary")
    senderMails.CompareMode = 1

    Dim items       As Outlook.items
    Dim item        As Object
    Dim matchEmail  As String

    Set items = folder.items

    Dim i As Long
    For i = 1 To items.Count
        Set item = items(i)

        If item.Class = olMail Then
            If isSent Then
                ' Gesendete Mails: ersten Empfaenger pruefen
                matchEmail = GetFirstRecipientAddress(item)
            Else
                matchEmail = LCase(GetSenderEmailAddress(item))
            End If

            If emailMap.Exists(matchEmail) Then
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

        ' Zielordner: konfigurierter Pfad + Unterordner
        Dim targetPath As String
        targetPath = emailMap(key) & "\" & subFolder

        If Not EnsureDirectory(targetPath) Then
            MsgBox "Ordner konnte nicht erstellt werden:" & vbCrLf & targetPath, _
                   vbExclamation, "EmailSorter"
            GoTo NextSender
        End If

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

        ' Alle Mails exportieren; aeltere danach loeschen
        For j = 1 To mailCollection.Count
            Set currentMail = mailCollection(j)

            Dim filePath As String
            filePath = BuildMsgFilePath(targetPath, currentMail)

            If SaveMailToFile(currentMail, targetPath, filePath) Then
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
        Next j

NextSender:
    Next key

    Set senderMails = Nothing
End Sub

' =============================================================================
' Hilfsfunktionen
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
'''     Vollstaendiger Dateipfad als String, z.B.
'''     "C:\Ablage\KundeA\20260513_143022 - Betreff.msg"
Private Function BuildMsgFilePath(ByVal folderPath As String, _
                                  ByVal mail As Outlook.mailItem) As String
    Dim datePart    As String
    Dim subjectPart As String
    Dim fileName    As String

    datePart = Format(mail.ReceivedTime, "YYYYMMDD_HHMMSS")
    subjectPart = SanitizeFileName(mail.Subject)

    If Len(subjectPart) > 80 Then subjectPart = Left(subjectPart, 80)

    fileName = datePart & " - " & subjectPart & ".msg"

    ' Abschliessende Backslashes entfernen, dann sauber zusammensetzen
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

    ' Fuehrende/abschliessende Leerzeichen und Punkte entfernen
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
'''     True wenn der Ordner existiert oder erfolgreich erstellt wurde,
'''     False bei einem Fehler.
Private Function EnsureDirectory(ByVal path As String) As Boolean
    ' Abschliessenden Backslash entfernen falls vorhanden
    Do While Right(path, 1) = "\"
        path = Left(path, Len(path) - 1)
    Loop

    Dim fso As Object
    Set fso = CreateObject("Scripting.FileSystemObject")

    ' Ordner existiert bereits - nichts zu tun
    If fso.FolderExists(path) Then
        EnsureDirectory = True
        Exit Function
    End If

    ' Elternordner rekursiv sicherstellen, dann diesen Ordner anlegen
    Dim parentPath As String
    parentPath = fso.GetParentFolderName(path)

    If Len(parentPath) = 0 Or parentPath = path Then
        ' Laufwerkswurzel erreicht - kann nicht angelegt werden
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
''' Behandelt sowohl externe Absender (SenderEmailAddress) als auch
''' interne Exchange-Absender, bei denen die Adresse aus dem
''' AddressEntry ausgelesen werden muss.
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

''' Gibt die SMTP-Adresse des ersten Empfaengers einer gesendeten Mail zurueck.
'''
''' Args:
'''     mail: Das MailItem, dessen Empfaengeradresse ermittelt werden soll.
'''
''' Returns:
'''     Die SMTP-E-Mail-Adresse des ersten Empfaengers (Lowercase),
'''     oder leerer String wenn keine Empfaenger vorhanden.
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

''' Gibt den Standard-Posteingang des ersten Kontos zurueck.
'''
''' Returns:
'''     Das MAPIFolder-Objekt des Posteingangs, oder Nothing bei Fehler.
Private Function GetInboxFolder() As Outlook.MAPIFolder
    On Error GoTo InboxError
    Set GetInboxFolder = Application.Session.GetDefaultFolder(olFolderInbox)
    Exit Function
InboxError:
    Set GetInboxFolder = Nothing
End Function


''' Speichert eine Mail als .msg-Datei auf dem Dateisystem.
'''
''' Args:
'''     mail:     Das zu exportierende MailItem.
'''     filePath: Vollstaendiger Zieldateipfad inkl. Dateiname.
'''
''' Returns:
'''     True wenn die Datei erfolgreich gespeichert wurde und
'''     anschliessend auf dem Dateisystem nachweislich existiert.
'''     False bei jedem Fehler.
Private Function SaveMailToFile(ByVal mail As Outlook.mailItem, _
                                ByVal folderPath As String, _
                                ByRef filePath As String) As Boolean
    Dim fso         As Object
    Dim folder      As Object
    Dim countBefore As Long
    Dim countAfter  As Long

    Set fso = CreateObject("Scripting.FileSystemObject")

    On Error GoTo SaveError

    ' Datei existiert bereits - ueberspringen, aber als Erfolg werten
    If fso.FileExists(filePath) Then
        SaveMailToFile = True
        Exit Function
    End If

    ' Dateianzahl im Zielordner vor dem Speichern
    Set folder = fso.GetFolder(folderPath)
    countBefore = folder.Files.Count

    mail.SaveAs filePath, olMSG

    ' Dateianzahl nach dem Speichern - muss groesser sein
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
'''     True wenn die Datei existiert, sonst False.
Private Function FileExists(ByVal path As String) As Boolean
    FileExists = (Len(Dir(path)) > 0)
End Function
