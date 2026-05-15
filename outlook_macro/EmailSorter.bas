' =============================================================================
' EmailSorter.bas
' Outlook 2019 VBA-Makro
'
' Funktionsweise:
'   1. Liest eine YAML-Datei (students.yaml) ein.
'   2. Durchlaeuft E-Mails im Posteingang und in Gesendeten Elementen.
'   3. Ordnet jede Mail einem Studierenden zu.
'   4. Sucht nach Keywords fuer Zielordner.
'   5. Speichert die Mail als .msg-Datei.
'   6. Behaelt nur die neueste Mail; aeltere werden nach Export geloescht.
'
' YAML-Format:
'   students:
'   - name: Max Mustermann
'     smail: m.mustermann@smail.th-koeln.de
'     emails: []
'     folders:
'     - keys:
'       - BachelorThesis
'       path: D:\Pfade\Mustermann
'
' WICHTIG: Den Pfad zur YAML-Datei in YAML_FILE_PATH anpassen!
' =============================================================================

Option Explicit

' Pfad zur YAML-Konfigurationsdatei - bitte anpassen
Private Const YAML_FILE_PATH As String = "D:\TH_Koeln\academic-memory-mcp\students.yaml"

' =============================================================================
' Hauptprozedur
' =============================================================================

''' Einstiegspunkt: Liest die YAML-Datei und sortiert Mails in Ordner.
Public Sub SortInboxByConfig()
    Dim studentMap As Object    ' Dictionary: email_lower -> foldersDict
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

    Dim savedCount   As Long
    Dim deletedCount As Long

    ProcessFolder inbox, studentMap, "Inbox", False, savedCount, deletedCount
    ProcessFolder sentItems, studentMap, "SentItems", True, savedCount, deletedCount

    MsgBox "Fertig!" & vbCrLf & _
           "Exportiert: " & savedCount & " E-Mail(s)" & vbCrLf & _
           "Geloescht (Duplikate): " & deletedCount & " E-Mail(s)", _
           vbInformation, "EmailSorter"
End Sub

' =============================================================================
' YAML-Konfiguration einlesen
' =============================================================================

''' Liest die YAML-Datei ein und erstellt eine Map von E-Mails auf Ordner.
'''
''' Args:
'''     yamlPath: Pfad zur YAML-Datei.
'''
''' Returns:
'''     Dictionary email -> foldersDict.
Private Function ReadStudentMap(ByVal yamlPath As String) As Object
    Dim result As Object
    Set result = CreateObject("Scripting.Dictionary")
    result.CompareMode = 1

    Dim fileContent As String
    fileContent = ReadUtf8File(yamlPath)
    If Len(fileContent) = 0 Then Exit Function

    Dim allLines() As String
    allLines = Split(fileContent, vbLf)

    Dim smailAddr   As String
    Dim allAddrs    As Object
    Dim foldersDict As Object
    Dim inFolders   As Boolean
    Dim inEmails    As Boolean
    Dim inFolderEntry As Boolean
    Dim currentEntryPath As String
    Dim currentEntryKeys As String
    Dim inKeysList   As Boolean

    smailAddr = ""
    Set allAddrs = New Collection
    Set foldersDict = CreateObject("Scripting.Dictionary")
    foldersDict.CompareMode = 1
    inFolders = False
    inEmails = False
    inFolderEntry = False
    inKeysList = False

    Dim iLine As Long
    For iLine = 0 To UBound(allLines)
        Dim line    As String
        Dim trimmed As String
        Dim lineIndent As Long
        line = allLines(iLine)
        If Right(line, 1) = vbCr Then line = Left(line, Len(line) - 1)
        trimmed = Trim(line)
        lineIndent = Len(line) - Len(LTrim(line))

        If Len(trimmed) = 0 Then GoTo NextLine

        ' Studierenden-Block (Einrueckung 0)
        If Left(trimmed, 2) = "- " And lineIndent = 0 Then
            CommitFolderEntry foldersDict, currentEntryKeys, currentEntryPath
            If Len(smailAddr) > 0 Then CommitStudentEntry result, smailAddr, allAddrs, foldersDict
            
            smailAddr = ""
            Set allAddrs = New Collection
            Set foldersDict = CreateObject("Scripting.Dictionary")
            foldersDict.CompareMode = 1
            inFolders = False
            inEmails = False
            inFolderEntry = False
            inKeysList = False
            currentEntryKeys = ""
            currentEntryPath = ""
            
            ' name: part could be on the same line
            Dim afterDash As String
            afterDash = Trim(Mid(trimmed, 3))
            If Left(afterDash, 5) = "name:" Then
                ' Ignored
            End If
            GoTo NextLine
        End If

        ' smail, emails, folders (Einrueckung 2)
        If lineIndent = 2 Then
            If Left(trimmed, 6) = "smail:" Then
                smailAddr = LCase(Replace(Trim(Mid(trimmed, 7)), """", ""))
                If Len(smailAddr) > 0 Then allAddrs.Add smailAddr
                inFolders = False
                inEmails = False
                GoTo NextLine
            End If

            If Left(trimmed, 7) = "emails:" Then
                Dim emailsRaw As String
                emailsRaw = Trim(Mid(trimmed, 8))
                If emailsRaw = "[]" Then inEmails = False Else inEmails = True
                inFolders = False
                GoTo NextLine
            End If

            If Left(trimmed, 8) = "folders:" Then
                inFolders = True
                inEmails = False
                GoTo NextLine
            End If
            
            ' Neuer folder-Eintrag (Einrueckung 2, beginnt mit "- ")
            If inFolders And Left(trimmed, 2) = "- " Then
                CommitFolderEntry foldersDict, currentEntryKeys, currentEntryPath
                currentEntryKeys = ""
                currentEntryPath = ""
                inFolderEntry = True
                inKeysList = False
                
                Dim folderAfterDash As String
                folderAfterDash = Trim(Mid(trimmed, 3))
                If Left(folderAfterDash, 5) = "keys:" Then
                    currentEntryKeys = Trim(Mid(folderAfterDash, 6))
                    If Len(currentEntryKeys) = 0 Then inKeysList = True
                ElseIf Left(folderAfterDash, 5) = "path:" Then
                    currentEntryPath = Replace(Replace(Trim(Mid(folderAfterDash, 6)), """", ""), "\\", "\")
                End If
                GoTo NextLine
            End If
            
            ' email entry (Einrueckung 2, beginnt mit "- ")
            If inEmails And Left(trimmed, 2) = "- " Then
                Dim eAddr As String
                eAddr = LCase(Replace(Trim(Mid(trimmed, 3)), """", ""))
                If Len(eAddr) > 0 Then allAddrs.Add eAddr
                GoTo NextLine
            End If
        End If

        ' Felder innerhalb eines folder-Eintrags (Einrueckung 4)
        If inFolderEntry And lineIndent = 4 Then
            If Left(trimmed, 5) = "keys:" Then
                currentEntryKeys = Trim(Mid(trimmed, 6))
                If Len(currentEntryKeys) = 0 Then inKeysList = True Else inKeysList = False
            ElseIf Left(trimmed, 5) = "path:" Then
                currentEntryPath = Replace(Replace(Trim(Mid(trimmed, 6)), """", ""), "\\", "\")
                inKeysList = False
            End If
            GoTo NextLine
        End If
        
        ' Keys in Listenform oder items (Einrueckung 4, beginnt mit "- ")
        If inKeysList And Left(trimmed, 2) = "- " And lineIndent = 4 Then
            Dim kw As String
            kw = Replace(Trim(Mid(trimmed, 3)), """", "")
            If Len(currentEntryKeys) > 0 Then currentEntryKeys = currentEntryKeys & ","
            currentEntryKeys = currentEntryKeys & kw
            GoTo NextLine
        End If

NextLine:
    Next iLine

    CommitFolderEntry foldersDict, currentEntryKeys, currentEntryPath
    If Len(smailAddr) > 0 Then CommitStudentEntry result, smailAddr, allAddrs, foldersDict

    Set ReadStudentMap = result
End Function

''' Traegt einen Ordner-Eintrag in das foldersDict ein.
'''
''' Args:
'''     foldersDict: Ziel-Dictionary.
'''     keysRaw:     Rohe Keyword-Liste.
'''     folderPath:  Pfad zum Ordner.
Private Sub CommitFolderEntry(ByVal foldersDict As Object, _
                              ByVal keysRaw As String, _
                              ByVal folderPath As String)
    If Len(Trim(keysRaw)) = 0 Or Len(Trim(folderPath)) = 0 Then Exit Sub

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

''' Speichert alle Adressen eines Studierenden in der studentMap.
'''
''' Args:
'''     result:      Ziel-Dictionary.
'''     smailAddr:   Hauptadresse.
'''     allAddrs:    Liste aller Adressen.
'''     foldersDict: Ordner-Zuordnung.
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
' Ordner verarbeiten
' =============================================================================

''' Durchlaeuft einen Outlook-Ordner und exportiert Mails.
'''
''' Args:
'''     folder:       Der Ordner.
'''     studentMap:   Konfiguration.
'''     subFolder:    Name des Unterordners (Inbox/SentItems).
'''     isSent:       Ob es gesendete Mails sind.
'''     savedCount:   Zaehler fuer gespeicherte Mails.
'''     deletedCount: Zaehler fuer geloeschte Duplikate.
Private Sub ProcessFolder(ByVal folder As Outlook.MAPIFolder, _
                          ByVal studentMap As Object, _
                          ByVal subFolder As String, _
                          ByVal isSent As Boolean, _
                          ByRef savedCount As Long, _
                          ByRef deletedCount As Long)
    Dim items As Outlook.items
    Set items = folder.items
    
    Dim senderMails As Object
    Set senderMails = CreateObject("Scripting.Dictionary")
    senderMails.CompareMode = 1

    Dim i As Long
    For i = items.Count To 1 Step -1
        Dim item As Object
        Set item = items.item(i)
        If TypeOf item Is Outlook.mailItem Then
            Dim mail As Outlook.mailItem
            Set mail = item
            Dim emailAddr As String
            If isSent Then
                emailAddr = GetFirstRecipientAddress(mail)
            Else
                emailAddr = GetSenderEmailAddress(mail)
            End If

            If Len(Trim(emailAddr)) > 0 Then
                If studentMap.Exists(emailAddr) Then
                    If Not senderMails.Exists(emailAddr) Then
                        Set senderMails(emailAddr) = New Collection
                    End If
                    senderMails(emailAddr).Add mail
                End If
            End If
        End If
    Next i

    Dim key As Variant
    For Each key In senderMails.Keys
        If Len(Trim(CStr(key))) > 0 Then
            Dim foldersDict As Object
            Set foldersDict = studentMap(key)

            If foldersDict.Count > 0 Then
                Dim mails As Collection
                Set mails = senderMails(key)

                Dim newestMail As Outlook.mailItem
                Set newestMail = mails(1)
                Dim m As Variant
                For Each m In mails
                    If m.ReceivedTime > newestMail.ReceivedTime Then Set newestMail = m
                Next m

                Dim j As Long
                For j = 1 To mails.Count
                    Dim currentMail As Outlook.mailItem
                    Set currentMail = mails(j)

                    Dim targetFolder As String
                    targetFolder = FindFolderByKeyword(currentMail, foldersDict)

                    If Len(targetFolder) = 0 Then
                        Dim firstKey As Variant
                        firstKey = foldersDict.Keys
                        If UBound(firstKey) >= 0 Then targetFolder = foldersDict(firstKey(0))
                    End If

                    If Len(targetFolder) > 0 Then
                        Dim fullPath As String
                        fullPath = targetFolder & "\" & subFolder
                        If EnsureDirectory(fullPath) Then
                            Dim filePath As String
                            filePath = BuildMsgFilePath(fullPath, currentMail)
                            If SaveMailToFile(currentMail, fullPath, filePath) Then
                                savedCount = savedCount + 1
                                If currentMail.EntryID <> newestMail.EntryID Then
                                    currentMail.Delete
                                    deletedCount = deletedCount + 1
                                End If
                            End If
                        End If
                    End If
                Next j
            End If
        End If
    Next key
End Sub

''' Sucht Keywords im Betreff/Text einer Mail.
'''
''' Args:
'''     mail:        Die Mail.
'''     foldersDict: Keyword-zu-Pfad-Map.
'''
''' Returns:
'''     Gefundener Pfad oder leerer String.
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
' =============================================================================

''' Erstellt den Dateipfad fuer eine Mail.
'''
''' Args:
'''     folderPath: Zielordner.
'''     mail:       Die Mail.
'''
''' Returns:
'''     Dateipfad.
Private Function BuildMsgFilePath(ByVal folderPath As String, _
                                  ByVal mail As Outlook.mailItem) As String
    Dim datePart    As String
    Dim subjectPart As String
    datePart = Format(mail.ReceivedTime, "YYYYMMDD_HHMMSS")
    subjectPart = SanitizeFileName(mail.Subject)
    If Len(subjectPart) > 80 Then subjectPart = Left(subjectPart, 80)
    BuildMsgFilePath = folderPath & "\" & datePart & " - " & subjectPart & ".msg"
End Function

''' Entfernt ungueltige Zeichen aus Dateinamen.
'''
''' Args:
'''     name: Name.
'''
''' Returns:
'''     Bereinigter Name.
Private Function SanitizeFileName(ByVal name As String) As String
    Dim invalidChars As String
    Dim i            As Long
    invalidChars = "\/:*?""<>|"
    SanitizeFileName = name
    For i = 1 To Len(invalidChars)
        SanitizeFileName = Join(Split(SanitizeFileName, Mid(invalidChars, i, 1)), "_")
    Next i
    SanitizeFileName = Trim(SanitizeFileName)
    If Len(SanitizeFileName) = 0 Then SanitizeFileName = "kein_Betreff"
End Function

''' Stellt sicher dass ein Ordner existiert.
'''
''' Args:
'''     path: Pfad.
'''
''' Returns:
'''     True bei Erfolg.
Private Function EnsureDirectory(ByVal path As String) As Boolean
    Dim fso As Object
    Set fso = CreateObject("Scripting.FileSystemObject")
    If fso.FolderExists(path) Then
        EnsureDirectory = True
        Exit Function
    End If
    Dim parent As String
    parent = fso.GetParentFolderName(path)
    If Len(parent) > 0 And parent <> path Then
        If EnsureDirectory(parent) Then
            On Error Resume Next
            fso.CreateFolder path
            EnsureDirectory = fso.FolderExists(path)
            Exit Function
        End If
    End If
    EnsureDirectory = False
End Function

''' Ermittelt die Absender-E-Mail.
'''
''' Args:
'''     mail: Die Mail.
'''
''' Returns:
'''     E-Mail-Adresse.
Private Function GetSenderEmailAddress(ByVal mail As Outlook.mailItem) As String
    On Error Resume Next
    GetSenderEmailAddress = LCase(mail.SenderEmailAddress)
    Dim sender As Outlook.AddressEntry
    Set sender = mail.Sender
    If Not sender Is Nothing Then
        If sender.AddressEntryUserType = olExchangeUserAddressEntry Then
            GetSenderEmailAddress = LCase(sender.GetExchangeUser().PrimarySmtpAddress)
        End If
    End If
End Function

''' Ermittelt die E-Mail des ersten Empfaengers.
'''
''' Args:
'''     mail: Die Mail.
'''
''' Returns:
'''     E-Mail-Adresse.
Private Function GetFirstRecipientAddress(ByVal mail As Outlook.mailItem) As String
    On Error Resume Next
    GetFirstRecipientAddress = LCase(mail.Recipients(1).Address)
    Dim recip As Outlook.Recipient
    Set recip = mail.Recipients(1)
    If Not recip.AddressEntry Is Nothing Then
        If recip.AddressEntry.AddressEntryUserType = olExchangeUserAddressEntry Then
            GetFirstRecipientAddress = LCase(recip.AddressEntry.GetExchangeUser().PrimarySmtpAddress)
        End If
    End If
End Function

''' Speichert eine Mail als .msg Datei.
'''
''' Args:
'''     mail:       Die Mail.
'''     folderPath: Zielordner.
'''     filePath:   Dateipfad.
'''
''' Returns:
'''     True bei Erfolg.
Private Function SaveMailToFile(ByVal mail As Outlook.mailItem, _
                                ByVal folderPath As String, _
                                ByVal filePath As String) As Boolean
    On Error Resume Next
    mail.SaveAs filePath, olMSG
    SaveMailToFile = (Err.Number = 0)
End Function

''' Prueft ob eine Datei existiert.
'''
''' Args:
'''     path: Pfad.
'''
''' Returns:
'''     True bei Existenz.
Private Function FileExists(ByVal path As String) As Boolean
    FileExists = (Len(Dir(path)) > 0)
End Function

''' Liest eine UTF-8 Datei.
'''
''' Args:
'''     filePath: Pfad.
'''
''' Returns:
'''     Inhalt.
Private Function ReadUtf8File(ByVal filePath As String) As String
    On Error Resume Next
    Dim stream As Object
    Set stream = CreateObject("ADODB.Stream")
    stream.CharSet = "UTF-8"
    stream.Open
    stream.LoadFromFile filePath
    ReadUtf8File = stream.ReadText
    stream.Close
End Function
